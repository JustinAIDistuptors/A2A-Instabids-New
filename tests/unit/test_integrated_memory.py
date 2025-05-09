#!/usr/bin/env python
"""
Unit tests for the integrated memory module.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.memory.integrated_memory import IntegratedMemory


class TestIntegratedMemory(unittest.TestCase):
    """Test cases for IntegratedMemory class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock database client
        self.mock_db = MagicMock()
        self.user_id = "test-user-123"
        
        # Create memory instance with mock db
        self.memory = IntegratedMemory(self.mock_db, self.user_id)
    
    def test_init(self):
        """Test memory initialization."""
        self.assertEqual(self.memory.db, self.mock_db)
        self.assertEqual(self.memory.user_id, self.user_id)
        self.assertFalse(self.memory._is_loaded)
        self.assertFalse(self.memory._is_dirty)
        self.assertEqual(self.memory._memory_cache, {})
    
    def test_add_message(self):
        """Test adding a message to conversation history."""
        # Set memory as loaded
        self.memory._is_loaded = True
        
        # Add a message
        self.memory.add_message("user", "Hello, world!")
        
        # Verify message was added
        self.assertEqual(len(self.memory.history), 1)
        self.assertEqual(self.memory.history[0]["role"], "user")
        self.assertEqual(self.memory.history[0]["content"], "Hello, world!")
        self.assertIn("timestamp", self.memory.history[0])
        self.assertTrue(self.memory._is_dirty)
    
    def test_add_multi_modal_input(self):
        """Test adding a multi-modal input."""
        # Set memory as loaded
        self.memory._is_loaded = True
        
        # Add multi-modal input
        input_data = {"url": "https://example.com/image.jpg", "width": 800, "height": 600}
        self.memory.add_multi_modal_input("image-1", "image", input_data)
        
        # Verify input was added
        self.assertIn("image-1", self.memory.multi_modal_context)
        self.assertEqual(self.memory.multi_modal_context["image-1"]["type"], "image")
        self.assertEqual(self.memory.multi_modal_context["image-1"]["data"], input_data)
        self.assertIn("timestamp", self.memory.multi_modal_context["image-1"])
        self.assertTrue(self.memory._is_dirty)
    
    def test_set_and_get_slot(self):
        """Test setting and getting slot values."""
        # Set memory as loaded
        self.memory._is_loaded = True
        
        # Set required slots
        self.memory.set_required_slots(["name", "email"])
        
        # Set optional slots
        self.memory.set_optional_slots(["phone"])
        
        # Set valid slots
        self.assertTrue(self.memory.set_slot("name", "John Doe"))
        self.assertTrue(self.memory.set_slot("email", "john@example.com"))
        self.assertTrue(self.memory.set_slot("phone", "123-456-7890"))
        
        # Set invalid slot
        self.assertFalse(self.memory.set_slot("address", "123 Main St"))
        
        # Get slots
        self.assertEqual(self.memory.get_slot("name"), "John Doe")
        self.assertEqual(self.memory.get_slot("email"), "john@example.com")
        self.assertEqual(self.memory.get_slot("phone"), "123-456-7890")
        self.assertIsNone(self.memory.get_slot("address"))
        self.assertEqual(self.memory.get_slot("address", "default"), "default")
        
        # Get all slots
        slots = self.memory.get_all_slots()
        self.assertEqual(slots, {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "123-456-7890"
        })
        
        # Check missing required slots
        self.assertEqual(self.memory.get_missing_required_slots(), set())
        
        # Reset a required slot
        self.memory.slots.pop("name")
        self.assertEqual(self.memory.get_missing_required_slots(), {"name"})
        self.assertFalse(self.memory.all_required_slots_filled())
    
    def test_get_history(self):
        """Test getting conversation history."""
        # Set memory as loaded
        self.memory._is_loaded = True
        
        # Add messages
        self.memory.add_message("user", "Hello")
        self.memory.add_message("assistant", "Hi there")
        
        # Get history
        history = self.memory.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "Hi there")
    
    def test_get_multi_modal_context(self):
        """Test getting multi-modal context."""
        # Set memory as loaded
        self.memory._is_loaded = True
        
        # Add multi-modal inputs
        input_data1 = {"url": "https://example.com/image1.jpg"}
        input_data2 = {"url": "https://example.com/image2.jpg"}
        self.memory.add_multi_modal_input("image-1", "image", input_data1)
        self.memory.add_multi_modal_input("image-2", "image", input_data2)
        
        # Get multi-modal context
        context = self.memory.get_multi_modal_context()
        self.assertEqual(len(context), 2)
        self.assertEqual(context["image-1"]["type"], "image")
        self.assertEqual(context["image-1"]["data"], input_data1)
        self.assertEqual(context["image-2"]["type"], "image")
        self.assertEqual(context["image-2"]["data"], input_data2)
    
    def test_memory_interface(self):
        """Test Memory interface implementation."""
        # Set memory as loaded
        self.memory._is_loaded = True
        
        # Set values
        self.memory.set("favorite_color", "blue")
        self.memory.set("favorite_number", 42)
        
        # Get values
        self.assertEqual(self.memory.get("favorite_color"), "blue")
        self.assertEqual(self.memory.get("favorite_number"), 42)
        self.assertIsNone(self.memory.get("nonexistent_key"))
        self.assertEqual(self.memory.get("nonexistent_key", "default"), "default")
    
    @patch("src.memory.integrated_memory.datetime")
    async def test_load_existing_memory(self, mock_datetime):
        """Test loading existing memory from database."""
        # Set up mock datetime
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.utcnow.return_value = mock_now
        mock_datetime.datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Set up mock database response
        memory_data = {
            "conversation_state": {
                "conversation_id": "conv-123",
                "history": [{"role": "user", "content": "Hello", "timestamp": "2023-01-01T10:00:00Z"}],
                "slots": {"name": "John"},
                "required_slots": ["name", "email"],
                "optional_slots": ["phone"],
                "multi_modal_context": {},
                "session_ids": ["session-1"]
            },
            "context": {
                "favorite_color": "blue"
            }
        }
        
        mock_response = MagicMock()
        mock_response.data = {"memory_data": memory_data}
        self.mock_db.table().select().eq().maybe_single().execute.return_value = mock_response
        
        # Load memory
        result = await self.memory.load()
        
        # Verify result
        self.assertTrue(result)
        self.assertTrue(self.memory._is_loaded)
        self.assertFalse(self.memory._is_dirty)
        self.assertEqual(self.memory._memory_cache, memory_data)
        self.assertEqual(self.memory.conversation_id, "conv-123")
        self.assertEqual(len(self.memory.history), 1)
        self.assertEqual(self.memory.slots, {"name": "John"})
        self.assertEqual(self.memory.required_slots, {"name", "email"})
        self.assertEqual(self.memory.optional_slots, {"phone"})
        self.assertEqual(self.memory.session_ids, {"session-1"})
    
    @patch("src.memory.integrated_memory.datetime")
    async def test_load_new_memory(self, mock_datetime):
        """Test loading new memory when none exists."""
        # Set up mock datetime
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.utcnow.return_value = mock_now
        mock_datetime.datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Set up mock database response - no existing memory
        mock_response = MagicMock()
        mock_response.data = None
        self.mock_db.table().select().eq().maybe_single().execute.return_value = mock_response
        
        # Load memory
        result = await self.memory.load()
        
        # Verify result
        self.assertTrue(result)
        self.assertTrue(self.memory._is_loaded)
        self.assertTrue(self.memory._is_dirty)
        
        # Verify database insert was called
        self.mock_db.table().upsert.assert_called_once()
    
    @patch("src.memory.integrated_memory.datetime")
    async def test_save(self, mock_datetime):
        """Test saving memory to database."""
        # Set up mock datetime
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.utcnow.return_value = mock_now
        mock_datetime.datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Set memory as loaded and dirty
        self.memory._is_loaded = True
        self.memory._is_dirty = True
        
        # Add some data
        self.memory.add_message("user", "Hello")
        self.memory.set_slot("name", "John")
        self.memory.set("favorite_color", "blue")
        
        # Set up mock database response
        mock_response = MagicMock()
        mock_response.data = [{"id": "123"}]
        self.mock_db.table().upsert().execute.return_value = mock_response
        
        # Save memory
        result = await self.memory.save()
        
        # Verify result
        self.assertTrue(result)
        self.assertFalse(self.memory._is_dirty)
        
        # Verify database upsert was called with correct data
        args = self.mock_db.table().upsert.call_args[0][0]
        self.assertEqual(args["user_id"], self.user_id)
        self.assertIn("memory_data", args)
        self.assertIn("updated_at", args)


if __name__ == "__main__":
    unittest.main()
