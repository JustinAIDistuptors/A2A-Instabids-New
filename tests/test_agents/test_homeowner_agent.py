import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from google.adk.conversation import Message, ConversationHandler

from src.memory.persistent_memory import PersistentMemory
from src.slot_filler.slot_filler_factory import SlotFillerFactory, SlotFiller
from src.agents.homeowner_agent import HomeownerAgent


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
async def agent(mock_db):
    return HomeownerAgent(mock_db)


class TestHomeownerAgent:
    def test_initialization(self, agent):
        assert agent.default_required_slots == ["location", "project_type"]
        assert "timeline" in agent.default_optional_slots
        assert "budget" in agent.default_optional_slots
        
        # Verify we have project types and timeline options
        assert len(agent.project_types) > 0
        assert len(agent.timeline_options) > 0
        assert len(agent.budget_options) > 0

    def test_extract_location(self, agent):
        # Test with various location formats
        assert agent._extract_location("I'm in New York") == "New York"
        assert agent._extract_location("Looking for contractors in Denver, CO") == "Denver, CO"
        assert agent._extract_location("Near the Chicago area") == "Chicago"
        
        # Test with no location
        assert agent._extract_location("I want to renovate my bathroom") is None

    def test_extract_project_type(self, agent):
        # Test direct mentions
        assert agent._extract_project_type("I need to renovate my bathroom") == "bathroom"
        assert agent._extract_project_type("Kitchen remodel needed") == "kitchen"
        
        # Test indirect mentions
        assert agent._extract_project_type("Need new cabinets and countertops") == "kitchen"
        assert agent._extract_project_type("Looking to redo the shower and toilet") == "bathroom"
        
        # Test with no project type
        assert agent._extract_project_type("Looking for contractors") is None

    def test_extract_timeline(self, agent):
        # Test direct mentions
        assert agent._extract_timeline("I need it done immediately") == "immediately"
        assert agent._extract_timeline("Looking to start within 1 month") == "within 1 month"
        
        # Test indirect mentions
        assert agent._extract_timeline("Need it done ASAP") == "immediately"
        assert agent._extract_timeline("Planning for next year") == "6-12 months"
        
        # Test with no timeline
        assert agent._extract_timeline("I want to renovate my bathroom") is None

    def test_extract_budget(self, agent):
        # Test direct mentions
        assert agent._extract_budget("My budget is under $5,000") == "under $5,000"
        assert agent._extract_budget("I can spend $15,000-$30,000") == "$15,000-$30,000"
        
        # Test variations
        assert agent._extract_budget("Looking to spend under 5k") == "under $5,000"
        assert agent._extract_budget("Budget between $50k and $100k") == "$50,000-$100,000"
        
        # Test with no budget
        assert agent._extract_budget("I want to renovate my bathroom") is None

    def test_extract_project_type_from_image(self, agent):
        # Test with image URLs containing project hints
        assert agent._extract_project_type_from_image({"url": "https://example.com/bathroom-design.jpg"}) == "bathroom"
        assert agent._extract_project_type_from_image({"url": "https://example.com/kitchen-countertop.png"}) == "kitchen"
        
        # Test with no hints
        assert agent._extract_project_type_from_image({"url": "https://example.com/image.jpg"}) is None

    def test_extract_style_from_image(self, agent):
        # Test with image URLs containing style hints
        assert agent._extract_style_from_image({"url": "https://example.com/modern-bathroom.jpg"}) == "modern"
        assert agent._extract_style_from_image({"url": "https://example.com/rustic-kitchen.png"}) == "rustic"
        
        # Test with no hints
        assert agent._extract_style_from_image({"url": "https://example.com/image.jpg"}) is None

    @patch('src.agents.homeowner_agent.SlotFiller')
    async def test_process_message_with_memory_all_slots_filled(self, mock_slot_filler_class, agent):
        # Setup
        mock_message = MagicMock(spec=Message)
        mock_message.text = "I need a bathroom renovation in Denver"
        mock_message.sender_id = "test-user-123"
        mock_message.conversation_id = "test-conversation-123"
        mock_message.attachments = []
        
        # Mock the slot filling results
        mock_slot_result = {
            "all_required_slots_filled": True,
            "missing_slots": [],
            "filled_slots": {"location": "Denver", "project_type": "bathroom"},
            "extracted_from_text": {"location": "Denver", "project_type": "bathroom"},
            "extracted_from_vision": {},
            "slot_filler": MagicMock()
        }
        mock_slot_result["slot_filler"].get_filled_slots = MagicMock(
            return_value={"location": "Denver", "project_type": "bathroom"}
        )
        
        agent._process_with_slot_filling = AsyncMock(return_value=mock_slot_result)
        agent._generate_response_with_all_slots = AsyncMock(return_value="Great! I'll help with your bathroom project in Denver.")
        
        # Execute
        result = await agent._process_message_with_memory(mock_message, "test-user-123", "test-conversation-123")
        
        # Verify
        agent._process_with_slot_filling.assert_called_once()
        agent._generate_response_with_all_slots.assert_called_once_with(mock_slot_result)
        assert result == "Great! I'll help with your bathroom project in Denver."

    @patch('src.agents.homeowner_agent.SlotFiller')
    async def test_process_message_with_memory_missing_slots(self, mock_slot_filler_class, agent):
        # Setup
        mock_message = MagicMock(spec=Message)
        mock_message.text = "I need a bathroom renovation"
        mock_message.sender_id = "test-user-123"
        mock_message.conversation_id = "test-conversation-123"
        mock_message.attachments = []
        
        # Mock the slot filling results
        mock_slot_result = {
            "all_required_slots_filled": False,
            "missing_slots": ["location"],
            "filled_slots": {"project_type": "bathroom"},
            "extracted_from_text": {"project_type": "bathroom"},
            "extracted_from_vision": {},
            "slot_filler": MagicMock()
        }
        mock_slot_result["slot_filler"].get_filled_slots = MagicMock(
            return_value={"project_type": "bathroom"}
        )
        mock_slot_result["slot_filler"].state = MagicMock()
        mock_slot_result["slot_filler"].state._multi_modal_context = {}
        
        agent._process_with_slot_filling = AsyncMock(return_value=mock_slot_result)
        agent._generate_response_for_missing_slots = AsyncMock(
            return_value="Thanks! Where are you located?"
        )
        
        # Execute
        result = await agent._process_message_with_memory(mock_message, "test-user-123", "test-conversation-123")
        
        # Verify
        agent._process_with_slot_filling.assert_called_once()
        agent._generate_response_for_missing_slots.assert_called_once_with(mock_slot_result)
        assert result == "Thanks! Where are you located?"

    async def test_generate_response_with_all_slots(self, agent):
        # Setup
        mock_slot_filler = MagicMock(spec=SlotFiller)
        mock_slot_filler.get_filled_slots = MagicMock(
            return_value={
                "location": "Denver",
                "project_type": "bathroom",
                "budget": "$15,000-$30,000"
            }
        )
        
        slot_result = {
            "slot_filler": mock_slot_filler,
            "extracted_from_text": {"location": "Denver", "project_type": "bathroom"},
            "extracted_from_vision": {}
        }
        
        # Execute
        response = await agent._generate_response_with_all_slots(slot_result)
        
        # Verify
        assert "I see you're in Denver" in response
        assert "You're looking to renovate your bathroom" in response
        assert "Location: Denver" in response
        assert "Project: bathroom" in response
        assert "Budget: $15,000-$30,000" in response
        assert "When are you looking to start this project?" in response  # Asking for missing timeline

    async def test_generate_response_for_missing_slots(self, agent):
        # Setup
        mock_slot_filler = MagicMock(spec=SlotFiller)
        mock_slot_filler.get_filled_slots = MagicMock(
            return_value={"project_type": "bathroom"}
        )
        mock_slot_filler.state = MagicMock()
        mock_slot_filler.state._multi_modal_context = {}
        
        slot_result = {
            "slot_filler": mock_slot_filler,
            "missing_slots": ["location"],
            "extracted_from_text": {"project_type": "bathroom"},
            "extracted_from_vision": {}
        }
        
        # Execute
        response = await agent._generate_response_for_missing_slots(slot_result)
        
        # Verify
        assert "Thanks for sharing that information" in response
        assert "You're looking to renovate your bathroom" in response
        assert "Where are you located?" in response

    @patch('src.agents.homeowner_agent.SlotFiller')
    async def test_process_message_with_vision(self, mock_slot_filler_class, agent):
        # Setup
        mock_message = MagicMock(spec=Message)
        mock_message.text = "What do you think of this design?"
        mock_message.sender_id = "test-user-123"
        mock_message.conversation_id = "test-conversation-123"
        mock_message.attachments = [{
            "type": "image",
            "url": "https://example.com/modern-bathroom.jpg"
        }]
        
        # Mock the slot filling results
        mock_slot_result = {
            "all_required_slots_filled": True,
            "missing_slots": [],
            "filled_slots": {"location": "Denver", "project_type": "bathroom", "style_preference": "modern"},
            "extracted_from_text": {},
            "extracted_from_vision": {"project_type": "bathroom", "style_preference": "modern"},
            "slot_filler": MagicMock()
        }
        mock_slot_result["slot_filler"].get_filled_slots = MagicMock(
            return_value={"location": "Denver", "project_type": "bathroom", "style_preference": "modern"}
        )
        
        agent._process_with_slot_filling = AsyncMock(return_value=mock_slot_result)
        agent._generate_response_with_all_slots = AsyncMock(
            return_value="I see you're interested in a modern bathroom design!"
        )
        
        # Execute
        result = await agent._process_message_with_memory(mock_message, "test-user-123", "test-conversation-123")
        
        # Verify
        agent._process_with_slot_filling.assert_called_once()
        # Verify vision extractors were passed
        args, kwargs = agent._process_with_slot_filling.call_args
        assert "_extract_project_type_from_image" in str(kwargs["vision_extractors"])
        assert "_extract_style_from_image" in str(kwargs["vision_extractors"])
        
        agent._generate_response_with_all_slots.assert_called_once_with(mock_slot_result)
        assert result == "I see you're interested in a modern bathroom design!"