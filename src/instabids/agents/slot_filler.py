"""
Slot filling module for structured data collection in conversations.

This module provides utilities for tracking and filling required information slots
in a conversation, helping guide users through providing all necessary details.
"""
from __future__ import annotations
from typing import Dict, List, Any

# Define slots with their questions and any validation/extraction logic
SLOTS = {
    "title": {
        "q": "What would you like to call this project? (e.g., 'Living Room Window Replacement', 'Kitchen Faucet Repair')"
    },
    "category": {
        "q": "What category best fits this project? (e.g., repair, renovation, installation, maintenance, construction)",
        "options": ["repair", "renovation", "installation", "maintenance", "construction", "other"]
    },
    "description": { 
        "q": "Could you describe the project and what you need done in a bit more detail?"
    },
    "scope_summary": { 
        "q": "Can you provide some key details about the scope? For example, any specific measurements, materials, or items involved?"
    },
    "address": {
        "q": "What is the street address for the project?"
    },
    "city": {
        "q": "Which city is the project in?"
    },
    "state": {
        "q": "Which state?"
    },
    "zip_code": {
        "q": "And the zip code?"
    },
    "urgency": {
        "q": "How urgent is this project? (e.g., ASAP, within a week, within a month, flexible)",
    },
    "budget_range": {
        "q": "What budget range do you have in mind (e.g., $500-$1000, or even a rough estimate is fine)?"
    },
    "timeline": {
        "q": "When would you ideally like the work to start or be completed?"
    },
    "contact_preference": {
        "q": "How do you prefer to be contacted? (e.g., email, phone)",
    },
    "additional_notes": {
        "q": "Is there anything else you'd like to add about the project or your requirements?"
    }
}

def missing_slots(card: Dict[str, Any]) -> List[str]:
    """
    Return slots still empty, in priority order.
    
    Args:
        card: Dictionary containing slot values
        
    Returns:
        List of slot names that are still empty, in priority order
    """
    # Define the order in which slots should be filled
    order = [
        "title", "category", "description", "scope_summary",
        "address", "city", "state", "zip_code",
        "urgency", "budget_range", "timeline", 
        "contact_preference", "additional_notes"
    ]
    
    # Return slots that are empty or None
    return [s for s in order if not card.get(s)]

def validate_slot(slot_name: str, value: Any) -> bool:
    """
    Validate a slot value against any defined constraints.
    
    Args:
        slot_name: Name of the slot to validate
        value: Value to validate
        
    Returns:
        True if valid, False otherwise
    """
    slot_def = SLOTS.get(slot_name, {})
    
    # If the slot has defined options, check that the value is one of them
    if "options" in slot_def and value:
        return str(value).lower() in [opt.lower() for opt in slot_def["options"]]
    
    # For slots without specific validation, just check they're not empty
    return bool(value)

def get_next_question(card: Dict[str, Any]) -> str:
    """
    Get the next question to ask based on missing slots.
    
    Args:
        card: Dictionary containing slot values
        
    Returns:
        Question string to ask the user, or empty string if all slots are filled
    """
    missing = missing_slots(card)
    if not missing:
        return ""
    
    return SLOTS[missing[0]]["q"]