# tests/test_vision_boost.py
import pytest
import uuid
import os
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

# Modules to test
from instabids.tools import gemini_vision_tool
from instabids.data import photo_repo
from instabids.agents.homeowner_agent import HomeownerAgent # Added import
from instabids_google.adk.memory.conversation_state import ConversationState


# --- Fixtures ---

@pytest.fixture
def mock_gemini_model():
    """Fixture for a mocked Gemini Pro Vision model."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"labels": ["outdoor", "deck", "wood"], "confidence": 0.85}'
    mock_response.embedding = MagicMock()
    mock_response.embedding.values = [0.1, 0.2, 0.3] * 256
    mock_candidate = MagicMock()
    mock_candidate.content = MagicMock()
    mock_candidate.content.parts = [mock_response]
    mock_generate_response = MagicMock()
    mock_generate_response.candidates = [mock_candidate]
    mock_model.generate_content.return_value = mock_generate_response
    return mock_model

@pytest.fixture
def mock_google_generativeai(mock_gemini_model):
    """Fixture to patch google.generativeai."""
    with patch('instabids.tools.gemini_vision_tool.genai') as mock_genai:
        mock_genai.configure = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_gemini_model
        yield mock_genai

@pytest.fixture
def temp_image_file(tmp_path):
    """Creates a dummy image file for testing."""
    img_path = tmp_path / "test_image.jpg"
    img_path.write_text("dummy image data")
    return img_path

# --- Fixtures for photo_repo ---
@pytest.fixture
def mock_supabase_client():
    """Fixture for a mocked Supabase client."""
    mock_client = MagicMock()
    mock_from = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_execute = MagicMock()

    mock_client.table.return_value = mock_from
    mock_from.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.execute.return_value = mock_execute # Simulate success

    return mock_client

@pytest.fixture
def mock_photo_repo_deps(mock_supabase_client):
    """Fixture to patch dependencies for photo_repo."""
    with patch('instabids.data.photo_repo.get_supabase_client', return_value=mock_supabase_client) as mock_getter:
        yield {
            "get_client": mock_getter,
            "client": mock_supabase_client
        }

# --- Fixture for HomeownerAgent --- (NEW)
@pytest.fixture
def homeowner_agent_instance():
    """Fixture for a HomeownerAgent instance with mocked memory."""
    mock_memory = MagicMock()
    mock_memory.load_state = MagicMock()
    mock_memory.save_state = MagicMock()
    # Patch base class init if needed, adjust depending on LlmAgent structure
    with patch('google.adk.LlmAgent.__init__', return_value=None):
         agent = HomeownerAgent(memory=mock_memory)
    # Initialize agent state (adjust based on actual ConversationState needs)
    agent.state = ConversationState(user_id="test_user", project_id=str(uuid.uuid4()))
    return agent
# --- END HomeownerAgent Fixture ---


# --- Unit Tests: gemini_vision_tool ---

@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
def test_gemini_analyse_success(mock_google_generativeai, mock_gemini_model, temp_image_file):
    """Test successful analysis using the Gemini vision tool."""
    image_path = str(temp_image_file)
    result = gemini_vision_tool.analyse(image_path)

    assert result is not None
    assert result["labels"] == ["outdoor", "deck", "wood"]
    assert result["confidence"] == 0.85
    assert len(result["embedding"]) == 768
    assert result["embedding"][:3] == [0.1, 0.2, 0.3]
    mock_google_generativeai.configure.assert_called_once_with(api_key="test-key")
    mock_google_generativeai.GenerativeModel.assert_called_once_with('gemini-1.5-flash')
    mock_gemini_model.generate_content.assert_called_once()

def test_gemini_analyse_no_api_key(temp_image_file):
    """Test analysis failure when API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        result = gemini_vision_tool.analyse(str(temp_image_file))
        assert result is None

def test_gemini_analyse_file_not_found():
    """Test analysis failure when image file does not exist."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
      with patch('instabids.tools.gemini_vision_tool.Path.exists', return_value=False):
        result = gemini_vision_tool.analyse("non_existent_file.jpg")
        assert result is None

@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
def test_gemini_analyse_api_error(mock_google_generativeai, mock_gemini_model, temp_image_file):
    """Test analysis failure due to an API error."""
    mock_gemini_model.generate_content.side_effect = Exception("API rate limit exceeded")
    result = gemini_vision_tool.analyse(str(temp_image_file))
    assert result is None


# --- Unit Tests: photo_repo ---

def test_save_photo_meta_success(mock_photo_repo_deps):
    """Test successfully saving photo metadata."""
    project_id = str(uuid.uuid4())
    storage_path = "images/photo1.jpg"
    meta = {
        "labels": ["kitchen", "renovation", "countertop"],
        "embedding": [0.5] * 768,
        "confidence": 0.92
    }
    photo_repo.save_photo_meta(project_id, storage_path, meta)

    mock_client = mock_photo_repo_deps['client']
    mock_client.table.assert_called_once_with('project_photos')
    mock_client.table.return_value.update.assert_called_once_with({
        "vision_labels": meta["labels"],
        "embed": meta["embedding"],
        "confidence": meta["confidence"]
    })
    mock_update = mock_client.table.return_value.update.return_value
    mock_update.eq.assert_any_call('project_id', project_id)
    mock_update.eq.assert_any_call('storage_path', storage_path)
    mock_update.eq.return_value.execute.assert_called_once()

def test_save_photo_meta_no_meta(mock_photo_repo_deps):
    """Test saving when metadata is None."""
    project_id = str(uuid.uuid4())
    storage_path = "images/photo2.jpg"
    meta = None
    photo_repo.save_photo_meta(project_id, storage_path, meta)

    mock_client = mock_photo_repo_deps['client']
    mock_client.table.assert_not_called()

def test_save_photo_meta_missing_keys(mock_photo_repo_deps):
    """Test saving when metadata dict is missing expected keys."""
    project_id = str(uuid.uuid4())
    storage_path = "images/photo3.jpg"
    meta = {"labels": ["incomplete"]}
    photo_repo.save_photo_meta(project_id, storage_path, meta)

    mock_client = mock_photo_repo_deps['client']
    mock_client.table.assert_called_once_with('project_photos')
    # Check that default values (None) are used for missing keys
    mock_client.table.return_value.update.assert_called_once_with({
        "vision_labels": meta["labels"],
        "embed": None,
        "confidence": None
    })
    mock_client.table.return_value.update.return_value.eq.return_value.execute.assert_called_once()

def test_save_photo_meta_db_error(mock_photo_repo_deps):
    """Test handling of a database error during save."""
    project_id = str(uuid.uuid4())
    storage_path = "images/photo4.jpg"
    meta = { "labels": ["error"], "embedding": [0.1]*768, "confidence": 0.5 }
    mock_client = mock_photo_repo_deps['client']
    mock_execute = mock_client.table.return_value.update.return_value.eq.return_value.execute
    mock_execute.side_effect = Exception("DB connection failed")

    # Expect the exception to propagate
    with pytest.raises(Exception, match="DB connection failed"):
        photo_repo.save_photo_meta(project_id, storage_path, meta)
    mock_execute.assert_called_once()


# --- Integration Tests: HomeownerAgent Image Processing ---

@patch('instabids.agents.homeowner_agent.gemini_vision_tool.analyse')
@patch('instabids.agents.homeowner_agent.save_photo_meta')
def test_homeowner_agent_vision_to_slots(mock_save_photo_meta, mock_analyse, homeowner_agent_instance, temp_image_file):
    """Test the _vision_to_slots method of HomeownerAgent."""
    agent = homeowner_agent_instance
    project_id = agent.state.project_id
    image_path_str = str(temp_image_file)
    image_inputs = [{"path": image_path_str}]
    mock_meta = {"labels": ["int_tag"], "embedding": [0.9]*768, "confidence": 0.75}
    mock_analyse.return_value = mock_meta

    extracted_tags = agent._vision_to_slots(image_inputs, project_id)

    assert extracted_tags == ["int_tag"]
    mock_analyse.assert_called_once_with(image_path_str)
    expected_storage_path = temp_image_file.name # Assuming storage path is just the filename
    mock_save_photo_meta.assert_called_once_with(project_id, expected_storage_path, mock_meta)

@patch('instabids.agents.homeowner_agent.gemini_vision_tool.analyse')
@patch('instabids.agents.homeowner_agent.save_photo_meta')
def test_homeowner_agent_vision_to_slots_multiple_images(mock_save_photo_meta, mock_analyse, homeowner_agent_instance, tmp_path):
    """Test _vision_to_slots with multiple images."""
    agent = homeowner_agent_instance
    project_id = agent.state.project_id
    img1 = tmp_path / "img1.png"; img1.touch()
    img2 = tmp_path / "img2.jpeg"; img2.touch()
    image_inputs = [{"path": str(img1)}, {"path": str(img2)}]
    mock_meta1 = {"labels": ["tag1", "tag2"], "embedding": [0.1]*768, "confidence": 0.8}
    mock_meta2 = {"labels": ["tag3"], "embedding": [0.2]*768, "confidence": 0.9}
    mock_analyse.side_effect = [mock_meta1, mock_meta2]

    extracted_tags = agent._vision_to_slots(image_inputs, project_id)

    assert extracted_tags == ["tag1", "tag2", "tag3"] # Check combined unique tags
    assert mock_analyse.call_count == 2
    assert mock_save_photo_meta.call_count == 2
    mock_save_photo_meta.assert_any_call(project_id, img1.name, mock_meta1)
    mock_save_photo_meta.assert_any_call(project_id, img2.name, mock_meta2)

# --- Remaining HomeownerAgent tests to be added later ---
