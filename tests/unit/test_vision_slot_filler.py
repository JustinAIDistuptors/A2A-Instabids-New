'''
Tests for the vision-enhanced slot filler functionality.

Tests the integration between the slot filler module and vision analysis,
including extracting slot values from image analysis results.
'''
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json
from pathlib import Path

from instabids.agents.slot_filler import (
    missing_slots, validate_slot, get_next_question,
    process_image_for_slots, update_card_from_images
)

# Sample vision analysis results
SAMPLE_ANALYSIS = {
    "labels": ["roof", "damage", "shingles", "repair"],
    "description": "Damaged roof shingles with visible wear and tear",
    "damage_assessment": "Moderate damage to roof shingles with potential water infiltration",
    "dimensions": (800, 600)
}

@pytest.fixture
def sample_card():
    return {
        "category": "repair",
        "job_type": "roof repair",
        "budget_range": "$5000-$8000"
    }

@pytest.fixture
def sample_image_path():
    """Create a path for a sample image file."""
    return "/tmp/test_roof_image.jpg"

# Test the basic slot filler functionality
def test_missing_slots(sample_card):
    """Test identifying which slots are missing."""
    missing = missing_slots(sample_card)
    assert "damage_assessment" in missing
    assert "timeline" in missing
    assert "location" in missing
    assert "category" not in missing

def test_validate_slot():
    """Test validating slot values."""
    # Test category validation
    assert validate_slot("category", "repair")
    assert validate_slot("category", "other")
    assert not validate_slot("category", "unknown")
    
    # Test empty values
    assert not validate_slot("job_type", "")
    assert not validate_slot("job_type", None)

def test_get_next_question(sample_card):
    """Test getting the next question to ask."""
    question = get_next_question(sample_card)
    assert "damage" in question.lower()

# Test the vision integration
@pytest.mark.asyncio
async def test_process_image_for_slots(sample_image_path):
    """Test processing an image to extract slot values."""
    # Mock the vision tool functions
    with patch('instabids.agents.slot_filler.validate_image_for_bid_card', new_callable=AsyncMock) as mock_validate:
        with patch('instabids.agents.slot_filler.Path.exists', return_value=True):
            # Set up the mock response
            mock_validate.return_value = {
                "is_valid": True,
                "analysis": SAMPLE_ANALYSIS,
                "recommendation": "Image is suitable for bid card"
            }
            
            # Call the function
            result = await process_image_for_slots(sample_image_path)
            
            # Verify the result
            assert "category" in result
            assert result["category"] == "repair"
            assert "job_type" in result
            assert "roof" in result["job_type"]
            assert "damage_assessment" in result
            assert "project_images" in result
            assert sample_image_path in result["project_images"]
            
            # Verify the vision function was called
            mock_validate.assert_called_once_with(sample_image_path)

@pytest.mark.asyncio
async def test_update_card_from_images(sample_card, sample_image_path):
    """Test updating a card with information from images."""
    # Mock the process_image_for_slots function
    with patch('instabids.agents.slot_filler.process_image_for_slots', new_callable=AsyncMock) as mock_process:
        # Set up the mock response
        mock_process.return_value = {
            "category": "repair",
            "job_type": "roof damage",
            "damage_assessment": "Moderate damage to roof shingles",
            "project_images": [sample_image_path]
        }
        
        # Call the function
        result = await update_card_from_images(sample_card, [sample_image_path])
        
        # Verify the result
        assert result["category"] == "repair"  # Unchanged from original card
        assert result["job_type"] == "roof repair"  # Unchanged from original card
        assert result["budget_range"] == "$5000-$8000"  # Unchanged from original card
        assert "damage_assessment" in result  # New from image
        assert result["damage_assessment"] == "Moderate damage to roof shingles"
        assert "project_images" in result
        assert sample_image_path in result["project_images"]
        
        # Verify the process function was called
        mock_process.assert_called_once_with(sample_image_path)

@pytest.mark.asyncio
async def test_update_card_from_multiple_images(sample_card):
    """Test updating a card with information from multiple images."""
    image_paths = ["/tmp/image1.jpg", "/tmp/image2.jpg"]
    
    # Mock the process_image_for_slots function with different results for each image
    with patch('instabids.agents.slot_filler.process_image_for_slots', new_callable=AsyncMock) as mock_process:
        def side_effect(path):
            if path == "/tmp/image1.jpg":
                return {
                    "category": "repair",
                    "job_type": "roof damage",
                    "project_images": ["/tmp/image1.jpg"]
                }
            else:  # image2.jpg
                return {
                    "damage_assessment": "Water damage visible on ceiling",
                    "project_images": ["/tmp/image2.jpg"]
                }
        
        mock_process.side_effect = side_effect
        
        # Call the function
        result = await update_card_from_images(sample_card, image_paths)
        
        # Verify the result has information from both images
        assert result["category"] == "repair"
        assert result["job_type"] == "roof repair"
        assert result["damage_assessment"] == "Water damage visible on ceiling"
        assert set(result["project_images"]) == set(image_paths)
        
        # Verify the process function was called for each image
        assert mock_process.call_count == 2

@pytest.mark.asyncio
async def test_invalid_image(sample_image_path):
    """Test handling an invalid image."""
    with patch('instabids.agents.slot_filler.validate_image_for_bid_card', new_callable=AsyncMock) as mock_validate:
        # Set up the mock response for an invalid image
        mock_validate.return_value = {
            "is_valid": False,
            "analysis": {},
            "recommendation": "Image may not be relevant to construction or repair"
        }
        
        # Call the function
        result = await process_image_for_slots(sample_image_path)
        
        # Verify the result is empty
        assert result == {}
        
        # Verify the vision function was called
        mock_validate.assert_called_once_with(sample_image_path)
