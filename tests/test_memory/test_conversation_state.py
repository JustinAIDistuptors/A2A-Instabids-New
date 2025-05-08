import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.memory.conversation_state import ConversationState
from src.memory.persistent_memory import PersistentMemory


@pytest.fixture
def mock_memory():
    memory = MagicMock(spec=PersistentMemory)
    memory.get = MagicMock(return_value=None)
    memory.set = MagicMock()
    memory.add_interaction = AsyncMock()
    return memory


@pytest.fixture
async def conversation_state(mock_memory):
    state = ConversationState(mock_memory, "test-conversation-123")
    await state.load()
    return state


class TestConversationState:
    async def test_initialization(self, mock_memory):
        state = ConversationState(mock_memory, "test-conversation-123")
        assert state.conversation_id == "test-conversation-123"
        assert state.memory == mock_memory
        assert state._slots == {}
        assert state._history == []

    async def test_load_new_state(self, mock_memory):
        mock_memory.get.return_value = None
        
        state = ConversationState(mock_memory, "test-conversation-123")
        result = await state.load()
        
        assert result is True
        assert state._is_loaded is True
        assert state._is_dirty is True
        mock_memory.get.assert_called_once_with("conversation_state_test-conversation-123")

    async def test_load_existing_state(self, mock_memory):
        existing_state = {
            "slots": {"location": "New York", "project_type": "bathroom"},
            "history": [{"role": "user", "content": "Hello", "timestamp": "2025-05-08T12:00:00"}],
            "required_slots": ["location", "project_type"],
            "optional_slots": ["timeline"],
            "multi_modal_context": {}
        }
        mock_memory.get.return_value = existing_state
        
        state = ConversationState(mock_memory, "test-conversation-123")
        result = await state.load()
        
        assert result is True
        assert state._is_loaded is True
        assert state._slots == {"location": "New York", "project_type": "bathroom"}
        assert len(state._history) == 1
        assert state._required_slots == {"location", "project_type"}

    async def test_save(self, conversation_state, mock_memory):
        conversation_state._is_dirty = True
        conversation_state._slots = {"location": "Miami"}
        
        result = await conversation_state.save()
        
        assert result is True
        assert conversation_state._is_dirty is False
        mock_memory.set.assert_called_once()
        mock_memory.add_interaction.assert_called_once()

    async def test_slot_operations(self, conversation_state):
        # Test setting a slot
        conversation_state.set_slot("location", "Boston")
        assert conversation_state._slots["location"] == "Boston"
        assert conversation_state._is_dirty is True
        
        # Test getting a slot
        assert conversation_state.get_slot("location") == "Boston"
        
        # Test has_slot
        assert conversation_state.has_slot("location") is True
        assert conversation_state.has_slot("non_existent") is False
        
        # Test clearing a slot
        conversation_state._is_dirty = False
        conversation_state.clear_slot("location")
        assert "location" not in conversation_state._slots
        assert conversation_state._is_dirty is True

    async def test_required_slots(self, conversation_state):
        conversation_state.set_required_slots(["location", "project_type"])
        conversation_state.set_slot("location", "Chicago")
        
        assert conversation_state.get_missing_required_slots() == ["project_type"]
        assert conversation_state.all_required_slots_filled() is False
        
        conversation_state.set_slot("project_type", "kitchen")
        assert conversation_state.all_required_slots_filled() is True
        assert conversation_state.get_filled_required_slots() == {
            "location": "Chicago", 
            "project_type": "kitchen"
        }

    async def test_history_operations(self, conversation_state):
        # Test adding to history
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.datetime(2025, 5, 8, 14, 30, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
            
            conversation_state.add_to_history("user", "Hello")
            conversation_state.add_to_history("assistant", "Hi there")
        
        assert len(conversation_state._history) == 2
        assert conversation_state._history[0]["role"] == "user"
        assert conversation_state._history[1]["role"] == "assistant"
        
        # Test getting history
        history = conversation_state.get_history(limit=1)
        assert len(history) == 1
        assert history[0]["content"] == "Hi there"
        
        # Test getting history as messages
        messages = conversation_state.get_history_as_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["content"] == "Hi there"
        
        # Test clearing history
        conversation_state.clear_history()
        assert conversation_state._history == []

    async def test_multi_modal_support(self, conversation_state):
        # Test adding multi-modal context
        conversation_state.add_multi_modal_context(
            "img1", "image", "https://example.com/image.jpg", {"width": 800, "height": 600}
        )
        
        assert "img1" in conversation_state._multi_modal_context
        assert conversation_state._multi_modal_context["img1"]["type"] == "image"
        
        # Test adding image attachment to history
        attachments = [{
            "id": "img2",
            "type": "image",
            "url": "https://example.com/another.jpg"
        }]
        conversation_state.add_to_history("user", "Check this image", attachments)
        
        assert "img2" in conversation_state._multi_modal_context
        assert conversation_state._history[-1]["attachments"] == attachments

    async def test_state_summary(self, conversation_state):
        conversation_state.set_required_slots(["location", "project_type"])
        conversation_state.set_optional_slots(["timeline"])
        conversation_state.set_slot("location", "Austin")
        conversation_state.add_to_history("user", "Hello")
        
        summary = conversation_state.get_state_summary()
        
        assert summary["conversation_id"] == "test-conversation-123"
        assert set(summary["required_slots"]) == {"location", "project_type"}
        assert summary["filled_slots"] == 1
        assert summary["missing_required"] == ["project_type"]
        assert summary["history_length"] == 1
        assert summary["all_required_filled"] is False