"""HomeownerAgent now uses advanced classifier with confidence."""
from __future__ import annotations
from typing import List, Any, Optional, Dict
import logging

# Use instabids_google.adk instead of google.adk to fix import conflicts
from instabids_google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools, openai_vision_tool
from memory.persistent_memory import PersistentMemory
from instabids.data import project_repo as repo
from instabids.agents.job_classifier import classify
from instabids.a2a_comm import send_envelope, on_envelope
from instabids.a2a.events import EVENT_SCHEMAS

# Set up logging
logger = logging.getLogger(__name__)
enable_tracing("stdout")

class HomeownerAgent(LlmAgent):
    """
    Agent responsible for handling homeowner-related operations.
    
    This agent classifies projects, stores them in the database,
    and emits events when operations are completed successfully.
    """
    
    def __init__(self, memory: Optional[PersistentMemory] = None):
        """
        Initialize the HomeownerAgent.
        
        Args:
            memory: Optional persistent memory system
        """
        super().__init__(
            name="HomeownerAgent",
            tools=[*supabase_tools, openai_vision_tool],
            system_prompt=(
                "Classify homeowner projects, store them, emit events."
            ),
            memory=memory,
        )

    def start_project(self, description: str, images: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Start a new homeowner project with optional images.
        
        This method:
        1. Classifies the project based on description and image tags
        2. Saves the project to the database within a transaction
        3. Saves any associated project photos
        4. Emits an A2A event upon successful creation
        
        Args:
            description: Text description of the project
            images: Optional list of image metadata dictionaries
            
        Returns:
            str: The project ID of the created project
            
        Raises:
            Exception: If there's an error saving the project
        """
        vision_tags: List[str] = [img.get("tag", "") for img in images] if images else []
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
            # Log the error before re-raising
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