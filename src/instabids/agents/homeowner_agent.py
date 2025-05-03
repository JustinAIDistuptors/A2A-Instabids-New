"""HomeownerAgent with slot-filling for project details."""
from __future__ import annotations
from pathlib import Path
from typing import List, Any, Dict, Set, Optional
import logging
import re

from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools, openai_vision_tool
from memory.persistent_memory import PersistentMemory
from memory.conversation_state import ConversationState
from instabids.data import project_repo as repo
from instabids.data.pref_repo import get_pref, upsert_pref
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
        ("budget_range", "Rough budget range?"),
        ("timeline", "Preferred start and end dates?"),
        ("group_bidding", "Are you open to bundling with nearby jobs to save costs?"),
    ]
    for slot, q in order:
        if slot in missing:
            return q
    return "Anything else I should know about your project?"

# Load system prompt from file
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "homeowner_agent.md").read_text()

class HomeownerAgent(LlmAgent):
    """Agent that helps homeowners create and manage projects."""

    def __init__(self, memory: Optional[PersistentMemory] = None):
        super().__init__(name="HomeownerAgent", tools=[*supabase_tools, openai_vision_tool], system_prompt=SYSTEM_PROMPT, memory=memory or PersistentMemory())
        
    async def gather_project_info(self, user_id: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Gather project information through slot-filling.
        
        Args:
            user_id: User ID for preference lookup/storage
            description: Optional initial project description
            
        Returns:
            Dict with project info or next question
        """
        state = ConversationState(self.memory)
        missing = REQUIRED_SLOTS - set(state.get_slots().keys())
        
        if description:
            state.set_slot("description", description)
            state.set_slot("title", description[:80])
            # naive preference learn: if user mentions budget "$10k" store as default
            m = re.search(r"\$(\d[\d,]*)", description)
            if m:
                upsert_pref(user_id, "default_budget", int(m.group(1).replace(",", "")))
        
        if missing:
            # try filling from saved preferences
            if "budget_range" in missing:
                if (default := get_pref(user_id, "default_budget")):
                    state.set_slot("budget_range", [0, default])
                    missing.remove("budget_range")
            if missing:
                return {"need_more": True, "question": _next_question(missing)}
        
        # All slots filled
        return {
            "need_more": False,
            "project": state.get_slots()
        }
    
    async def answer_question(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Answer a homeowner's question about their project.
        
        Args:
            question: The homeowner's question
            context: Optional context information
            
        Returns:
            Agent's response
        """
        # TODO: Implement question answering logic
        return f"I'll help you with: {question}"
    
    async def create_project(self, description: str, images: Optional[List[Dict[str, Any]]] = None) -> str:
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