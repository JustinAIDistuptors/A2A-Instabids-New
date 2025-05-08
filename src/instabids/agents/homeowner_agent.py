'''HomeownerAgent: multimodal concierge for homeowners.'''
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from google.adk import LlmAgent, enable_tracing
from google.adk.messages import UserMessage

# Tools imports
from instabids.tools import supabase_tools
from instabids.tools.stt_tool import speech_to_text
from instabids.tools.vision_tool_plus import analyse, validate_image_for_bid_card

# Other imports
from instabids.a2a_comm import send_envelope
from memory.persistent_memory import PersistentMemory
from memory.conversation_state import ConversationState
import logging
from instabids.data import project_repo as repo
from .job_classifier import classify
from .slot_filler import missing_slots, SLOTS, get_next_question, process_image_for_slots, update_card_from_images

# enable stdout tracing for dev envs
enable_tracing("stdout")
# Set up logging
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are HomeownerAgent, a long‑term concierge for homeowners. "
    "Given images, voice/text, or forms, classify the project, ask clarifying "
    "questions, persist structured data to Supabase, and emit a 'project.created' "
    "A2A envelope once you have enough details. Keep memory of preferences and "
    "prior jobs for each user. Analyze images to identify damage, materials, "
    "and project type."
)

class HomeownerAgent(LlmAgent):
    '''Concrete ADK agent with multimodal intake and memory.'''
    def __init__(self, memory: Optional[PersistentMemory] = None):
        super().__init__(name="HomeownerAgent", tools=[*supabase_tools], 
                      system_prompt=SYSTEM_PROMPT, memory=memory or PersistentMemory())
        
    async def gather_project_info(self, user_id: str, description: Optional[str] = None, 
                               form_payload: Optional[Dict[str, Any]] = None, 
                               project_id: Optional[str] = None) -> Dict[str, Any]:
        '''
        Gather project information through slot-filling.
        
        Args:
            user_id: User ID for preference lookup/storage
            description: Optional initial project description
            form_payload: Optional form data
            project_id: Optional project ID for context
            
        Returns:
            Dict with project info or next question
        '''
        # Initialize or get state
        state_key = f"project_info:{user_id}"
        state = self.memory.get(state_key, ConversationState())
        
        # Add new input if provided
        if description:
            state.add_user_input(description)
        
        # Determine next action based on state
        if state.is_complete():
            # We have all required information
            return {
                "need_more": False,
                "project": state.get_slots()
            }
        else:
            # Need more info - determine what to ask next
            next_slot = state.get_next_slot()
            question = state.get_question_for_slot(next_slot)
            
            # Save state
            self.memory.set(state_key, state)
            
            return {
                "need_more": True,
                "next_slot": next_slot,
                "question": question,
                "project": state.get_slots()
            }
            
    async def process_input(
        self, 
        user_id: str,
        description: Optional[str] = None,
        form_payload: Optional[Dict[str, Any]] = None,
        base64_audio: Optional[str] = None,
        project_id: Optional[str] = None,
        image_paths: List[Path] | None = None
    ) -> Dict[str, Any]:
        '''
        Process user input from various sources (text, audio, form).
        
        Args:
            user_id: User ID for preference lookup/storage
            description: Optional text description
            form_payload: Optional form data
            base64_audio: Optional base64-encoded audio
            project_id: Optional project ID for context
            image_paths: Optional paths to images
            
        Returns:
            Response dict with next question or project info
        '''
        # Process audio input if provided
        if base64_audio:
            transcript = await speech_to_text(base64_audio)
            if transcript:
                description = transcript
                logger.info(f"Processed audio input: {description[:50]}...")
            else:
                logger.warning("Audio transcription failed or was rejected")
                return {"error": "Could not understand audio. Please try again or type your request."}
        
        # Process form input if provided
        if form_payload:
            # Update memory with form data
            bid_card = self.memory.get("bid_card", default={})
            bid_card.update(form_payload)
            self.memory.set("bid_card", bid_card)
        
        # Build bid_card dict from memory + this turn
        bid_card = {
            **self.memory.get("bid_card", default={}),
            "description": description or "",
            "user_id": user_id,
        }
        
        # Process images if provided and update bid_card with extracted information
        if image_paths:
            try:
                # Use the enhanced slot filler to process images
                bid_card = await update_card_from_images(bid_card, [str(path) for path in image_paths])
                
                # Log processed images
                logger.info(f"Processed {len(image_paths)} images for slot filling")
                if "project_images" in bid_card:
                    logger.info(f"Images added to project: {len(bid_card['project_images'])}")
                
                # Extract any damage assessment for later use
                if "damage_assessment" in bid_card and bid_card["damage_assessment"]:
                    logger.info(f"Extracted damage assessment from images: {bid_card['damage_assessment'][:50]}...")
            except Exception as e:
                logger.error(f"Error processing images: {e}")
                # Continue with what we have, don't fail the entire process
        
        # Check if we need more information using slot filler
        missing = missing_slots(bid_card)
        if missing:
            # Use the slot filler to determine next question
            next_question = get_next_question(bid_card)
            self.memory.set("bid_card", bid_card)
            return {
                "need_more": True, 
                "follow_up": next_question,
                "collected": {k: v for k, v in bid_card.items() if k in SLOTS and v}
            }
        
        # If we have all needed information, finalize project
        # Classify the job based on description and any extracted category from images
        classification_input = bid_card.get("description", "")
        if "category" in bid_card and bid_card["category"]:
            classification_input += f" {bid_card['category']}"
        if "job_type" in bid_card and bid_card["job_type"]:
            classification_input += f" {bid_card['job_type']}"
            
        classification = classify(classification_input)
        
        # Set default category if not provided
        if not bid_card.get("category"):
            bid_card["category"] = classification.get("category", "OTHER")
            
        # Create project in database
        project_id = await self._create_project(bid_card)
        
        return {
            "need_more": False,
            "project_id": project_id,
            "category": classification.get("category"),
            "confidence": classification.get("confidence", 0),
            "message": "Great! I have all the information I need to create your project."
        }
    
    async def answer_question(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        '''
        Answer a homeowner's question about their project.
        
        Args:
            question: The user's question
            context: Optional context like project history
            
        Returns:
            Agent's response
        '''
        # TODO: Implement answer_question
        return "I'll need to look that up for you."
    
    async def create_project(self, description: str, images: Optional[List[Dict[str, Any]]] = None,
                       category: Optional[str] = None, urgency: Optional[str] = None,
                       user_id: Optional[str] = None, vision_context: Optional[Dict[str, Any]] = None) -> str:
        '''Create a project in the database.'''
        # Prepare classification input with any additional context
        classification_input = description
        if vision_context:
            for img_data in vision_context.values():
                if isinstance(img_data, dict):
                    # Add any labels or descriptions from vision analysis
                    if "labels" in img_data and isinstance(img_data["labels"], list):
                        classification_input += " " + " ".join(img_data["labels"])
                    if "description" in img_data and img_data["description"]:
                        classification_input += " " + img_data["description"]
                        
        # Get classification
        cls = classify(classification_input)
        
        # Prepare project row
        row = {
            "description": description,
            "homeowner_id": user_id,
            "category": category or cls["category"],
            "confidence": cls["confidence"],
        }
        
        try:
            pid = repo.save_project(row)
            if images:
                repo.save_project_photos(pid, images)
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope ----------------------------------
        payload = {"project_id": pid, "homeowner_id": row["homeowner_id"]}
        send_envelope("project.created", payload, "homeowner_agent")
        return pid
    
    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------
    async def _process_images(self, image_paths: List[Path]) -> dict[str, Any]:
        '''Process images through vision analysis and slot filling.'''
        try:
            # Convert paths to strings
            path_strings = [str(p) for p in image_paths]
            
            # Use the enhanced slot filler's process_image_for_slots function
            results = await asyncio.gather(*[process_image_for_slots(path) for path in path_strings])
            
            # Combine results
            combined_context = {}
            for i, result in enumerate(results):
                if result:  # Only add if we got valid results
                    img_name = image_paths[i].name
                    combined_context[img_name] = result
            
            return combined_context
        except Exception as e:
            logger.error(f"Error processing images: {e}")
            return {}
    
    async def _create_project(self, bid_card: Dict[str, Any]) -> str:
        '''Create a project with collected information.'''
        # Extract images if present
        images = []
        if "project_images" in bid_card:
            images = bid_card.pop("project_images")
        
        # Extract user_id
        user_id = bid_card.get("user_id")
        
        # Format project data for database
        project_data = {
            "homeowner_id": user_id,
            "title": bid_card.get("title", bid_card.get("description", "")[:80]),
            "description": bid_card.get("description", ""),
            "category": bid_card.get("category", "").lower(),
            "job_type": bid_card.get("job_type", ""),
            "location": bid_card.get("location", ""),
            "budget_range": bid_card.get("budget_range", ""),
            "timeline": bid_card.get("timeline", ""),
            "group_bidding": bid_card.get("group_bidding", "no").lower() == "yes",
        }
        
        # Add damage assessment if available
        if "damage_assessment" in bid_card and bid_card["damage_assessment"]:
            project_data["damage_notes"] = bid_card["damage_assessment"]
        
        try:
            with repo._Tx():
                pid = repo.save_project(project_data)
                if images:
                    image_data = [{"path": img} for img in images] if isinstance(images[0], str) else images
                    repo.save_project_photos(pid, image_data)
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope ----------------------------------
        payload = {"project_id": pid, "homeowner_id": project_data["homeowner_id"]}
        send_envelope("project.created", payload)
        return pid