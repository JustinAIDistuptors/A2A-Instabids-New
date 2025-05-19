"""Conversation state management for slot-filling dialogs."""

from typing import Dict, Any, List, Optional, Set
import json

class ConversationState:
    """Manages the state of a slot-filling conversation."""
    
    def __init__(self):
        """Initialize a new conversation state."""
        self.slots: Dict[str, Any] = {}
        self.required_slots: Set[str] = {
            "category",           # Project category (repair, renovation, etc.)
            "job_type",          # Specific job type
            "location",          # Where work will be performed
            "budget_range",      # Budget expectations
            "timeline",          # When work should be done
            "description"        # Detailed project description
        }
        self.slot_questions: Dict[str, str] = {
            "category": "What type of project are you looking for? (repair, renovation, installation, maintenance, or construction)",
            "job_type": "What specific job are you looking to have done?",
            "location": "Where will this work be performed? (Which room or area of your home?)",
            "budget_range": "Do you have a budget range in mind for this project?",
            "timeline": "When would you like this project to be completed?",
            "description": "Can you provide some additional details about your project?"
        }
        self.slot_priorities: Dict[str, int] = {
            "category": 1,
            "job_type": 2,
            "location": 3,
            "description": 4,
            "budget_range": 5,
            "timeline": 6
        }
        self.user_inputs: List[str] = []
    
    def add_user_input(self, user_input: str) -> None:
        """Add user input to the conversation history."""
        self.user_inputs.append(user_input)
        self._extract_slots_from_input(user_input)
    
    def _extract_slots_from_input(self, user_input: str) -> None:
        """Extract slot values from user input using simple heuristics."""
        # Simple keyword-based extraction (to be improved with NLP)
        text = user_input.lower()
        
        # Category extraction
        if "repair" in text:
            self.slots["category"] = "repair"
        elif "renovat" in text or "remodel" in text:
            self.slots["category"] = "renovation"
        elif "install" in text:
            self.slots["category"] = "installation"
        elif "maintenance" in text or "clean" in text or "service" in text:
            self.slots["category"] = "maintenance"
        elif "build" in text or "construct" in text:
            self.slots["category"] = "construction"
        
        # Budget extraction - look for dollar amounts
        import re
        budget_pattern = r'\$?(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\s*(?:k|thousand|K)?'
        budget_matches = re.findall(budget_pattern, text)
        if budget_matches:
            # Convert to numeric value
            try:
                amount = budget_matches[0].replace(',', '')
                # Handle 'k' or 'thousand' suffix
                if 'k' in text or 'thousand' in text:
                    amount = float(amount) * 1000
                self.slots["budget_range"] = f"${float(amount):.2f}" # Ensure two decimal places for currency
            except ValueError:
                pass # Failed to convert amount
        
        # Timeline extraction - look for dates or time references
        if any(word in text for word in ["urgent", "emergency", "immediately", "asap"]):
            self.slots["timeline"] = "Urgent / ASAP"
        elif any(word in text for word in ["week", "weeks"]):
            self.slots["timeline"] = "Within weeks"
        elif any(word in text for word in ["month", "months"]):
            self.slots["timeline"] = "Within months"
        
        # Location extraction - look for room names
        rooms = ["bathroom", "kitchen", "bedroom", "living room", "basement", 
                 "attic", "garage", "yard", "driveway", "roof", "outside", "exterior"]
        for room in rooms:
            if room in text:
                self.slots["location"] = room.title()
                break
        
        # If no specific slots were extracted, set the description if empty and it's not a command
        # This heuristic might need refinement based on actual interaction patterns.
        if "description" not in self.slots and user_input.strip() and not any(self.slots.get(s) for s in ["category", "job_type", "location"]):
            self.slots["description"] = user_input
    
    def get_next_slot(self) -> Optional[str]:
        """Get the next slot that needs to be filled, based on priority."""
        missing_slots = self.required_slots - set(self.slots.keys())
        if not missing_slots:
            return None
            
        # Return the highest priority missing slot
        return min(missing_slots, key=lambda slot: self.slot_priorities.get(slot, 999))
    
    def get_question_for_slot(self, slot: str) -> str:
        """Get the question to ask for a specific slot."""
        return self.slot_questions.get(slot, f"Can you tell me about the {slot.replace('_', ' ')}?")
    
    def is_complete(self) -> bool:
        """Check if all required slots are filled."""
        return self.required_slots.issubset(set(self.slots.keys()))
    
    def get_slots(self) -> Dict[str, Any]:
        """Get all filled slots."""
        return self.slots
    
    def to_json(self) -> str:
        """Convert state to JSON for storage."""
        return json.dumps({
            "slots": self.slots,
            "user_inputs": self.user_inputs
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ConversationState':
        """Create state object from JSON."""
        try:
            data = json.loads(json_str)
            state = cls()
            state.slots = data.get("slots", {})
            state.user_inputs = data.get("user_inputs", [])
            return state
        except json.JSONDecodeError:
            # Handle cases where json_str is not valid JSON, perhaps return a new empty state or log error
            # For now, returning a new empty state
            return cls()