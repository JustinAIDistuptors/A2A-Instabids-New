"""
Unit tests for the enhanced vision tool.

Tests the functionality of the vision_tool_plus module, including:
- Image analysis with file path
- Image analysis with base64 data
- Error handling
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
import base64

from instabids.tools.vision_tool_plus import analyse, analyze_base64

# Sample test image data
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

# Sample response data
SAMPLE_RESPONSE = {
    "choices": [
        {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "arguments": '{"labels": ["roof", "damage", "shingles"]}'
                        }
                    }
                ]
            }
        }
    ],
    "usage": {
        "image_size": (800, 600)
    }
}

@pytest.fixture
def sample_image_file():
    """Create a sample image file for testing."""
    temp_dir = Path("/tmp/instabids_test")
    temp_dir.mkdir(exist_ok=True)
    img_path = temp_dir / "test_image.jpg"
    
    # Write base64 data to file
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(SAMPLE_IMAGE_BASE64))
    
    yield str(img_path)
    
    # Clean up
    if img_path.exists():
        img_path.unlink()
    if temp_dir.exists():
        temp_dir.rmdir()

@pytest.mark.asyncio
async def test_analyse_with_file(sample_image_file):
    """Test analyzing an image from a file path."""
    with patch('instabids.tools.vision_tool_plus.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
        # Set up the mock response
        mock_create.return_value = MagicMock(**SAMPLE_RESPONSE)
        
        # Call the function
        result = await analyse(sample_image_file)
        
        # Verify the result
        assert "labels" in result
        assert "dimensions" in result
        assert result["labels"] == ["roof", "damage", "shingles"]
        assert result["dimensions"] == (800, 600)
        
        # Verify the API was called correctly
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert kwargs["model"] == "gpt-4o-vision-preview"
        assert len(kwargs["messages"]) == 1
        assert kwargs["messages"][0]["role"] == "user"

@pytest.mark.asyncio
async def test_analyse_file_not_found():
    """Test error handling when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        await analyse("/nonexistent/path/to/image.jpg")

@pytest.mark.asyncio
async def test_analyze_base64():
    """Test analyzing an image from base64 data."""
    with patch('instabids.tools.vision_tool_plus.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
        # Set up the mock response
        mock_create.return_value = MagicMock(**SAMPLE_RESPONSE)
        
        # Call the function
        result = await analyze_base64(SAMPLE_IMAGE_BASE64)
        
        # Verify the result
        assert "labels" in result
        assert "dimensions" in result
        assert result["labels"] == ["roof", "damage", "shingles"]
        assert result["dimensions"] == (800, 600)
        
        # Verify the API was called correctly
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert kwargs["model"] == "gpt-4o-vision-preview"
        assert len(kwargs["messages"]) == 1
        assert "data:image/jpeg;base64" in kwargs["messages"][0]["content"][1]["image_url"]["url"]

@pytest.mark.asyncio
async def test_api_error_handling():
    """Test error handling when API call fails."""
    with patch('instabids.tools.vision_tool_plus.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
        # Set up the mock to raise an exception
        mock_create.side_effect = Exception("API Error")
        
        # Test with file path
        with pytest.raises(Exception) as exc_info:
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', MagicMock()):
                    await analyse("/fake/path/to/image.jpg")
        assert "API Error" in str(exc_info.value)
        
        # Test with base64
        with pytest.raises(Exception) as exc_info:
            await analyze_base64(SAMPLE_IMAGE_BASE64)
        assert "API Error" in str(exc_info.value)