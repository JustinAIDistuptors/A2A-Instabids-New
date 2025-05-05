"""HomeownerAgent – conversational slot-filling → bid-card creation."""
from __future__ import annotations
import logging, re, uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from google.adk import LlmAgent, enable_tracing
# Assuming these imports are correct based on your project structure
# from instabids.tools import supabase_tools, openai_vision_tool # Not in bundle, might be needed
# from memory.persistent_memory import PersistentMemory # Not in bundle, might be needed
from instabids.data import project_repo as repo
from instabids.agents.job_classifier import classify # Assuming this exists
from instabids.agents.bidcard_agent import BidCardAgent # Assumes bidcard_agent.py is correct
from instabids.a2a_comm import send_envelope, on_envelope # Assuming this exists

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
    for slot, q in order:
        if slot in missing:
            return q
    # Ensure title is asked if missing, though it might be derived differently
    if "title" in missing:
         return "What would you like to call this project?"
    return "Can you tell me more about your project?"

class HomeownerAgent(LlmAgent):
    """Converses with homeowner, fills slots, delegates to BidCardAgent."""
    def __init__(self, project_id: Optional[str] = None) -> None:
        # Simplified init based on bundle - may need to add back tools/memory if required by LlmAgent
        super().__init__(
             name="HomeownerAgent",
             # tools=[openai_vision_tool, *supabase_tools], # Removed based on bundle, add back if needed
             system_prompt="You help homeowners create complete bid cards by asking relevant questions.",
             # memory=PersistentMemory(), # Removed based on bundle, add back if needed
        )
        self.project_id = project_id
        # Assuming BidCardAgent doesn't need project_id at init based on bundle agent code
        self.bid_card_agent = BidCardAgent()
        self.memory_store: Dict[str, Any] = {}   # conversational scratch

        # Load existing project data if project_id is provided (optional enhancement)
        # if project_id:
        #    try:
        #        project_data = repo.get_project(project_id) # Assuming get_project exists
        #        if project_data:
        #            self.memory_store.update(project_data) # Pre-fill memory
        #    except Exception as e:
        #        logger.error(f"Error loading project data {project_id}: {e}")


    # ───────────────────────────────────────────

    async def process_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Entry point from UI / API. data may contain: text, form_data."""
        user_id = data.get("user_id", "") # Make sure user_id is passed in
        if not user_id:
             # Handle missing user_id appropriately, maybe raise error or default
             logger.warning("user_id not provided in process_input data")
             # For now, let's use a placeholder, but this should be fixed
             user_id = "placeholder_user_id"

        text     = data.get("text", "")
        form     = data.get("form_data", {})

        # merge form directly into scratch memory
        if form:
            logger.debug(f"Updating memory with form data: {form}")
            self.memory_store.update(form)

        if text:
            logger.debug(f"Processing text input: {text}")
            self._extract_info(text)

        # --- Ensure essential fields exist before checking missing ---
        # Title might come from text or form, ensure it's handled
        if "title" not in self.memory_store and "description" in self.memory_store:
             self.memory_store["title"] = self.memory_store["description"][:80] # Default title
        if "title" not in self.memory_store and text:
             self.memory_store["title"] = text[:80] # Fallback title from text


        # --- Check for missing slots ---
        missing = self._missing_slots()
        if missing:
            question = _next_question(missing)
            logger.info(f"Missing slots: {missing}. Asking: {question}")
            return {"need_more": True, "follow_up": question, "missing": list(missing)}

        # --- All slots filled → create bid-card ---
        logger.info("All required slots filled. Creating bid card.")
        try:
            # Ensure project_id exists before creating bid card
            if not self.project_id:
                 # Maybe create a project first if necessary, or require it
                 # For now, let's create a dummy one if missing
                 logger.warning("No project_id set for HomeownerAgent, generating one.")
                 self.project_id = str(uuid.uuid4())
                 # Potentially save a minimal project entry here?
                 # repo.save_project(...)

            # Prepare data for BidCard Pydantic model
            # This assumes BidCardAgent.create_bid_card_from_project expects project_data dict
            # Let's adapt to call generate directly if BidCardAgent is simpler per bundle
            bid_card_data = {
                 "homeowner_id": user_id,
                 "project_id": self.project_id,
                 "category": self.memory_store.get("category", "other"), # Ensure category exists
                 "job_type": self.memory_store.get("job_type", "Unknown"), # Ensure job_type exists
                 "budget_min": self.memory_store.get("budget_min"),
                 "budget_max": self.memory_store.get("budget_max"),
                 "timeline": self.memory_store.get("timeline"),
                 "location": self.memory_store.get("location"),
                 "group_bidding": self.memory_store.get("group_bidding", False),
                 "details": self.memory_store.get("details", {}) # Pass any extra details
            }

            # Parse budget_range if it exists
            if "budget_range" in self.memory_store:
                 min_val, max_val = self._parse_budget(self.memory_store["budget_range"])
                 bid_card_data["budget_min"] = min_val
                 bid_card_data["budget_max"] = max_val

            # Add any remaining memory items to details
            for key, value in self.memory_store.items():
                 if key not in bid_card_data and key not in REQUIRED_SLOTS:
                      bid_card_data["details"][key] = value


            # Create BidCard object (assuming BidCardAgent expects this)
            from instabids.agents.bidcard_agent import BidCard # Import locally if needed
            bid_card_obj = BidCard(**bid_card_data)

            # Call the agent to generate/save the bid card
            # Assuming bid_agent.generate saves and returns ID based on BC-503 bundle desc
            bid_id = await self.bid_card_agent.generate(bid_card_obj)

            logger.info(f"Bid card created with ID: {bid_id}")
            send_envelope("bidcard.created", {
                "bid_card_id": bid_id,
                "project_id":  self.project_id,
                "homeowner_id": user_id,
            })
            self.memory_store = {} # Clear memory after success
            return {
                "need_more": False,
                "follow_up": "Great! Your project bid card is live for contractors.",
                "bid_card_id": bid_id,
                "project_id":  self.project_id,
            }
        except Exception as e:
             logger.error(f"Error creating bid card: {e}", exc_info=True)
             return {
                  "need_more": True, # Indicate failure, maybe ask user to clarify
                  "follow_up": f"Sorry, I encountered an error creating the bid card: {e}. Could you please try rephrasing?"
             }


    # ───────────── info extraction helpers ─────────────
    def _extract_info(self, text: str) -> None:
        # very naive regexes – MVP
        text_lower = text.lower()
        if "group bidding" in text_lower:
            self.memory_store["group_bidding"] = "no" not in text_lower
            logger.debug(f"Extracted group_bidding: {self.memory_store['group_bidding']}")

        # Handle budget: $1,000 - $2,000 or $1000 to $2k etc.
        budget_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)\s*(?:-|to|through)\s*\$?([\d,k]+(?:\.\d{2})?)', text, re.IGNORECASE)
        if budget_match:
             min_str = budget_match.group(1).replace(',', '')
             max_str = budget_match.group(2).replace(',', '').replace('k', '000')
             self.memory_store["budget_range"] = f"{min_str}-{max_str}" # Store raw range string
             logger.debug(f"Extracted budget_range: {self.memory_store['budget_range']}")
             # Actual parsing happens just before creating BidCard

        # Handle location: "in City, ST" or "at Address, City, ST"
        loc_match = re.search(r'(?:in|at|location is)\s+([\w\s]+,\s*[A-Z]{2})', text, re.IGNORECASE)
        if loc_match:
            self.memory_store["location"] = loc_match.group(1).strip()
            logger.debug(f"Extracted location: {self.memory_store['location']}")

        # Handle timeline: "next week", "in 2 months", "ASAP"
        timeline_match = re.search(r'(?:timeline|by|in|within)\s+(next\s+\w+|(?:\d+|a\s+few)\s+(?:days?|weeks?|months?)|ASAP|as soon as possible)', text, re.IGNORECASE)
        if timeline_match:
            self.memory_store["timeline"] = timeline_match.group(1).strip()
            logger.debug(f"Extracted timeline: {self.memory_store['timeline']}")

        # Simplistic job_type extraction - assumes a descriptive sentence
        # More robust: Use LLM call or better NLP if needed
        if "job_type" not in self.memory_store:
             if any(kw in text_lower for kw in ["repair", "install", "renovat", "build", "construct", "maintain", "maintenance", "fix"]):
                  # Basic extraction - might grab too much/little
                  potential_job = text.strip()
                  # Try to find sentence boundary before setting
                  sentences = re.split(r'[.!?]', potential_job)
                  if sentences: potential_job = sentences[0] # Take first sentence
                  self.memory_store["job_type"] = potential_job[:150] # Limit length
                  logger.debug(f"Extracted job_type (simplistic): {self.memory_store['job_type']}")
                  # Also try to infer category if not present
                  if "category" not in self.memory_store:
                       # Requires BidCardAgent instance or separate mapping logic
                       # self.memory_store["category"] = self.bid_card_agent.map_category(self.memory_store["job_type"])
                       # logger.debug(f"Inferred category: {self.memory_store['category']}")
                       pass # Add category inference later if needed


    def _parse_budget(self, budget_range: str) -> tuple[Optional[float], Optional[float]]:
         """Parses budget range string like '1000-5000' into min/max floats."""
         try:
              parts = budget_range.replace(',', '').split('-')
              if len(parts) == 2:
                   min_val = float(parts[0].strip())
                   max_val = float(parts[1].strip())
                   return min_val, max_val
         except ValueError:
              logger.warning(f"Could not parse budget_range: {budget_range}")
         return None, None


    def _missing_slots(self) -> Set[str]:
         # Check memory_store against REQUIRED_SLOTS
         current_keys = set(self.memory_store.keys())
         # Special check for budget - budget_range implies budget_min/max
         if "budget_range" in current_keys:
              current_keys.add("budget_min") # Treat range as covering min/max conceptually
              current_keys.add("budget_max")
         return REQUIRED_SLOTS - current_keys

    def _has_required_info(self) -> bool:
        return not self._missing_slots()

# ───────────── A2A event listeners (placeholders) ─────────────
@on_envelope("bidcard.created")
async def _bidcard_created(evt: Dict[str, Any]) -> None:
    logger.info("Bid card created event received: %s", evt)
    # Potential actions: notify user via another channel, log analytics, etc.

# Add other listeners if needed (e.g., for bid.accepted)
# @on_envelope("bid.accepted")
# async def _handle_bid_accepted(evt: Dict[str, Any]) -> None:
#    logger.info(f"Received bid.accepted event: {evt}")
