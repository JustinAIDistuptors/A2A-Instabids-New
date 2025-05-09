"""End-to-end tests for BidCard Memory Integration"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import datetime
import json
import os

# Mock Supabase for testing
class MockSupabase:
    def __init__(self):
        self.tables = {
            "user_memories": [],
            "user_preferences": [],
            "user_memory_interactions": [],
            "bid_cards": [],
            "projects": []
        }
        self.query_results = {}
    
    def table(self, name):
        self.current_table = name
        self.query = {"select": "*", "filters": {}}
        return self
    
    def select(self, cols):
        self.query["select"] = cols
        return self
    
    def eq(self, field, value):
        if "filters" not in self.query:
            self.query["filters"] = {}
        self.query["filters"][field] = value
        return self
    
    def gte(self, field, value):
        if "filters" not in self.query:
            self.query["filters"] = {}
        self.query["filters"][f"{field}_gte"] = value
        return self
    
    def order(self, field, desc=False):
        self.query["order"] = {"field": field, "desc": desc}
        return self
    
    def limit(self, limit_val):
        self.query["limit"] = limit_val
        return self
    
    def maybe_single(self):
        return self
    
    def insert(self, data):
        if isinstance(data, list):
            self.tables[self.current_table].extend(data)
        else:
            self.tables[self.current_table].append(data)
        return self
    
    def upsert(self, data):
        # Simple upsert implementation - replace if id exists
        if isinstance(data, dict) and "id" in data:
            for i, item in enumerate(self.tables[self.current_table]):
                if item.get("id") == data["id"]:
                    self.tables[self.current_table][i] = data
                    return self
        # If not replaced, insert
        return self.insert(data)
    
    def update(self, data):
        # Assume last query was to filter to a specific item
        if "filters" in self.query and self.query["filters"]:
            # Simple update for the first matching item
            for item in self.tables[self.current_table]:
                matches = True
                for key, value in self.query["filters"].items():
                    if key.endswith("_gte"):
                        field = key[:-4]
                        if item.get(field, 0) < value:
                            matches = False
                            break
                    elif item.get(key) != value:
                        matches = False
                        break
                
                if matches:
                    item.update(data)
                    break
        return self
    
    async def execute(self):
        # Mock execution
        class MockResponse:
            def __init__(self, data=None, error=None):
                self.data = data if data is not None else []
                self.error = error
        
        # Return data based on query
        if "filters" in self.query and self.query["filters"]:
            # Filter the data
            result = []
            for item in self.tables[self.current_table]:
                matches = True
                for key, value in self.query["filters"].items():
                    if key.endswith("_gte"):
                        field = key[:-4]
                        if item.get(field, 0) < value:
                            matches = False
                            break
                    elif item.get(key) != value:
                        matches = False
                        break
                
                if matches:
                    result.append(item)
            
            # Apply order if specified
            if "order" in self.query:
                order_field = self.query["order"]["field"]
                desc = self.query["order"]["desc"]
                result.sort(key=lambda x: x.get(order_field, ""), reverse=desc)
            
            # Apply limit if specified
            if "limit" in self.query and self.query["limit"]:
                result = result[:self.query["limit"]]
            
            return MockResponse(data=result)
        
        # Return all data
        return MockResponse(data=self.tables[self.current_table])


# Import modules under test
from memory.persistent_memory import PersistentMemory
from memory.bidcard_memory_integration import create_bid_card_with_memory, get_recent_bidcards, record_bidcard_view

# Create mock data
MOCK_USER_ID = str(uuid.uuid4())
MOCK_PROJECT_ID = str(uuid.uuid4())
MOCK_PROJECT = {
    "id": MOCK_PROJECT_ID,
    "owner_id": MOCK_USER_ID,
    "title": "Kitchen Renovation",
    "description": "Need to renovate my kitchen with new cabinets and countertops",
    "vision_tags": ["kitchen", "cabinet", "countertop"],
    "created_at": datetime.datetime.utcnow().isoformat()
}


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = MockSupabase()
    
    # Add test data
    db.tables["projects"].append(MOCK_PROJECT)
    
    # Add some memory data
    db.tables["user_memories"].append({
        "user_id": MOCK_USER_ID,
        "memory_data": {
            "context": {
                "last_visit": datetime.datetime.utcnow().isoformat()
            }
        },
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat()
    })
    
    # Add some preference data
    db.tables["user_preferences"].append({
        "id": str(uuid.uuid4()),
        "user_id": MOCK_USER_ID,
        "preference_key": "preferred_project_categories",
        "preference_value": "renovation",
        "confidence": 0.8,
        "source": "previous_project",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat()
    })
    
    db.tables["user_preferences"].append({
        "id": str(uuid.uuid4()),
        "user_id": MOCK_USER_ID,
        "preference_key": "preferred_budget_range",
        "preference_value": "$5,000-$10,000",
        "confidence": 0.7,
        "source": "previous_project",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat()
    })
    
    return db


@pytest.fixture
async def memory(mock_db):
    """Create a memory instance with mock DB."""
    memory = PersistentMemory(mock_db, MOCK_USER_ID)
    await memory.load()
    return memory


@pytest.fixture
def vision_data():
    """Create mock vision data."""
    return {
        "tags": ["kitchen", "countertop", "cabinet"],
        "objects": ["cabinet", "countertop", "sink"],
        "confidence": 0.85
    }


@pytest.mark.asyncio
async def test_create_bid_card_with_memory_e2e(mock_db, memory, vision_data):
    """Test end-to-end bid card creation with memory integration."""
    # Patch the original create_bid_card function
    with patch("instabids.agents.bidcard_agent.create_bid_card") as mock_create:
        # Set up mock return value
        mock_card = {
            "id": str(uuid.uuid4()),
            "project_id": MOCK_PROJECT_ID,
            "category": "renovation",
            "job_type": "kitchen remodel",
            "budget_range": "$5,000-$10,000",
            "timeline": "1-3 months",
            "ai_confidence": 0.85,
            "status": "final",
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        mock_create.return_value = (mock_card, 0.85)
        
        # Call the integrated function
        card, confidence = await create_bid_card_with_memory(
            MOCK_PROJECT, vision_data, memory, MOCK_USER_ID
        )
        
        # Verify the card was created
        assert card["id"] is not None
        assert card["category"] == "renovation"
        assert card["budget_range"] == "$5,000-$10,000"
        assert confidence == 0.85
        
        # Verify memory was updated
        interactions = await memory.get_recent_interactions("bidcard_creation")
        assert len(interactions) == 1
        assert interactions[0]["data"]["project_id"] == MOCK_PROJECT_ID
        assert interactions[0]["data"]["category"] == "renovation"
        
        # Check that preferences were updated
        pref = memory.get_preference("preferred_project_categories")
        assert pref == "renovation"


@pytest.mark.asyncio
async def test_get_recent_bidcards_e2e(mock_db, memory):
    """Test retrieving recent bid cards from memory."""
    # Add some interactions to memory
    await memory.add_interaction("bidcard_creation", {
        "project_id": MOCK_PROJECT_ID,
        "category": "renovation",
        "job_type": "kitchen remodel",
        "budget_range": "$5,000-$10,000",
        "timeline": "1-3 months",
        "confidence": 0.85
    })
    
    # Get recent bid cards
    cards = await get_recent_bidcards(memory)
    
    # Verify the cards were retrieved
    assert len(cards) == 1
    assert cards[0]["data"]["project_id"] == MOCK_PROJECT_ID
    assert cards[0]["data"]["category"] == "renovation"


@pytest.mark.asyncio
async def test_record_bidcard_view_e2e(mock_db, memory):
    """Test recording a bid card view in memory."""
    # Record a bid card view
    card_id = str(uuid.uuid4())
    await record_bidcard_view(memory, card_id, MOCK_PROJECT_ID)
    
    # Verify the view was recorded
    interactions = await memory.get_recent_interactions("bidcard_view")
    assert len(interactions) == 1
    assert interactions[0]["data"]["card_id"] == card_id
    assert interactions[0]["data"]["project_id"] == MOCK_PROJECT_ID


@pytest.mark.asyncio
async def test_api_integration(mock_db):
    """Test API route integration with memory."""
    # Import API module
    import bidcard_api_routes as api
    
    # Patch the Supabase client
    with patch("bidcard_api_routes.supabase_client", mock_db):
        # Patch project_repo and bidcard_repo
        with patch("bidcard_api_routes.project_repo") as mock_project_repo, \
             patch("bidcard_api_routes.bidcard_repo") as mock_bidcard_repo, \
             patch("bidcard_api_routes.user_repo") as mock_user_repo:
            
            # Set up mock return values
            mock_project_repo.fetch.return_value = MOCK_PROJECT
            mock_bidcard_repo.list_for_project.return_value = [{
                "id": str(uuid.uuid4()),
                "project_id": MOCK_PROJECT_ID,
                "category": "renovation",
                "created_at": datetime.datetime.utcnow().isoformat()
            }]
            mock_user_repo.get_user.return_value = {"id": MOCK_USER_ID}
            
            # Test generate_bid_card
            with patch("bidcard_api_routes.create_bid_card") as mock_create:
                mock_card = {
                    "id": str(uuid.uuid4()),
                    "project_id": MOCK_PROJECT_ID,
                    "category": "renovation",
                    "created_at": datetime.datetime.utcnow().isoformat()
                }
                mock_create.return_value = (mock_card, 0.85)
                
                # Call API
                result = await api.generate_bid_card(MOCK_PROJECT_ID, MOCK_USER_ID)
                
                # Verify result
                assert "bid_card" in result
                assert "confidence" in result
                assert result["bid_card"]["category"] == "renovation"
            
            # Test list_bid_cards_for_project
            result = await api.list_bid_cards_for_project(MOCK_PROJECT_ID, MOCK_USER_ID)
            
            # Verify result
            assert len(result) == 1
            assert result[0]["project_id"] == MOCK_PROJECT_ID
            
            # Verify memory interaction
            memory = await api.get_memory_for_user(MOCK_USER_ID)
            interactions = await memory.get_recent_interactions("bidcard_view")
            assert len(interactions) > 0