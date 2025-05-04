"""
Unit tests for the slot filler module.

Tests the functionality of the slot filler module, including:
- Missing slot detection in priority order
- Slot validation
- Next question generation
"""
import pytest
from instabids.agents.slot_filler import missing_slots, validate_slot, get_next_question, SLOTS

def test_missing_slots_empty():
    """Test missing_slots with an empty card."""
    card = {}
    missing = missing_slots(card)
    assert len(missing) == 6
    assert missing[0] == "category"
    assert "job_type" in missing
    assert "budget_range" in missing
    assert "timeline" in missing
    assert "location" in missing
    assert "group_bidding" in missing

def test_missing_slots_partial():
    """Test missing_slots with a partially filled card."""
    card = {"category": "repair", "job_type": "roof repair"}
    missing = missing_slots(card)
    assert len(missing) == 4
    assert missing[0] == "budget_range"
    assert "timeline" in missing
    assert "location" in missing
    assert "group_bidding" in missing

def test_missing_slots_complete():
    """Test missing_slots with a completely filled card."""
    card = {
        "category": "repair",
        "job_type": "roof repair",
        "budget_range": "$1000-$2000",
        "timeline": "Next week",
        "location": "123 Main St",
        "group_bidding": "yes"
    }
    missing = missing_slots(card)
    assert len(missing) == 0

def test_missing_order():
    """Test that missing slots are returned in priority order."""
    card = {"category": "repair", "job_type": ""}
    assert missing_slots(card)[0] == "job_type"
    
    card = {"category": "", "job_type": "roof repair"}
    assert missing_slots(card)[0] == "category"
    
    card = {"category": "repair", "job_type": "roof repair", "budget_range": ""}
    assert missing_slots(card)[0] == "budget_range"

def test_validate_slot_with_options():
    """Test slot validation for slots with defined options."""
    # Test category validation
    assert validate_slot("category", "repair") is True
    assert validate_slot("category", "REPAIR") is True  # Case insensitive
    assert validate_slot("category", "unknown") is False
    
    # Test group_bidding validation
    assert validate_slot("group_bidding", "yes") is True
    assert validate_slot("group_bidding", "no") is True
    assert validate_slot("group_bidding", "maybe") is False

def test_validate_slot_without_options():
    """Test slot validation for slots without defined options."""
    # These slots just check for non-empty values
    assert validate_slot("job_type", "roof repair") is True
    assert validate_slot("job_type", "") is False
    assert validate_slot("budget_range", "$1000-$2000") is True
    assert validate_slot("timeline", "Next week") is True

def test_get_next_question():
    """Test getting the next question based on missing slots."""
    # Empty card should return the category question
    card = {}
    assert get_next_question(card) == SLOTS["category"]["q"]
    
    # Card with category should return job_type question
    card = {"category": "repair"}
    assert get_next_question(card) == SLOTS["job_type"]["q"]
    
    # Complete card should return empty string
    card = {
        "category": "repair",
        "job_type": "roof repair",
        "budget_range": "$1000-$2000",
        "timeline": "Next week",
        "location": "123 Main St",
        "group_bidding": "yes"
    }
    assert get_next_question(card) == ""