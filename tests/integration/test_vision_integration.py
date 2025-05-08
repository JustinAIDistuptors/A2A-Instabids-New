'''
Integration tests for the vision-2.0 feature.

Tests the full integration between the vision tool, slot filler, and homeowner agent,
ensuring that images can be processed and information extracted for project creation.
'''
import pytest
import os
from pathlib import Path
import base64
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio

from instabids.tools.vision_tool_plus import analyse, batch_analyse, validate_image_for_bid_card
from instabids.agents.slot_filler import process_image_for_slots, update_card_from_images
from instabids.agents.homeowner_agent import HomeownerAgent
from instabids.tools.base64_helpers import encode_image_file, save_base64_to_file

# Sample test image paths
TEST_IMAGES_DIR = Path(__file__).parent.parent / "fixtures" / "images"

# Create test images directory if it doesn't exist
TEST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Sample image data in base64 format - small placeholder image 
# (this would be replaced with actual test images in a real implementation)
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

@pytest.fixture
def sample_image_path():
    """Create a sample image file for testing."""
    img_path = TEST_IMAGES_DIR / "test_roof.jpg"
    
    # Only create the file if it doesn't exist
    if not img_path.exists():
        img_data = base64.b64decode(SAMPLE_IMAGE_BASE64)
        with open(img_path, "wb") as f:
            f.write(img_data)
            
    return str(img_path)

@pytest.fixture
def mock_vision_response():
    """Mock response from the vision API."""
    return {
        "labels": ["roof", "shingles", "damage", "repair"],
        "description": "Damaged roof shingles with visible wear and tear",
        "damage_assessment": "Moderate damage to roof shingles with potential water infiltration",
        "dimensions": (800, 600)
    }

@pytest.mark.asyncio
async def test_vision_analysis_with_mock(sample_image_path):
    """Test the vision analysis function with a mocked API response."""
    with patch('instabids.tools.vision_tool_plus.client.chat.completions.create', new_callable=AsyncMock) as mock_api:
        # Setup mock response
        mock_api.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(
                    tool_calls=[MagicMock(
                        function=MagicMock(
                            arguments='''{"labels": ["roof", "shingles", "damage"], 
                                        "description": "Damaged roof shingles", 
                                        "damage_assessment": "Moderate damage"}'''
                        )
                    )]
                )
            )],
            usage=MagicMock(image_size=(800, 600))
        )
        
        # Call the function
        result = await analyse(sample_image_path)
        
        # Verify the result
        assert "labels" in result
        assert "roof" in result["labels"]
        assert "damage" in result["labels"]
        assert "damage_assessment" in result
        assert "dimensions" in result

@pytest.mark.asyncio
async def test_slot_filler_process_image(sample_image_path, mock_vision_response):
    """Test that the slot filler can process an image and extract values."""
    with patch('instabids.agents.slot_filler.validate_image_for_bid_card', new_callable=AsyncMock) as mock_validate:
        # Setup mock response
        mock_validate.return_value = {
            "is_valid": True,
            "analysis": mock_vision_response,
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

@pytest.mark.asyncio
async def test_update_card_from_images(sample_image_path, mock_vision_response):
    """Test updating a card with information from images."""
    # Create an initial card
    card = {
        "description": "I need to fix my leaking roof",
        "user_id": "test-user"
    }
    
    with patch('instabids.agents.slot_filler.process_image_for_slots', new_callable=AsyncMock) as mock_process:
        # Setup mock response - first image provides category and job_type
        mock_process.return_value = {
            "category": "repair",
            "job_type": "roof repair",
            "damage_assessment": "Moderate damage to roof shingles",
            "project_images": [sample_image_path]
        }
        
        # Call the function
        updated_card = await update_card_from_images(card, [sample_image_path])
        
        # Verify the result
        assert updated_card["category"] == "repair"
        assert updated_card["job_type"] == "roof repair"
        assert updated_card["damage_assessment"] == "Moderate damage to roof shingles"
        assert updated_card["project_images"] == [sample_image_path]
        assert updated_card["description"] == "I need to fix my leaking roof"
        assert updated_card["user_id"] == "test-user"

@pytest.mark.asyncio
async def test_homeowner_agent_process_input_with_images(sample_image_path, mock_vision_response):
    """Test the homeowner agent can process input with images."""
    # Create a homeowner agent
    agent = HomeownerAgent()
    
    # Mock the memory
    agent.memory = MagicMock()
    agent.memory.get.return_value = {}
    
    # Mock the update_card_from_images function
    with patch('instabids.agents.homeowner_agent.update_card_from_images', new_callable=AsyncMock) as mock_update:
        # Setup mock response
        mock_update.return_value = {
            "category": "repair",
            "job_type": "roof repair",
            "damage_assessment": "Moderate damage to roof shingles",
            "project_images": [sample_image_path],
            "description": "I need roof repair",
            "user_id": "test-user"
        }
        
        # Also mock the _create_project method to avoid database operations
        with patch.object(agent, '_create_project', new_callable=AsyncMock) as mock_create_project:
            mock_create_project.return_value = "test-project-id"
            
            # Mock missing_slots to return an empty list (all slots filled)
            with patch('instabids.agents.homeowner_agent.missing_slots', return_value=[]):
                # Mock classify to return a classification
                with patch('instabids.agents.homeowner_agent.classify', return_value={"category": "repair", "confidence": 0.9}):
                    # Call the function
                    result = await agent.process_input(
                        user_id="test-user",
                        description="I need roof repair",
                        image_paths=[Path(sample_image_path)]
                    )
                    
                    # Verify the result
                    assert result["need_more"] == False
                    assert result["project_id"] == "test-project-id"
                    assert result["category"] == "repair"
                    assert result["confidence"] == 0.9
                    
                    # Verify the update_card_from_images was called
                    mock_update.assert_called_once()
                    # Verify _create_project was called
                    mock_create_project.assert_called_once()

@pytest.mark.asyncio
async def test_homeowner_agent_process_input_need_more_info(sample_image_path):
    """Test the homeowner agent requests more information when needed."""
    # Create a homeowner agent
    agent = HomeownerAgent()
    
    # Mock the memory
    agent.memory = MagicMock()
    agent.memory.get.return_value = {}
    
    # Mock the update_card_from_images function
    with patch('instabids.agents.homeowner_agent.update_card_from_images', new_callable=AsyncMock) as mock_update:
        # Setup mock response with incomplete information
        mock_update.return_value = {
            "category": "repair",
            "project_images": [sample_image_path],
            "description": "I need roof repair",
            "user_id": "test-user"
            # Missing job_type, budget, timeline, etc.
        }
        
        # Mock missing_slots to return slots that are still missing
        with patch('instabids.agents.homeowner_agent.missing_slots', return_value=["job_type", "budget_range", "timeline"]):
            # Mock get_next_question
            with patch('instabids.agents.homeowner_agent.get_next_question', return_value="Which specific job is it?"):
                # Call the function
                result = await agent.process_input(
                    user_id="test-user",
                    description="I need roof repair",
                    image_paths=[Path(sample_image_path)]
                )
                
                # Verify the result
                assert result["need_more"] == True
                assert result["follow_up"] == "Which specific job is it?"
                assert "collected" in result
                assert result["collected"]["category"] == "repair"
                
                # Verify memory was updated
                agent.memory.set.assert_called_once()

# This test would need actual API keys to run
@pytest.mark.skip(reason="Requires actual OpenAI API key")
@pytest.mark.asyncio
async def test_vision_analysis_real_api(sample_image_path):
    """Test the vision analysis function with the real API."""
    # Ensure an OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("No OpenAI API key available")
        
    # Call the function
    result = await analyse(sample_image_path)
    
    # Verify the result structure
    assert "labels" in result
    assert isinstance(result["labels"], list)
    assert "description" in result
    assert "damage_assessment" in result
    assert "dimensions" in result