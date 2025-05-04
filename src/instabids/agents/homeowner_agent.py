"""HomeownerAgent with slot-filling for project details."""
from __future__ import annotations
from pathlib import Path
from typing import List, Any, Dict, Set, Optional
import logging
import re

from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools
from instabids.tools.vision_tool_plus import analyse as vision_call
from memory.persistent_memory import PersistentMemory
from memory.conversation_state import ConversationState
from instabids.data import project_repo as repo
from instabids.data.pref_repo import get_pref, upsert_pref, get_prefs
from instabids.agents.job_classifier import classify
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
            if isinstance(v, dict) and "labels" in v:
                vision_tags.extend(v["labels"])
    
    return classify(description, vision_tags)


class HomeownerAgent(LlmAgent):
    """Agent for helping homeowners gather project details."""

    def __init__(self, project_id: str = None, memory=None):
        """
        Initialize the HomeownerAgent.
        
        Args:
            project_id: Optional project ID to load existing data
            memory: Optional memory instance to use
        """
        super().__init__()
        self.project_id = project_id
        
        # Initialize memory with user preferences if available
        if project_id and not memory:
            try:
                project = repo.get_project(project_id)
                if project and "homeowner_id" in project:
                    # Preload preferences for this user
                    user_prefs = get_prefs(project["homeowner_id"])
                    memory = PersistentMemory(project_id, initial_state=user_prefs)
            except Exception as e:
                logger.error(f"Failed to load preferences for project {project_id}: {e}")
        
        # Fall back to default memory if needed
        self.memory = memory or PersistentMemory(project_id) if project_id else ConversationState()
        
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
            self.memory.update(form_data)
        
        # 2) Process vision context if images provided
        vision_context = {}
        images = input_data.get("images", [])
        if images:
            for i, img_data in enumerate(images):
                try:
                    # Save the image to a temporary file
                    temp_dir = Path("/tmp/instabids")
                    temp_dir.mkdir(exist_ok=True)
                    p = temp_dir / f"img_{i}.jpg"
                    
                    with open(p, "wb") as f:
                        f.write(img_data)
                    
                    # Analyze the image using the enhanced vision tool
                    result = await vision_call(str(p))
                    vision_context[f"image_{i}"] = result
                    
                except Exception as e:
                    logger.error(f"Vision API error: {e}")
        
        # Create user message for the LLM
        user_msg = {"text": description or "", "vision_context": vision_context}
        
        # 3) Process the user message
        response = await self.chat(user_msg)
        
        # 4) Classify job type & urgency (simple rule-based for v1)
        classification = classify_job(description or "", vision_context)
        
        # 5) Check if we have all required information
        missing = set(REQUIRED_SLOTS) - set(self.memory.keys())
        
        # If we have budget information, sync it to user preferences
        if "budget_range" in self.memory and user_id:
            budget_range = self.memory.get("budget_range")
            if budget_range:
                # Store budget preference with high confidence (0.9)
                upsert_pref(user_id, "budget_range", budget_range, confidence=0.9)
        
        if not missing:
            # We have all the information, create a project
            project_id = await self._create_project(self.memory)
            return {
                "need_more": False,
                "project_id": project_id,
                "message": "Great! I have all the information I need to create your project."
            }
        
        # 6) If we're still missing information, ask for it
        next_q = _next_question(missing)
        
        return {
            "need_more": True,
            "follow_up": next_q,
            "collected": {k: v for k, v in self.memory.items() if k in REQUIRED_SLOTS}
        }

    async def _create_project(self, memory: Dict[str, Any]) -> str:
        """
        Create a project with the collected information.
        
        Args:
            memory: Dictionary containing project details
            
        Returns:
            Project ID
        """
        # Extract relevant information
        images = memory.get("images", [])
        user_id = memory.get("user_id", "TODO_user_id")
        
        # Prepare project data
        project_data = {
            "homeowner_id": user_id,
            "title": memory.get("title", memory.get("description", "")[:80]),
            "description": memory.get("description", ""),
            "category": memory.get("category", "").lower(),
            "job_type": memory.get("job_type", ""),
            "location": memory.get("location", ""),
            "budget_range": memory.get("budget_range", ""),
            "timeline": memory.get("timeline", ""),
            "group_bidding": memory.get("group_bidding", "no").lower() == "yes",
        }
        
        # Sync important preferences to the user's profile
        if user_id != "TODO_user_id":
            # Store preferences with high confidence (0.9)
            for key in ["budget_range", "location", "timeline"]:
                if key in memory and memory[key]:
                    upsert_pref(user_id, key, memory[key], confidence=0.9)
        
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
        vision_tags: list[str] = []
        if images:
            for img in images:
                if "labels" in img:
                    vision_tags.extend(img["labels"])
                elif "tag" in img:
                    vision_tags.append(img["tag"])
                    
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