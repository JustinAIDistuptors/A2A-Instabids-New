# tests/test_vision_boost.py
import pytest
import uuid
import os # Added os import for environment patching
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

# Modules to test
from instabids.tools import gemini_vision_tool
# from instabids.data import photo_repo # Will add later
# from instabids.agents.homeowner_agent import HomeownerAgent # Will add later
# from instabids_google.adk.memory.conversation_state import ConversationState # Will add later


# --- Fixtures ---

@pytest.fixture
def mock_gemini_model():
    """Fixture for a mocked Gemini Pro Vision model."""
    mock_model = MagicMock()
    # Setup mock response structure based on gemini_vision_tool.analyse expectations
    mock_response = MagicMock()
    mock_response.text = '{"labels": ["outdoor", "deck", "wood"], "confidence": 0.85}'
    # Mock embedding - precise structure might depend on actual API/usage
    mock_response.embedding = MagicMock() # Ensure embedding attribute exists
    mock_response.embedding.values = [0.1, 0.2, 0.3] * 256 # Example 768-dim embedding
    # Simulate the candidates list structure correctly
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_response] # Assuming response text/embedding is in parts
    mock_generate_response = MagicMock()
    mock_generate_response.candidates = [mock_candidate]
    mock_model.generate_content.return_value = mock_generate_response
    return mock_model

@pytest.fixture
def mock_google_generativeai(mock_gemini_model):
    """Fixture to patch google.generativeai."""
    # Target the specific module where genai is used
    with patch('instabids.tools.gemini_vision_tool.genai') as mock_genai:
        # Configure the mock genai object
        mock_genai.configure = MagicMock()
        # Make GenerativeModel return our specific mocked model
        mock_genai.GenerativeModel.return_value = mock_gemini_model
        yield mock_genai

# Supabase fixtures will be added later

@pytest.fixture
def temp_image_file(tmp_path):
    """Creates a dummy image file for testing."""
    img_path = tmp_path / "test_image.jpg"
    img_path.write_text("dummy image data") # Content doesn't matter for mocked API
    return img_path

# HomeownerAgent fixture will be added later


# --- Unit Tests: gemini_vision_tool ---

@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
def test_gemini_analyse_success(mock_google_generativeai, mock_gemini_model, temp_image_file):
    """Test successful analysis using the Gemini vision tool."""
    image_path = str(temp_image_file)
    result = gemini_vision_tool.analyse(image_path)

    # Assertions
    assert result is not None
    assert "labels" in result
    assert "embedding" in result
    assert "confidence" in result
    assert result["labels"] == ["outdoor", "deck", "wood"]
    assert result["confidence"] == 0.85
    assert len(result["embedding"]) == 768 # Check embedding dimension
    assert result["embedding"][:3] == [0.1, 0.2, 0.3] # Check first few values

    # Check API call structure
    mock_google_generativeai.configure.assert_called_once_with(api_key="test-key")
    mock_google_generativeai.GenerativeModel.assert_called_once_with('gemini-1.5-flash')
    # Check that generate_content was called (exact args might be complex due to image loading)
    mock_gemini_model.generate_content.assert_called_once()


def test_gemini_analyse_no_api_key(temp_image_file):
    """Test analysis failure when API key is missing."""
    # Ensure API key is not set for this test
    with patch.dict(os.environ, {}, clear=True):
        result = gemini_vision_tool.analyse(str(temp_image_file))
        assert result is None

def test_gemini_analyse_file_not_found():
    """Test analysis failure when image file does not exist."""
    # Need to patch os.environ here too if the function checks it early
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
      # Also patch Path.exists within the scope of the tool's module
      with patch('instabids.tools.gemini_vision_tool.Path.exists', return_value=False):
        result = gemini_vision_tool.analyse("non_existent_file.jpg")
        assert result is None

@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
def test_gemini_analyse_api_error(mock_google_generativeai, mock_gemini_model, temp_image_file):
    """Test analysis failure due to an API error."""
    # Simulate an API error
    mock_gemini_model.generate_content.side_effect = Exception("API rate limit exceeded")

    result = gemini_vision_tool.analyse(str(temp_image_file))
    assert result is None

# --- Tests for photo_repo and HomeownerAgent to be added later ---
