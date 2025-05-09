import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from google.adk.conversation import Message, ConversationHandler

from src.memory.persistent_memory import PersistentMemory
from src.slot_filler.slot_filler_factory import SlotFillerFactory, SlotFiller
from src.agents.memory_enabled_agent import MemoryEnabledAgent


class ConcreteMemoryEnabledAgent(MemoryEnabledAgent):
    """Concrete implementation of MemoryEnabledAgent for testing."""
    
    async def _process_message_with_memory(self, message, user_id, conversation_id):
        """Test implementation that just returns a fixed response."""
        return f"Response to: {message.text}"


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.maybe_single = MagicMock(return_value=db)
    db.execute = AsyncMock()
    db.upsert = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    return db


@pytest.fixture
def mock_handler():
    handler = MagicMock(spec=ConversationHandler)
    return handler


@pytest.fixture
def mock_message():
    message = MagicMock(spec=Message)
    message.text = "Hello agent"
    message.sender_id = "test-user-123"
    message.conversation_id = "test-conversation-123"
    message.attachments = []
    return message


@pytest.fixture
async def agent(mock_db):
    return ConcreteMemoryEnabledAgent(mock_db)


class TestMemoryEnabledAgent:
    @patch('src.agents.memory_enabled_agent.PersistentMemory')
    async def test_ensure_memory(self, mock_memory_class, agent, mock_db):
        # Setup
        mock_memory = MagicMock(spec=PersistentMemory)
        mock_memory.load = AsyncMock()
        mock_memory_class.return_value = mock_memory
        
        # Execute
        memory = await agent._ensure_memory("test-user-123")
        
        # Verify
        assert memory == mock_memory
        mock_memory_class.assert_called_once_with(mock_db, "test-user-123")
        mock_memory.load.assert_called_once()
        
        # Second call should use cached instance
        mock_memory_class.reset_mock()
        memory2 = await agent._ensure_memory("test-user-123")
        assert memory2 == mock_memory
        mock_memory_class.assert_not_called()

    @patch('src.agents.memory_enabled_agent.SlotFillerFactory')
    @patch('src.agents.memory_enabled_agent.PersistentMemory')
    async def test_ensure_slot_filler_factory(self, mock_memory_class, mock_factory_class, agent):
        # Setup
        mock_memory = MagicMock(spec=PersistentMemory)
        mock_memory.load = AsyncMock()
        mock_memory_class.return_value = mock_memory
        
        mock_factory = MagicMock(spec=SlotFillerFactory)
        mock_factory_class.return_value = mock_factory
        
        # Execute
        factory = await agent._ensure_slot_filler_factory("test-user-123")
        
        # Verify
        assert factory == mock_factory
        mock_factory_class.assert_called_once_with(mock_memory)
        
        # Second call should use cached factory
        mock_factory_class.reset_mock()
        factory2 = await agent._ensure_slot_filler_factory("test-user-123")
        assert factory2 == mock_factory
        mock_factory_class.assert_not_called()

    @patch('src.agents.memory_enabled_agent.SlotFiller')
    async def test_get_or_create_slot_filler(self, mock_slot_filler_class, agent):
        # Setup
        mock_slot_filler = MagicMock(spec=SlotFiller)
        
        # Mock the factory method
        mock_factory = MagicMock(spec=SlotFillerFactory)
        mock_factory.create_slot_filler = AsyncMock(return_value=mock_slot_filler)
        agent._ensure_slot_filler_factory = AsyncMock(return_value=mock_factory)
        
        # Execute
        slot_filler = await agent._get_or_create_slot_filler(
            "test-user-123", "test-conversation-123", ["location"], ["timeline"]
        )
        
        # Verify
        assert slot_filler == mock_slot_filler
        agent._ensure_slot_filler_factory.assert_called_once_with("test-user-123")
        mock_factory.create_slot_filler.assert_called_once_with(
            "test-conversation-123", ["location"], ["timeline"]
        )
        
        # Second call should use cached instance
        mock_factory.create_slot_filler.reset_mock()
        slot_filler2 = await agent._get_or_create_slot_filler(
            "test-user-123", "test-conversation-123", ["location"], ["timeline"]
        )
        assert slot_filler2 == mock_slot_filler
        mock_factory.create_slot_filler.assert_not_called()

    async def test_handle(self, agent, mock_message, mock_handler):
        # Setup
        memory_mock = MagicMock(spec=PersistentMemory)
        memory_mock.add_interaction = AsyncMock()
        agent._ensure_memory = AsyncMock(return_value=memory_mock)
        agent._process_message_with_memory = AsyncMock(return_value="Response to: Hello agent")
        
        # Execute
        response = await agent.handle(mock_message, mock_handler)
        
        # Verify
        agent._ensure_memory.assert_called_once_with("test-user-123")
        agent._process_message_with_memory.assert_called_once_with(
            mock_message, "test-user-123", "test-conversation-123"
        )
        memory_mock.add_interaction.assert_called_once_with(
            "conversation",
            {
                "user_message": "Hello agent",
                "agent_response": "Response to: Hello agent",
                "conversation_id": "test-conversation-123",
                "has_attachments": False
            }
        )
        assert response.text == "Response to: Hello agent"

    async def test_handle_with_error(self, agent, mock_message, mock_handler):
        # Setup
        memory_mock = MagicMock(spec=PersistentMemory)
        memory_mock.add_interaction = AsyncMock()
        agent._ensure_memory = AsyncMock(return_value=memory_mock)
        agent._process_message_with_memory = AsyncMock(side_effect=Exception("Test error"))
        
        # Execute
        response = await agent.handle(mock_message, mock_handler)
        
        # Verify
        memory_mock.add_interaction.assert_called_once_with(
            "error",
            {
                "error_type": "<class 'Exception'>",
                "error_message": "Test error",
                "user_message": "Hello agent",
                "conversation_id": "test-conversation-123"
            }
        )
        assert response.text == "I'm sorry, I encountered an error processing your message. Please try again."

    async def test_process_with_slot_filling_text_only(self, agent, mock_message):
        # Setup
        mock_slot_filler = MagicMock(spec=SlotFiller)
        mock_slot_filler.extract_slots_from_message = AsyncMock(return_value={"location": "Denver"})
        mock_slot_filler.update_from_message = AsyncMock()
        mock_slot_filler.all_required_slots_filled = MagicMock(return_value=True)
        mock_slot_filler.get_missing_required_slots = MagicMock(return_value=[])
        mock_slot_filler.get_filled_slots = MagicMock(return_value={"location": "Denver"})
        
        agent._get_or_create_slot_filler = AsyncMock(return_value=mock_slot_filler)
        
        # Mock extractors
        text_extractor = MagicMock(return_value="Denver")
        text_extractors = {"location": text_extractor}
        
        # Execute
        result = await agent._process_with_slot_filling(
            mock_message,
            "test-user-123",
            "test-conversation-123",
            ["location"],
            None,
            text_extractors
        )
        
        # Verify
        agent._get_or_create_slot_filler.assert_called_once_with(
            "test-user-123", "test-conversation-123", ["location"], None
        )
        mock_slot_filler.update_from_message.assert_called_once_with(
            "user", "Hello agent", []
        )
        mock_slot_filler.extract_slots_from_message.assert_called_once_with(
            "Hello agent", text_extractors
        )
        
        assert result["all_required_slots_filled"] is True
        assert result["missing_slots"] == []
        assert result["filled_slots"] == {"location": "Denver"}
        assert result["extracted_from_text"] == {"location": "Denver"}
        assert result["extracted_from_vision"] == {}
        assert result["slot_filler"] == mock_slot_filler

    async def test_process_with_slot_filling_with_vision(self, agent):
        # Setup
        # Create message with attachment
        mock_message = MagicMock(spec=Message)
        mock_message.text = "Check this image"
        mock_message.sender_id = "test-user-123"
        mock_message.conversation_id = "test-conversation-123"
        mock_message.attachments = [{
            "type": "image",
            "url": "https://example.com/kitchen.jpg",
            "id": "img123"
        }]
        
        # Mock slot filler
        mock_slot_filler = MagicMock(spec=SlotFiller)
        mock_slot_filler.extract_slots_from_message = AsyncMock(return_value={})
        mock_slot_filler.process_vision_inputs = AsyncMock(return_value={"project_type": "kitchen"})
        mock_slot_filler.update_from_message = AsyncMock()
        mock_slot_filler.all_required_slots_filled = MagicMock(return_value=True)
        mock_slot_filler.get_missing_required_slots = MagicMock(return_value=[])
        mock_slot_filler.get_filled_slots = MagicMock(return_value={"project_type": "kitchen"})
        
        agent._get_or_create_slot_filler = AsyncMock(return_value=mock_slot_filler)
        
        # Mock extractors
        vision_extractor = MagicMock(return_value="kitchen")
        vision_extractors = {"project_type": vision_extractor}
        
        # Execute
        result = await agent._process_with_slot_filling(
            mock_message,
            "test-user-123",
            "test-conversation-123",
            ["project_type"],
            None,
            None,
            vision_extractors
        )
        
        # Verify
        mock_slot_filler.process_vision_inputs.assert_called_once_with(
            mock_message.attachments[0], vision_extractors
        )
        
        assert result["all_required_slots_filled"] is True
        assert result["extracted_from_text"] == {}
        assert result["extracted_from_vision"] == {"project_type": "kitchen"}

    async def test_process_with_slot_filling_callback(self, agent, mock_message):
        # Setup
        mock_slot_filler = MagicMock(spec=SlotFiller)
        mock_slot_filler.extract_slots_from_message = AsyncMock(return_value={"location": "Denver"})
        mock_slot_filler.update_from_message = AsyncMock()
        mock_slot_filler.all_required_slots_filled = MagicMock(return_value=True)
        mock_slot_filler.get_missing_required_slots = MagicMock(return_value=[])
        mock_slot_filler.get_filled_slots = MagicMock(return_value={"location": "Denver"})
        
        agent._get_or_create_slot_filler = AsyncMock(return_value=mock_slot_filler)
        
        # Mock callback
        slot_filled_handler = AsyncMock()
        
        # Execute
        result = await agent._process_with_slot_filling(
            mock_message,
            "test-user-123",
            "test-conversation-123",
            ["location"],
            None,
            {"location": MagicMock(return_value="Denver")},
            None,
            slot_filled_handler
        )
        
        # Verify callback was called
        slot_filled_handler.assert_called_once_with(mock_slot_filler)