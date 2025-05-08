"""Tests for the slot filler module."""
import pytest
from instabids.agents.slot_filler import SLOTS, missing_slots, validate_slot, get_next_question

def test_slots_definition():
    """Test that slot definitions are properly structured."""
    assert "category" in SLOTS
    assert "job_type" in SLOTS
    assert "budget_range" in SLOTS
    assert "timeline" in SLOTS
    assert "location" in SLOTS
    assert "group_bidding" in SLOTS
    
    # Each slot should have a question
    for slot, definition in SLOTS.items():
        assert "q" in definition
        assert definition["q"]
        
    # Some slots should have options
    assert "options" in SLOTS["category"]
    assert "options" in SLOTS["group_bidding"]

def test_missing_slots_all_empty():
    """Test missing_slots when all slots are empty."""
    empty_card = {}
    result = missing_slots(empty_card)
    
    # Should return all slots in priority order
    assert len(result) == 6
    assert result[0] == "category"  # First slot to be filled
    assert "group_bidding" in result  # Should be included

def test_missing_slots_partially_filled():
    """Test missing_slots when some slots are filled."""
    partial_card = {
        "category": "renovation",
        "job_type": "bathroom remodel"
    }
    
    result = missing_slots(partial_card)
    
    assert len(result) == 4
    assert "category" not in result
    assert "job_type" not in result
    assert "budget_range" in result
    assert "timeline" in result
    assert "location" in result
    assert "group_bidding" in result

def test_missing_slots_all_filled():
    """Test missing_slots when all slots are filled."""
    complete_card = {
        "category": "renovation",
        "job_type": "bathroom remodel",
        "budget_range": "$5000-7000",
        "timeline": "Next month",
        "location": "Bathroom",
        "group_bidding": "yes"
    }
    
    result = missing_slots(complete_card)
    
    assert result == []  # No missing slots

def test_validate_slot_with_options():
    """Test slot validation for slots with fixed options."""
    # Valid options
    assert validate_slot("category", "renovation")
    assert validate_slot("category", "Renovation")  # Case insensitive
    assert validate_slot("group_bidding", "yes")
    
    # Invalid options
    assert not validate_slot("category", "unknown_category")
    assert not validate_slot("group_bidding", "maybe")

def test_validate_slot_without_options():
    """Test slot validation for slots without fixed options."""
    # Any non-empty value should be valid
    assert validate_slot("job_type", "bathroom remodel")
    assert validate_slot("budget_range", "$5000")
    assert validate_slot("location", "kitchen")
    
    # Empty values should be invalid
    assert not validate_slot("job_type", "")
    assert not validate_slot("budget_range", None)

def test_get_next_question_empty():
    """Test get_next_question with empty card."""
    card = {}
    question = get_next_question(card)
    
    assert question == SLOTS["category"]["q"]

def test_get_next_question_partially_filled():
    """Test get_next_question with partially filled card."""
    card = {
        "category": "renovation",
        "job_type": "bathroom remodel"
    }
    
    question = get_next_question(card)
    
    assert question == SLOTS["budget_range"]["q"]

def test_get_next_question_complete():
    """Test get_next_question with complete card."""
    complete_card = {
        "category": "renovation",
        "job_type": "bathroom remodel",
        "budget_range": "$5000-7000",
        "timeline": "Next month",
        "location": "Bathroom",
        "group_bidding": "yes"
    }
    
    question = get_next_question(complete_card)
    
    assert question == ""  # No more questions needed