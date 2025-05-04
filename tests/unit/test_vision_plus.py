"""
Unit tests for the enhanced vision tool.

Tests the functionality of the vision_tool_plus module, including:
- Image analysis with file path
- Label format validation
- Error handling
"""
import pytest
import os
import base64
import json
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from instabids.tools.vision_tool_plus import analyse

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
def sample_image_file(tmp_path):
    """Create a sample image file for testing."""
    test_dir = tmp_path / "test_vision"
    test_dir.mkdir(exist_ok=True)
    img_path = test_dir / "test_image.jpg"
    
    # Write base64 data to file
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(SAMPLE_IMAGE_BASE64))
    
    yield str(img_path)
    
    # Clean up
    if img_path.exists():
        img_path.unlink()
    if test_dir.exists():
        test_dir.rmdir()

@pytest.mark.asyncio
async def test_label_format(monkeypatch, tmp_path):
    """Test that the analyse function returns properly formatted labels."""
    # Create a test image file
    test_dir = tmp_path / "vision_test"
    test_dir.mkdir(exist_ok=True)
    img_path = test_dir / "test_image.jpg"
    
    # Write base64 data to file
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(SAMPLE_IMAGE_BASE64))
    
    # Set environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    # Mock the OpenAI client
    with patch("instabids.tools.vision_tool_plus.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [MagicMock()]
        mock_response.choices[0].message.tool_calls[0].function.arguments = json.dumps({
            "labels": ["roof", "damage", "shingles"]
        })
        mock_response.usage = {"image_size": (800, 600)}
        mock_create.return_value = mock_response
        
        # Call the function
        result = await analyse(str(img_path))
        
        # Verify the API was called correctly
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert kwargs["model"] == "gpt-4o-vision-preview"
        
        # Verify the result format
        assert "labels" in result
        assert "dimensions" in result
        assert isinstance(result["labels"], list)
        assert len(result["labels"]) == 3
        assert "roof" in result["labels"]
        assert "damage" in result["labels"]
        assert "shingles" in result["labels"]
        assert result["dimensions"] == (800, 600)

@pytest.mark.asyncio
async def test_file_not_found(monkeypatch):
    """Test error handling when file doesn't exist."""
    # Set environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        await analyse("/nonexistent/path/to/image.jpg")

@pytest.mark.asyncio
async def test_api_error_handling(monkeypatch, sample_image_file):
    """Test error handling when API call fails."""
    # Set environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    # Mock the OpenAI client to raise an exception
    with patch("instabids.tools.vision_tool_plus.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("API Error")
        
        # Test with valid file path
        with pytest.raises(Exception) as exc_info:
            await analyse(sample_image_file)
        
        assert "API Error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_empty_labels_handling(monkeypatch, sample_image_file):
    """Test handling of empty labels in response."""
    # Set environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    # Mock the OpenAI client
    with patch("instabids.tools.vision_tool_plus.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        # Set up the mock response with empty labels
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [MagicMock()]
        mock_response.choices[0].message.tool_calls[0].function.arguments = json.dumps({
            "labels": []
        })
        mock_response.usage = {"image_size": (800, 600)}
        mock_create.return_value = mock_response
        
        # Call the function
        result = await analyse(sample_image_file)
        
        # Verify the result has empty labels
        assert "labels" in result
        assert result["labels"] == []
        assert result["dimensions"] == (800, 600)