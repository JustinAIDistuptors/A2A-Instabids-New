import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.memory.persistent_memory import PersistentMemory
from src.memory.conversation_state import ConversationState
from src.slot_filler.slot_filler_factory import SlotFillerFactory, SlotFiller


@pytest.fixture
def mock_memory():
    memory = MagicMock(spec=PersistentMemory)
    memory.get = MagicMock(return_value=None)
    memory.set = MagicMock()
    memory.add_interaction = AsyncMock()
    return memory


@pytest.fixture
def mock_conversation_state():
    state = MagicMock(spec=ConversationState)
    state.get_slot = MagicMock()
    state.set_slot = MagicMock()
    state.clear_slot = MagicMock()
    state.clear_all_slots = MagicMock()
    state.has_slot = MagicMock()
    state.get_missing_required_slots = MagicMock()
    state.all_required_slots_filled = MagicMock()
    state.get_all_slots = MagicMock()
    state.get_filled_required_slots = MagicMock()
    state.add_to_history = MagicMock()
    state.save = AsyncMock()
    state.get_state_summary = MagicMock()
    state.get_history = MagicMock()
    state.get_history_as_messages = MagicMock()
    state.add_multi_modal_context = MagicMock()
    state.set_required_slots = MagicMock()
    state.set_optional_slots = MagicMock()
    state.load = AsyncMock()
    return state


class TestSlotFillerFactory:
    @pytest.fixture
    async def factory(self, mock_memory):
        factory = SlotFillerFactory(mock_memory)
        return factory

    @patch('src.slot_filler.slot_filler_factory.ConversationState')
    async def test_create_slot_filler(self, mock_conversation_state_class, factory, mock_conversation_state):
        # Setup
        mock_conversation_state_class.return_value = mock_conversation_state
        required_slots = ["location", "project_type"]
        optional_slots = ["timeline"]
        
        # Execute
        slot_filler = await factory.create_slot_filler(
            "test-conversation-123", required_slots, optional_slots
        )
        
        # Verify
        mock_conversation_state_class.assert_called_once_with(factory.memory, "test-conversation-123")
        mock_conversation_state.load.assert_called_once()
        mock_conversation_state.set_required_slots.assert_called_once_with(required_slots)
        mock_conversation_state.set_optional_slots.assert_called_once_with(optional_slots)
        assert isinstance(slot_filler, SlotFiller)
        assert slot_filler.state == mock_conversation_state


class TestSlotFiller:
    @pytest.fixture
    def slot_filler(self, mock_conversation_state):
        return SlotFiller(mock_conversation_state)

    def test_initialization(self, slot_filler, mock_conversation_state):
        assert slot_filler.state == mock_conversation_state
        assert slot_filler._on_slot_filled_callbacks == {}

    def test_slot_operations(self, slot_filler, mock_conversation_state):
        # Test get_slot
        mock_conversation_state.get_slot.return_value = "New York"
        assert slot_filler.get_slot("location") == "New York"
        mock_conversation_state.get_slot.assert_called_once_with("location", None)
        
        # Test set_slot
        slot_filler.set_slot("project_type", "bathroom")
        mock_conversation_state.set_slot.assert_called_once_with("project_type", "bathroom")
        
        # Test clear_slot
        slot_filler.clear_slot("location")
        mock_conversation_state.clear_slot.assert_called_once_with("location")
        
        # Test clear_all_slots
        slot_filler.clear_all_slots()
        mock_conversation_state.clear_all_slots.assert_called_once()
        
        # Test has_slot
        mock_conversation_state.has_slot.return_value = True
        assert slot_filler.has_slot("project_type") is True
        mock_conversation_state.has_slot.assert_called_once_with("project_type")

    def test_slot_status_methods(self, slot_filler, mock_conversation_state):
        # Test get_missing_required_slots
        mock_conversation_state.get_missing_required_slots.return_value = ["timeline"]
        assert slot_filler.get_missing_required_slots() == ["timeline"]
        
        # Test all_required_slots_filled
        mock_conversation_state.all_required_slots_filled.return_value = False
        assert slot_filler.all_required_slots_filled() is False
        
        # Test get_filled_slots
        mock_conversation_state.get_all_slots.return_value = {"location": "Miami"}
        assert slot_filler.get_filled_slots() == {"location": "Miami"}
        
        # Test get_filled_required_slots
        mock_conversation_state.get_filled_required_slots.return_value = {"location": "Miami"}
        assert slot_filler.get_filled_required_slots() == {"location": "Miami"}

    def test_slot_filled_callbacks(self, slot_filler):
        # Setup a mock callback
        callback = MagicMock()
        slot_filler.register_slot_filled_callback("location", callback)
        
        # Set a slot and check the callback is triggered
        slot_filler.set_slot("location", "Seattle")
        callback.assert_called_once_with("Seattle")
        
        # Check that only the right callback is triggered
        other_callback = MagicMock()
        slot_filler.register_slot_filled_callback("project_type", other_callback)
        
        # Reset first callback's mock to check it isn't called again
        callback.reset_mock()
        
        # Set a different slot
        slot_filler.set_slot("project_type", "kitchen")
        callback.assert_not_called()
        other_callback.assert_called_once_with("kitchen")

    async def test_update_from_message(self, slot_filler, mock_conversation_state):
        await slot_filler.update_from_message("user", "Hello there", [{"type": "image"}])
        
        mock_conversation_state.add_to_history.assert_called_once_with(
            "user", "Hello there", [{"type": "image"}]
        )
        mock_conversation_state.save.assert_called_once()

    async def test_extract_slots_from_message(self, slot_filler):
        # Setup mock extractors
        location_extractor = MagicMock(return_value="Chicago")
        project_extractor = MagicMock(return_value="bathroom")
        failed_extractor = MagicMock(side_effect=Exception("Extract error"))
        
        extractors = {
            "location": location_extractor,
            "project_type": project_extractor,
            "will_fail": failed_extractor
        }
        
        # Execute
        message = "I want to renovate my bathroom in Chicago"
        result = await slot_filler.extract_slots_from_message(message, extractors)
        
        # Verify
        assert result == {"location": "Chicago", "project_type": "bathroom"}
        location_extractor.assert_called_once_with(message)
        project_extractor.assert_called_once_with(message)
        failed_extractor.assert_called_once_with(message)

    async def test_process_vision_inputs(self, slot_filler, mock_conversation_state):
        # Setup mock vision extractors
        project_type_extractor = MagicMock(return_value="kitchen")
        color_extractor = MagicMock(return_value="white")
        
        vision_extractors = {
            "project_type": project_type_extractor,
            "color": color_extractor
        }
        
        # Execute
        image_data = {
            "id": "img123",
            "url": "https://example.com/image.jpg",
            "metadata": {"width": 800, "height": 600}
        }
        
        result = await slot_filler.process_vision_inputs(image_data, vision_extractors)
        
        # Verify
        assert result == {"project_type": "kitchen", "color": "white"}
        mock_conversation_state.add_multi_modal_context.assert_called_once_with(
            "img123", "image", "https://example.com/image.jpg", {"width": 800, "height": 600}
        )
        project_type_extractor.assert_called_once_with(image_data)
        color_extractor.assert_called_once_with(image_data)
        mock_conversation_state.save.assert_called_once()

    async def test_save(self, slot_filler, mock_conversation_state):
        mock_conversation_state.save.return_value = True
        assert await slot_filler.save() is True
        mock_conversation_state.save.assert_called_once()

    def test_get_methods(self, slot_filler, mock_conversation_state):
        # Test get_state_summary
        mock_conversation_state.get_state_summary.return_value = {"filled_slots": 2}
        assert slot_filler.get_state_summary() == {"filled_slots": 2}
        
        # Test get_history
        mock_conversation_state.get_history.return_value = [{"role": "user"}]
        assert slot_filler.get_history() == [{"role": "user"}]
        mock_conversation_state.get_history.assert_called_once_with(None)
        
        # Test get_history with limit
        mock_conversation_state.get_history.reset_mock()
        mock_conversation_state.get_history.return_value = [{"role": "user"}]
        assert slot_filler.get_history(5) == [{"role": "user"}]
        mock_conversation_state.get_history.assert_called_once_with(5)
        
        # Test get_history_as_messages
        mock_conversation_state.get_history_as_messages.return_value = [{"role": "user"}]
        assert slot_filler.get_history_as_messages() == [{"role": "user"}]
        mock_conversation_state.get_history_as_messages.assert_called_once_with(None)