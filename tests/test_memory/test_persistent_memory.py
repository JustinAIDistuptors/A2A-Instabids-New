import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.memory.persistent_memory import PersistentMemory


class TestPersistentMemory:
    @pytest.fixture
    def mock_db(self):
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
    async def memory(self, mock_db):
        memory = PersistentMemory(mock_db, "test-user-123")
        return memory

    async def test_initialization(self, mock_db):
        memory = PersistentMemory(mock_db, "test-user-123")
        assert memory.db == mock_db
        assert memory.user_id == "test-user-123"
        assert memory._memory_cache == {}
        assert memory._is_loaded is False
        assert memory._is_dirty is False

    async def test_load_new_memory(self, mock_db):
        # Mock no existing memory
        mock_db.execute.return_value.data = None
        
        memory = PersistentMemory(mock_db, "test-user-123")
        result = await memory.load()
        
        assert result is True
        assert memory._is_loaded is True
        assert memory._is_dirty is True
        assert "interactions" in memory._memory_cache
        assert "context" in memory._memory_cache
        assert "learned_preferences" in memory._memory_cache
        
        # Verify the database calls
        mock_db.table.assert_called_with("user_memories")
        mock_db.select.assert_called_with("memory_data")
        mock_db.eq.assert_called_with("user_id", "test-user-123")

    async def test_load_existing_memory(self, mock_db):
        # Mock existing memory
        existing_data = {
            "memory_data": {
                "interactions": [{"type": "login", "timestamp": "2025-05-01T12:00:00"}],
                "context": {"last_project": "bathroom"},
                "learned_preferences": {"color": {"value": "blue", "count": 2}}
            }
        }
        mock_db.execute.return_value.data = existing_data
        
        memory = PersistentMemory(mock_db, "test-user-123")
        result = await memory.load()
        
        assert result is True
        assert memory._is_loaded is True
        assert memory._is_dirty is False
        assert memory._memory_cache == existing_data["memory_data"]

    async def test_save(self, memory, mock_db):
        memory._memory_cache = {"context": {"project": "kitchen"}}  
        memory._is_loaded = True
        memory._is_dirty = True
        
        # Mock successful save
        mock_db.execute.return_value.data = [{}]  # Some data indicating success
        
        result = await memory.save()
        
        assert result is True
        assert memory._is_dirty is False
        
        # Verify the database calls
        mock_db.table.assert_called_with("user_memories")
        mock_db.upsert.assert_called_once()

    async def test_add_interaction(self, memory, mock_db):
        memory._memory_cache = {"interactions": []}
        memory._is_loaded = True
        interaction_data = {"project_type": "bathroom", "budget": "$5000-$10000"}
        
        result = await memory.add_interaction("project_creation", interaction_data)
        
        assert result is True
        assert len(memory._memory_cache["interactions"]) == 1
        assert memory._memory_cache["interactions"][0]["type"] == "project_creation"
        assert memory._memory_cache["interactions"][0]["data"] == interaction_data
        assert memory._is_dirty is True
        
        # Verify database calls
        mock_db.table.assert_called_with("user_memory_interactions")
        mock_db.insert.assert_called_once()

    async def test_memory_interface_methods(self, memory):
        # Test get/set methods
        memory._is_loaded = True
        memory._memory_cache = {"context": {}}
        
        memory.set("user_name", "John")
        assert memory._memory_cache["context"]["user_name"] == "John"
        assert memory._is_dirty is True
        
        assert memory.get("user_name") == "John"
        assert memory.get("non_existent") is None
        
        # Test not loaded case
        memory._is_loaded = False
        assert memory.get("user_name") is None

    async def test_get_recent_interactions(self, memory):
        memory._is_loaded = True
        memory._memory_cache = {
            "interactions": [
                {"type": "login", "timestamp": "2025-05-01T10:00:00", "data": {}},
                {"type": "project_creation", "timestamp": "2025-05-01T11:00:00", "data": {}},
                {"type": "login", "timestamp": "2025-05-01T12:00:00", "data": {}}
            ]
        }
        
        # Test getting all interactions
        interactions = memory.get_recent_interactions()
        assert len(interactions) == 3
        assert interactions[0]["timestamp"] == "2025-05-01T12:00:00"  # Most recent first
        
        # Test filtering by type
        login_interactions = memory.get_recent_interactions(interaction_type="login")
        assert len(login_interactions) == 2
        
        # Test limiting
        limited = memory.get_recent_interactions(limit=1)
        assert len(limited) == 1
        assert limited[0]["timestamp"] == "2025-05-01T12:00:00"

    async def test_preferences(self, memory):
        memory._is_loaded = True
        memory._memory_cache = {
            "learned_preferences": {
                "preferred_project_types": {"value": "bathroom", "count": 3},
                "timeline_preference": {"value": "1-3 months", "count": 1}
            }
        }
        
        # Test getting a preference
        assert memory.get_preference("preferred_project_types") == "bathroom"
        assert memory.get_preference("non_existent") is None
        
        # Test getting all preferences
        all_prefs = memory.get_all_preferences()
        assert len(all_prefs) == 2
        assert all_prefs["preferred_project_types"] == "bathroom"
        assert all_prefs["timeline_preference"] == "1-3 months"

    async def test_extract_preferences(self, memory, mock_db):
        memory._is_loaded = True
        memory._memory_cache = {"learned_preferences": {}}
        
        # Set up the mock
        memory._update_preference = AsyncMock()
        
        # Test project_creation preferences
        interaction_data = {"project_type": "kitchen", "timeline": "3-6 months"}
        await memory._extract_preferences("project_creation", interaction_data)
        
        # Verify it called update_preference with the right values
        assert memory._update_preference.call_count == 2
        memory._update_preference.assert_any_call(
            "preferred_project_types", "kitchen", "project_creation"
        )
        memory._update_preference.assert_any_call(
            "timeline_preference", "3-6 months", "project_creation"
        )

    async def test_update_preference(self, memory, mock_db):
        memory._is_loaded = True
        memory._memory_cache = {"learned_preferences": {}}
        
        # Test adding a new preference
        await memory._update_preference("color_preference", "blue", "user_selection")
        
        assert "color_preference" in memory._memory_cache["learned_preferences"]
        assert memory._memory_cache["learned_preferences"]["color_preference"]["value"] == "blue"
        assert memory._memory_cache["learned_preferences"]["color_preference"]["count"] == 1
        assert memory._is_dirty is True
        
        # Verify database call
        mock_db.table.assert_called_with("user_preferences")
        mock_db.upsert.assert_called_once()
        
        # Test strengthening an existing preference
        memory._is_dirty = False
        await memory._update_preference("color_preference", "blue", "user_selection")
        
        assert memory._memory_cache["learned_preferences"]["color_preference"]["count"] == 2
        assert memory._is_dirty is True