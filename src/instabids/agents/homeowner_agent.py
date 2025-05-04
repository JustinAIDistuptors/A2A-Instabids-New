"""HomeownerAgent with slot-filling for project details."""
from __future__ import annotations
from pathlib import Path
from typing import List, Any, Dict, Set, Optional
import logging
import re

from google.adk import LlmAgent, enable_tracing
from google.adk.messages import UserMessage, AssistantMessage
from instabids.tools import supabase_tools, openai_vision_tool
from memory.persistent_memory import PersistentMemory
from memory.conversation_state import ConversationState
from instabids.data import project_repo as repo
from instabids.data.pref_repo import get_pref, upsert_pref
from instabids.agents.job_classifier import classify
from instabids.agents.slot_filler import missing_slots, SLOTS
from instabids.a2a_comm import send_envelope, on_envelope
from instabids.a2a.events import EVENT_SCHEMAS

# Set up logging
logger = logging.getLogger(__name__)
enable_tracing("stdout")

REQUIRED_SLOTS: Set[str] = {
    "title", "category", "job_type", "location",
    "budget_range", "timeline", "group_bidding",
}

def _next_question(missing: Set[str]) -> str:
    order = [
        ("category", "Is this a repair, renovation, installation, maintenance, or construction project?"),
        ("job_type", "What specific work is needed (e.g., roof repair, lawn mowing)?"),
        ("location", "Where will the work take place?"),
        ("budget_range", "What's your budget range for this project?"),
        ("timeline", "When would you like this work to be done?"),
        ("group_bidding", "Are you open to group bidding to potentially lower costs?"),
    ]
    for slot, question in order:
        if slot in missing:
            return question
    return ""

def classify_job(description: str, vision_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Classify job type and urgency from description.
    
    Args:
        description: Text description of the job
        vision_context: Optional vision analysis results
        
    Returns:
        Classification results
    """
    vision_tags = []
    if vision_context:
        for k, v in vision_context.items():
            if isinstance(v, dict) and "tag" in v:
                vision_tags.append(v["tag"])
    
    return classify(description, vision_tags)


class HomeownerAgent(LlmAgent):
    """Agent for helping homeowners gather project details."""

    def __init__(self, project_id: str = None):
        """
        Initialize the HomeownerAgent.
        
        Args:
            project_id: Optional project ID to load existing data
        """
        super().__init__()
        self.project_id = project_id
        self.memory = PersistentMemory(project_id) if project_id else ConversationState()
        
        # Load existing project data if available
        if project_id:
            try:
                project = repo.get_project(project_id)
                if project:
                    self.memory["project"] = project
            except Exception as e:
                logger.error(f"Failed to load project {project_id}: {e}")

    async def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user input and return agent response.
        
        Args:
            input_data: Dictionary containing user input
            
        Returns:
            Agent response
        """
        # 1) Extract input data
        text = input_data.get("text", "")
        audio = input_data.get("audio")
        form_data = input_data.get("form_data", {})
        user_id = input_data.get("user_id")
        
        # Handle audio input if provided
        description = None
        if audio:
            from instabids.tools.stt_tool import speech_to_text
            description = await speech_to_text(audio)
            if not description:
                return {"error": "Could not transcribe audio clearly. Please try again."}
        else:
            description = text
        
        # Handle form data if provided
        if form_data:
            # Update memory with form data
            bid_card = self.memory.get("bid_card", default={})
            bid_card.update(form_data)
            self.memory["bid_card"] = bid_card
        
        # 2) Process vision context if images provided
        vision_context = {}
        images = input_data.get("images", [])
        if images:
            for i, img_data in enumerate(images):
                try:
                    result = await openai_vision_tool.analyze_image(img_data)
                    vision_context[f"image_{i}"] = result
                except Exception as e:
                    logger.error(f"Vision API error: {e}")
        
        # Create user message for the LLM
        user_msg = UserMessage(text=description or "")
        
        # 3) fill bid_card dict from memory + this turn
        bid_card = {
            **self.memory.get("bid_card", default={}),
            "description": description or "",
        }
        for k, v in vision_context.items():
            bid_card.setdefault("images", []).append(v)

        need = missing_slots(bid_card)
        if need:
            q = SLOTS[need[0]]["q"]
            self.memory["bid_card"] = bid_card
            return {"need_more": True, "follow_up": q}

        classification = classify_job(bid_card["description"], vision_context)
        
        # 4) Store classification results
        bid_card["category"] = classification.get("category", bid_card.get("category", ""))
        bid_card["job_type"] = classification.get("job_type", bid_card.get("job_type", ""))
        self.memory["bid_card"] = bid_card
        
        # 5) Check if we have all required information
        if all(bid_card.get(slot) for slot in REQUIRED_SLOTS):
            # We have all the information, create a project
            project_id = await self._create_project(bid_card)
            return {
                "need_more": False,
                "project_id": project_id,
                "message": "Great! I have all the information I need to create your project."
            }
        
        # 6) If we're still missing information, ask for it
        missing = [slot for slot in REQUIRED_SLOTS if not bid_card.get(slot)]
        next_q = _next_question(set(missing))
        
        return {
            "need_more": True,
            "follow_up": next_q,
            "collected": {k: v for k, v in bid_card.items() if k in REQUIRED_SLOTS and v}
        }

    async def _create_project(self, bid_card: Dict[str, Any]) -> str:
        """
        Create a project with the collected information.
        
        Args:
            bid_card: Dictionary containing project details
            
        Returns:
            Project ID
        """
        # Extract relevant information
        images = bid_card.pop("images", [])
        
        # Prepare project data
        project_data = {
            "homeowner_id": bid_card.get("user_id", "TODO_user_id"),
            "title": bid_card.get("title", bid_card.get("description", "")[:80]),
            "description": bid_card.get("description", ""),
            "category": bid_card.get("category", "").lower(),
            "job_type": bid_card.get("job_type", ""),
            "location": bid_card.get("location", ""),
            "budget_range": bid_card.get("budget_range", ""),
            "timeline": bid_card.get("timeline", ""),
            "group_bidding": bid_card.get("group_bidding", "no").lower() == "yes",
        }
        
        try:
            with repo._Tx():
                pid = repo.save_project(project_data)
                if images:
                    repo.save_project_photos(pid, images)
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope -----------------------------------------
        payload = {"project_id": pid, "homeowner_id": project_data["homeowner_id"]}
        send_envelope("project.created", payload)
        return pid

    async def start_project(self, description: str, images: List[Dict[str, Any]] = None) -> str:
        """
        Start a new project with the collected information.
        
        Args:
            description: Project description
            images: Optional list of image data
            
        Returns:
            Project ID
        """
        vision_tags: list[str] = [img.get("tag", "") for img in images] if images else []
        cls = classify(description, vision_tags)
        row = {
            "homeowner_id": "TODO_user_id",
            "title": description[:80],
            "description": description,
            "category": cls["category"].lower(),
            "confidence": cls["confidence"],
        }
        try:
            with repo._Tx():
                pid = repo.save_project(row)
                if images:
                    repo.save_project_photos(pid, images)
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope -----------------------------------------
        payload = {"project_id": pid, "homeowner_id": row["homeowner_id"]}
        send_envelope("project.created", payload)
        return pid


# ------------------------------------------------------------------
# listen for incoming events (example)
@on_envelope("bid.accepted")
async def _handle_bid_accepted(evt: Dict[str, Any]) -> None:  # noqa: D401
    """Handle bid accepted events."""
    # placeholder: update memory, notify homeowner, etc.
    logger.info(f"Received bid.accepted event: {evt}")