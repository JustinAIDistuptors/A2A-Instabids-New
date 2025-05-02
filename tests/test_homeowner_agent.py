"""Tests for HomeownerAgent functionality."""
import pytest
from pathlib import Path
from instabids.agents import HomeownerAgent
from instabids.data_access import get_project

@pytest.mark.asyncio
async def test_process_input():
    """Test basic project creation workflow."""
    agent = HomeownerAgent()
    
    # Test text-only input
    result = await agent.process_input(
        user_id="test_user_123",
        description="Need bathroom renovation"
    )
    
    assert "project_id" in result
    assert result["category"] == "bathroom"
    assert result["urgency"] == "medium"
    
    # Verify data was persisted
    project = await get_project(result["project_id"])
    assert project["description"] == "Need bathroom renovation"
    assert project["user_id"] == "test_user_123"

@pytest.mark.asyncio
async def test_image_processing():
    """Test image analysis workflow."""
    agent = HomeownerAgent()
    
    # Create test image (mock)
    test_image = Path("test_images/bathroom_before.jpg")
    test_image.touch()
    
    result = await agent.process_input(
        user_id="test_user_123",
        image_paths=[test_image]
    )
    
    assert "project_id" in result
    assert "vision_context" in result
    assert result["category"] == "bathroom"
    
    # Clean up test image
    test_image.unlink()
