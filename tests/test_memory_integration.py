'''Unit tests for the memory and vision integration'''
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from instabids.memory.persistent_memory import PersistentMemory
from instabids.memory.conversation_state import ConversationState
from instabids.agents.homeowner_agent import HomeownerAgent
from instabids.tools.gemini_vision_tool import analyse

@pytest.fixture
def mock_supabase():
    '''Create a mock Supabase client'''
    mock_client = MagicMock()
    # Mock table method and its chained methods
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    
    # Mock execute response
    mock_response = MagicMock()
    mock_response.data = [{'memory_data': {}}]
    mock_table.execute.return_value = mock_response
    
    return mock_client

@pytest.fixture
def sample_image_path(tmp_path):
    '''Create a sample image file for testing'''
    img_path = tmp_path / "test_image.jpg"
    img_path.write_bytes(b"dummy image data")
    return str(img_path)

@pytest.mark.asyncio
async def test_persistent_memory(mock_supabase):
    '''Test the PersistentMemory class'''
    # Setup
    user_id = "test-user-123"
    memory = PersistentMemory(mock_supabase, user_id)
    
    # Initial state
    assert memory._is_loaded is False
    assert memory._is_dirty is False
    
    # Test load
    await memory.load()
    mock_supabase.table.assert_called_with("user_memories")
    assert memory._is_loaded is True
    
    # Test set and save
    memory.set("test_key", "test_value")
    assert memory._is_dirty is True
    await memory.save()
    mock_supabase.table().upsert.assert_called_once()
    assert memory._is_dirty is False

@pytest.mark.asyncio
async def test_conversation_state():
    '''Test the ConversationState class'''
    # Setup
    state = ConversationState(user_id="test-user")
    
    # Test message handling
    state.add_user_message("Hello")
    state.add_assistant_message("Hi there!")
    assert len(state.history) == 2
    assert state.history[0]["role"] == "user"
    assert state.history[1]["role"] == "assistant"
    
    # Test slot handling
    state.set_slot("category", "PLUMBING")
    assert state.get_slot("category") == "PLUMBING"
    assert state.get_slot("nonexistent", "default") == "default"
    
    # Test vision data handling
    vision_data = {
        "labels": ["sink", "faucet", "water"],
        "embedding": [0.1, 0.2, 0.3],
        "confidence": 0.95
    }
    state.set_vision_data("image1.jpg", vision_data)
    labels = state.get_vision_labels()
    assert set(labels) == {"sink", "faucet", "water"}

@pytest.mark.asyncio
async def test_homeowner_agent_memory_integration(mock_supabase):
    '''Test that HomeownerAgent integrates correctly with memory'''
    # Patch necessary dependencies
    with patch("instabids.agents.homeowner_agent.gemini_analyse") as mock_analyse:
        with patch("instabids.agents.homeowner_agent.send_envelope") as mock_send_envelope:
            with patch("instabids.agents.homeowner_agent.repo") as mock_repo:
                # Configure mocks
                mock_analyse.return_value = {
                    "labels": ["sink", "faucet", "leak"],
                    "embedding": [0.1, 0.2, 0.3],
                    "confidence": 0.95
                }
                mock_repo._Tx.return_value.__enter__ = MagicMock()
                mock_repo._Tx.return_value.__exit__ = MagicMock()
                mock_repo.save_project.return_value = "test-project-id"
                
                # Create agent
                agent = HomeownerAgent("test-user", supabase_client=mock_supabase)
                
                # Process input with description
                response = await agent.process_input(description="I need to fix a leaky faucet")
                
                # Verify agent saved to memory
                assert mock_supabase.table.call_count > 0
                
                # Check that user message was added to conversation state
                assert "user" in [msg["role"] for msg in agent.conversation_state.history]

@patch("builtins.open")
@patch("instabids.tools.gemini_vision_tool._model")
def test_gemini_vision_tool(mock_model, mock_open, sample_image_path):
    '''Test the Gemini Vision Tool'''
    # Setup mocks
    mock_model_instance = MagicMock()
    mock_model.return_value = mock_model_instance
    
    # Mock response from Gemini model
    mock_response = MagicMock()
    mock_candidates = MagicMock()
    mock_content = MagicMock()
    mock_part = MagicMock()
    mock_function_call = MagicMock()
    
    # Configure the nested mock structure
    mock_function_call.args = {
        "labels": ["sink", "faucet", "water"],
        "embedding": [0.1, 0.2, 0.3],
        "confidence": 0.95
    }
    mock_part.function_call = mock_function_call
    mock_content.parts = [mock_part]
    mock_candidates.content = mock_content
    mock_response.candidates = [mock_candidates]
    
    mock_model_instance.generate_content.return_value = mock_response
    
    # Mock file read
    mock_file = MagicMock()
    mock_file.read.return_value = b"test image data"
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Test the function
    result = analyse(sample_image_path)
    
    # Verify results
    assert result is not None
    assert "labels" in result
    assert "embedding" in result
    assert "confidence" in result
    assert result["labels"] == ["sink", "faucet", "water"]
    assert result["embedding"] == [0.1, 0.2, 0.3]
    assert result["confidence"] == 0.95
