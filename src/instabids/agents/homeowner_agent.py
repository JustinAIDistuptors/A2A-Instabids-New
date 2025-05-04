"""HomeownerAgent with slot-filling for project details."""
from __future__ import annotations
from pathlib import Path
from typing import List, Any, Dict, Set, Optional
import logging
import re
import uuid

from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools, openai_vision_tool
from memory.persistent_memory import PersistentMemory
from memory.conversation_state import ConversationState
from instabids.data import project_repo as repo
from instabids.data.pref_repo import get_pref, upsert_pref
from instabids.agents.job_classifier import classify
from instabids.agents.bidcard_agent import BidCardAgent
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
        ("group_bidding", "Would you like to enable group bidding for potential discounts?"),
    ]
    for slot, question in order:
        if slot in missing:
            return question
    return "Can you tell me more about your project?"

class HomeownerAgent(LlmAgent):
    """Agent for homeowner conversations."""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize the agent."""
        super().__init__()
        self.memory = {}
        self.project_id = project_id
        self.bid_card_agent = BidCardAgent(project_id)
        
        # Load existing project data if available
        if project_id:
            try:
                project_data = repo.get_project(project_id)
                if project_data:
                    self.memory.update(project_data)
            except Exception as e:
                logger.error(f"Error loading project data: {e}")

    async def process_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user input and update memory.
        
        Args:
            data: Input data containing text, audio, or form_data
            
        Returns:
            Response with follow-up question or confirmation
        """
        user_id = data.get("user_id", "")
        text = data.get("text", "")
        audio = data.get("audio")
        form_data = data.get("form_data", {})
        
        # Process form data if available
        if form_data:
            self.memory.update(form_data)
            
            # Check if we have enough information to create a bid card
            if self._has_required_info():
                # Create bid card if we have all required information
                try:
                    bid_card = self.bid_card_agent.create_bid_card_from_project(
                        homeowner_id=user_id,
                        project_data=self.memory
                    )
                    
                    # Emit bid card created event
                    send_envelope("bidcard.created", {
                        "bid_card_id": bid_card["id"],
                        "project_id": self.project_id,
                        "homeowner_id": user_id
                    })
                    
                    return {
                        "follow_up": "Great! I've created a bid card for your project. Contractors will be able to view it and submit bids.",
                        "need_more": False,
                        "bid_card_id": bid_card["id"],
                        "project_id": self.project_id
                    }
                except Exception as e:
                    logger.error(f"Error creating bid card: {e}")
                    return {
                        "follow_up": f"I couldn't create a bid card due to an error: {str(e)}. Can you provide more information?",
                        "need_more": True
                    }
        
        # Process text input
        if text:
            # Extract information from text
            self._extract_info(text)
            
            # Check if we have all required information
            missing = self._missing_slots()
            if missing:
                question = _next_question(missing)
                return {
                    "follow_up": question,
                    "need_more": True,
                    "missing": list(missing)
                }
            else:
                # Create bid card if we have all required information
                try:
                    bid_card = self.bid_card_agent.create_bid_card_from_project(
                        homeowner_id=user_id,
                        project_data=self.memory
                    )
                    
                    # Emit bid card created event
                    send_envelope("bidcard.created", {
                        "bid_card_id": bid_card["id"],
                        "project_id": self.project_id,
                        "homeowner_id": user_id
                    })
                    
                    return {
                        "follow_up": "Great! I've created a bid card for your project. Contractors will be able to view it and submit bids.",
                        "need_more": False,
                        "bid_card_id": bid_card["id"],
                        "project_id": self.project_id
                    }
                except Exception as e:
                    logger.error(f"Error creating bid card: {e}")
                    return {
                        "follow_up": f"I couldn't create a bid card due to an error: {str(e)}. Can you provide more information?",
                        "need_more": True
                    }
        
        # Default response if no text or form data
        return {
            "follow_up": "How can I help with your project today?",
            "need_more": True
        }

    def _extract_info(self, text: str) -> None:
        """Extract information from text and update memory."""
        # Extract budget range
        budget_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:-|to)\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        budget_match = re.search(budget_pattern, text)
        if budget_match:
            min_val = budget_match.group(1).replace(',', '')
            max_val = budget_match.group(2).replace(',', '')
            self.memory["budget_range"] = f"{min_val}-{max_val}"
        
        # Extract location
        location_patterns = [
            r'in\s+([A-Za-z\s]+,\s*[A-Za-z]{2})',
            r'at\s+([A-Za-z\s]+,\s*[A-Za-z]{2})',
            r'location\s+is\s+([A-Za-z\s]+,\s*[A-Za-z]{2})'
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, text)
            if location_match:
                self.memory["location"] = location_match.group(1)
                break
        
        # Extract timeline
        timeline_patterns = [
            r'by\s+(next\s+\w+|\w+\s+\d{1,2}(?:st|nd|rd|th)?)',
            r'in\s+(\d+\s+(?:days?|weeks?|months?))',
            r'(as\s+soon\s+as\s+possible|ASAP)',
            r'(next\s+(?:week|month|year))'
        ]
        for pattern in timeline_patterns:
            timeline_match = re.search(pattern, text, re.IGNORECASE)
            if timeline_match:
                self.memory["timeline"] = timeline_match.group(1)
                break
        
        # Extract group bidding preference
        if re.search(r'group\s+bidding', text, re.IGNORECASE):
            if re.search(r'(?:yes|enable|want|interested\s+in)\s+group\s+bidding', text, re.IGNORECASE):
                self.memory["group_bidding"] = True
            elif re.search(r'(?:no|disable|don\'t\s+want|not\s+interested\s+in)\s+group\s+bidding', text, re.IGNORECASE):
                self.memory["group_bidding"] = False

    def _missing_slots(self) -> Set[str]:
        """Return set of missing required slots."""
        return REQUIRED_SLOTS - set(self.memory.keys())

    def _has_required_info(self) -> bool:
        """Check if we have all required information."""
        return len(self._missing_slots()) == 0

    def start_project(self, description: str, images: Optional[List[Dict[str, Any]]] = None) -> str:
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
        
        # Generate a new project ID if not already set
        if not self.project_id:
            self.project_id = str(uuid.uuid4())
            
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
                    
                # Update project ID for bid card agent
                self.project_id = pid
                self.bid_card_agent.project_id = pid
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope -----------------------------------------
        payload = {"project_id": pid, "homeowner_id": row["homeowner_id"]}
        send_envelope("project.created", payload)
        
        # Update memory with project information
        self.memory.update({
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "job_type": row["category"]  # Default job_type to category until more specific
        })
        
        return pid


# ------------------------------------------------------------------
# listen for incoming events
@on_envelope("project.created")
async def _handle_project_created(evt: Dict[str, Any]) -> None:
    """Handle project created events."""
    project_id = evt.get("project_id")
    homeowner_id = evt.get("homeowner_id")
    
    if project_id and homeowner_id:
        # Initialize BidCardAgent for the new project
        bid_card_agent = BidCardAgent(project_id)
        
        # Log the event
        logger.info(f"Project created: {project_id} for homeowner {homeowner_id}")

@on_envelope("bid.accepted")
async def _handle_bid_accepted(evt: Dict[str, Any]) -> None:  # noqa: D401
    """Handle bid accepted events."""
    # placeholder: update memory, notify homeowner, etc.
    logger.info(f"Received bid.accepted event: {evt}")

@on_envelope("bidcard.created")
async def _handle_bidcard_created(evt: Dict[str, Any]) -> None:
    """Handle bid card created events."""
    bid_card_id = evt.get("bid_card_id")
    project_id = evt.get("project_id")
    homeowner_id = evt.get("homeowner_id")
    
    if bid_card_id and project_id and homeowner_id:
        # Log the event
        logger.info(f"Bid card created: {bid_card_id} for project {project_id}")
        
        # Notify contractors (placeholder)
        send_envelope("notification.contractors", {
            "type": "new_bid_card",
            "bid_card_id": bid_card_id,
            "project_id": project_id
        })