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
from instabids.tools.gemini_vision_tool import analyse as gemini_analyse

# Other imports
from instabids.a2a_comm import send_envelope
from instabids.memory.persistent_memory import PersistentMemory
from instabids.memory.conversation_state import ConversationState
import logging
from instabids.data import project_repo as repo
from instabids.data.photo_repo import save_photo_meta, get_photo_meta, find_similar_photos
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
    def __init__(self, user_id: str, supabase_client=None, memory: Optional[PersistentMemory] = None):
        self.user_id = user_id
        self.supabase_client = supabase_client
        
        # Initialize persistent memory
        self.memory = memory or PersistentMemory(db=supabase_client, user_id=user_id)
        
        super().__init__(name="HomeownerAgent", tools=[*supabase_tools], 
                     system_prompt=SYSTEM_PROMPT)
        
        # Load user preferences and prior conversations
        self._load_user_context()
        
    async def _load_user_context(self):
        '''Load user context from persistent memory'''
        try:
            # Initialize conversation state for this user
            self.conversation_state = ConversationState(user_id=self.user_id)
            
            # Load state from persistent memory
            await self.memory.load_state(self.conversation_state)
            logger.info(f"Loaded context for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
            # Create new empty state if loading fails
            self.conversation_state = ConversationState(user_id=self.user_id)
        
    async def gather_project_info(self, description: Optional[str] = None, 
                             form_payload: Optional[Dict[str, Any]] = None, 
                             project_id: Optional[str] = None) -> Dict[str, Any]:
        '''
        Gather project information through slot-filling.
        
        Args:
            description: Optional initial project description
            form_payload: Optional form data
            project_id: Optional project ID for context
            
        Returns:
            Dict with project info or next question
        '''
        # Add new input if provided
        if description:
            self.conversation_state.add_user_message(description)
        
        # Update project_id if provided
        if project_id and not self.conversation_state.project_id:
            self.conversation_state.project_id = project_id
            
        # Update slots from form payload if provided
        if form_payload:
            for key, value in form_payload.items():
                if key in SLOTS:
                    self.conversation_state.set_slot(key, value)
        
        # Determine next action based on state
        missing = missing_slots(self.conversation_state.slots)
        if not missing:
            # We have all required information
            # Save state before completing
            await self.memory.save_state(self.conversation_state)
            return {
                "need_more": False,
                "project": self.conversation_state.slots
            }
        else:
            # Need more info - determine what to ask next
            next_question = get_next_question(self.conversation_state.slots)
            
            # Save state
            await self.memory.save_state(self.conversation_state)
            
            return {
                "need_more": True,
                "next_slot": missing[0],  # First missing slot
                "question": next_question,
                "project": self.conversation_state.slots
            }
            
    async def process_input(
        self, 
        description: Optional[str] = None,
        form_payload: Optional[Dict[str, Any]] = None,
        base64_audio: Optional[str] = None,
        project_id: Optional[str] = None,
        image_paths: List[Path] | None = None
    ) -> Dict[str, Any]:
        '''
        Process user input from various sources (text, audio, form).
        
        Args:
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
                # Add to conversation history
                self.conversation_state.add_user_message(transcript)
            else:
                logger.warning("Audio transcription failed or was rejected")
                return {"error": "Could not understand audio. Please try again or type your request."}
        
        # Process form input if provided
        if form_payload:
            # Update slots with form data
            for key, value in form_payload.items():
                if key in SLOTS:
                    self.conversation_state.set_slot(key, value)
        
        # Add description to conversation history if provided
        if description:
            self.conversation_state.add_user_message(description)
            
        # Process images if provided and update slots with extracted information
        if image_paths:
            try:
                # Process images with Gemini Vision
                vision_context = await self._process_images(image_paths)
                
                # Store vision data in conversation state
                for img_name, metadata in vision_context.items():
                    self.conversation_state.set_vision_data(img_name, metadata)
                
                # Update bid card from images
                await update_card_from_images(self.conversation_state.slots, [str(path) for path in image_paths])
                
                # Add images to project data
                if "project_images" not in self.conversation_state.slots:
                    self.conversation_state.slots["project_images"] = []
                
                for path in image_paths:
                    img_path = str(path)
                    if img_path not in self.conversation_state.slots["project_images"]:
                        self.conversation_state.slots["project_images"].append(img_path)
                
                # Log processed images
                logger.info(f"Processed {len(image_paths)} images for slot filling")
                
                # If we have project_id, save vision metadata to database
                if project_id and vision_context:
                    for img_name, metadata in vision_context.items():
                        await save_photo_meta(project_id, img_name, metadata)
                
            except Exception as e:
                logger.error(f"Error processing images: {e}")
                # Continue with what we have, don't fail the entire process
        
        # Save state
        await self.memory.save_state(self.conversation_state)
        
        # Check if we need more information using slot filler
        missing = missing_slots(self.conversation_state.slots)
        if missing:
            # Use the slot filler to determine next question
            next_question = get_next_question(self.conversation_state.slots)
            return {
                "need_more": True, 
                "follow_up": next_question,
                "collected": {k: v for k, v in self.conversation_state.slots.items() if k in SLOTS and v}
            }
        
        # If we have all needed information, finalize project
        # Classify the job based on description and any extracted category from images
        classification_input = self.conversation_state.slots.get("description", "")
        
        # Add any label context from vision analysis
        vision_labels = self.conversation_state.get_vision_labels()
        if vision_labels:
            classification_input += " " + " ".join(vision_labels)
            
        if "category" in self.conversation_state.slots and self.conversation_state.slots["category"]:
            classification_input += f" {self.conversation_state.slots['category']}"
        if "job_type" in self.conversation_state.slots and self.conversation_state.slots["job_type"]:
            classification_input += f" {self.conversation_state.slots['job_type']}"
            
        classification = classify(classification_input)
        
        # Set default category if not provided
        if not self.conversation_state.slots.get("category"):
            self.conversation_state.slots["category"] = classification.get("category", "OTHER")
            
        # Create project in database
        project_id = await self._create_project(self.conversation_state.slots)
        
        # Associate this project with the conversation state
        self.conversation_state.project_id = project_id
        await self.memory.save_state(self.conversation_state)
        
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
        # Add question to conversation history
        self.conversation_state.add_user_message(question)
        
        # TODO: Enhanced answer_question with memory and vision context
        response = "I'll need to look that up for you."
        
        # Add response to conversation history
        self.conversation_state.add_assistant_message(response)
        
        # Save conversation state
        await self.memory.save_state(self.conversation_state)
        
        return response
    
    async def create_project(self, description: str, images: Optional[List[Dict[str, Any]]] = None,
                         category: Optional[str] = None, urgency: Optional[str] = None,
                         vision_context: Optional[Dict[str, Any]] = None) -> str:
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
            "homeowner_id": self.user_id,
            "category": category or cls["category"],
            "confidence": cls["confidence"],
        }
        
        try:
            pid = repo.save_project(row)
            if images:
                repo.save_project_photos(pid, images)
                
                # Save vision metadata for each image if available
                if vision_context:
                    for img_name, metadata in vision_context.items():
                        if any(img.get("path") == img_name for img in images):
                            await save_photo_meta(pid, img_name, metadata)
                            
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope --------------------------
        payload = {"project_id": pid, "homeowner_id": row["homeowner_id"]}
        send_envelope("project.created", payload, "homeowner_agent")
        return pid
    
    # -------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------
    async def _process_images(self, image_paths: List[Path]) -> dict[str, Any]:
        '''Process images through vision analysis and slot filling.'''
        try:
            # Convert paths to strings
            path_strings = [str(p) for p in image_paths]
            
            # Process each image with Gemini Vision Analysis
            results = await asyncio.gather(*[gemini_analyse(path) for path in path_strings])
            
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
        
        # Extract vision context if present
        vision_context = None
        if hasattr(self.conversation_state, 'vision_context'):
            vision_context = self.conversation_state.vision_context
        
        # Format project data for database
        project_data = {
            "homeowner_id": self.user_id,
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
                    
                    # Save vision metadata for each image if available
                    if vision_context:
                        for img_path, meta in vision_context.items():
                            for img in image_data:
                                if img_path == img.get("path") or img_path.endswith(img.get("path", "")):
                                    await save_photo_meta(pid, img.get("path"), meta)
                                    break
                    
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope -------------------------
        payload = {"project_id": pid, "homeowner_id": project_data["homeowner_id"]}
        send_envelope("project.created", payload)
        return pid