"""
Slot filling module for structured data collection in conversations.

This module provides utilities for tracking and filling required information slots
in a conversation, helping guide users through providing all necessary details.
"""
from __future__ import annotations
from typing import Dict, List, Any

# Define slots with their questions and any validation/extraction logic
SLOTS = {
    "category": {
        "q": "What category best fits this project (repair, renovation, installation, maintenance, construction, other)?",
        "options": ["repair", "renovation", "installation", "maintenance", "construction", "other"]
    },
    "job_type": {
        "q": "Which specific job is it? (e.g. roof repair, lawn mowing)"
    },
    "budget_range": {
        "q": "What budget range do you have in mind (rough estimate is fine)?"
    },
    "timeline": {
        "q": "When would you like the work to start and finish?"
    },
    "location": {
        "q": "Where is the project located?"
    },
    "group_bidding": {
        "q": "Are you open to group bidding to lower cost? (yes/no)",
        "options": ["yes", "no"]
    },
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
    order = ["category", "job_type", "budget_range", "timeline", "location", "group_bidding"]
    
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