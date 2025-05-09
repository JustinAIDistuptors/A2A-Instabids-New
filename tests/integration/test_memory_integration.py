#!/usr/bin/env python
"""
Integration tests for the memory module with A2A communication.

These tests verify that the memory system works correctly with
the A2A communication system. They require a live Supabase instance
and are intended to be run in the CI/CD pipeline.
"""

import unittest
import asyncio
import os
import uuid
from datetime import datetime

import pytest

from src.memory import IntegratedMemory, MemoryManager
from src.a2a_types.core import Agent


@pytest.mark.integration
class TestMemoryIntegration(unittest.TestCase):
    """Integration tests for memory with A2A communication."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once per test run."""
        # Check if Supabase credentials are set
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
            pytest.skip("Supabase credentials not set - skipping integration tests")
            
    def setUp(self):
        """Set up test environment before each test."""
        self.memory_manager = MemoryManager()
        # Generate unique user ID for each test
        self.user_id = f"test-user-{uuid.uuid4()}"
        # Test agent IDs
        self.agent1_id = "test-agent-1"
        self.agent2_id = "test-agent-2"
        
        # Initialize memory manager
        assert self.memory_manager.initialize(), "Failed to initialize memory manager"
    
    async def test_user_memory_lifecycle(self):
        """Test creating, using, and deleting user memory."""
        # Get memory for user
        memory = await self.memory_manager.get_user_memory(self.user_id)
        assert memory is not None, "Failed to get user memory"
        
        # Set some data
        memory.add_message("user", "Hello, world!")
        memory.add_multi_modal_input("image-1", "image", {"url": "https://example.com/image.jpg"})
        memory.set("favorite_color", "blue")
        
        # Save to database
        assert await memory.save(), "Failed to save memory"
        
        # Get memory again to verify persistence
        memory2 = await self.memory_manager.get_user_memory(self.user_id)
        assert memory2 is not None, "Failed to get user memory again"
        
        # Verify data
        history = memory2.get_history()
        assert len(history) == 1, "History not persisted"
        assert history[0]["role"] == "user", "Message role not persisted"
        assert history[0]["content"] == "Hello, world!", "Message content not persisted"
        
        multi_modal = memory2.get_multi_modal_context()
        assert "image-1" in multi_modal, "Multi-modal context not persisted"
        assert multi_modal["image-1"]["type"] == "image", "Multi-modal type not persisted"
        assert multi_modal["image-1"]["data"]["url"] == "https://example.com/image.jpg", "Multi-modal data not persisted"
        
        assert memory2.get("favorite_color") == "blue", "Memory value not persisted"
        
        # Clean up
        assert await self.memory_manager.clear_memory(self.user_id), "Failed to clear memory"
    
    async def test_user_preferences(self):
        """Test storing and retrieving user preferences."""
        # Get memory for user
        memory = await self.memory_manager.get_user_memory(self.user_id)
        assert memory is not None, "Failed to get user memory"
        
        # Add an interaction that should extract preferences
        interaction_data = {
            "project_type": "bathroom_remodel",
            "timeline": "3_months"
        }
        assert await memory.add_interaction("project_creation", interaction_data), "Failed to add interaction"
        
        # Save to database
        assert await memory.save(), "Failed to save memory"
        
        # Get preferences directly from database
        prefs = await self.memory_manager.get_user_preferences(self.user_id)
        assert "preferred_project_types" in prefs, "Preference not extracted"
        assert prefs["preferred_project_types"] == "bathroom_remodel", "Wrong preference value"
        assert "timeline_preference" in prefs, "Timeline preference not extracted"
        assert prefs["timeline_preference"] == "3_months", "Wrong timeline preference"
        
        # Clean up
        assert await self.memory_manager.clear_memory(self.user_id), "Failed to clear memory"
    
    async def test_agent_message_routing(self):
        """Test recording and retrieving agent messages."""
        # Get memory for user
        memory = await self.memory_manager.get_user_memory(self.user_id)
        assert memory is not None, "Failed to get user memory"
        
        # Create a task and message IDs
        task_id = f"task-{uuid.uuid4()}"
        message_id = f"msg-{uuid.uuid4()}"
        
        # Record a message between agents
        assert await memory.record_agent_message(
            message_id=message_id,
            task_id=task_id,
            sender_agent_id=self.agent1_id,
            recipient_agent_id=self.agent2_id,
            content="Hello from Agent 1",
            role="assistant",
            session_id="test-session"
        ), "Failed to record agent message"
        
        # Record the routing event
        assert await memory.record_message_routing(
            message_id=message_id,
            task_id=task_id,
            sender_agent_id=self.agent1_id,
            recipient_agent_id=self.agent2_id,
            route_status="delivered"
        ), "Failed to record message routing"
        
        # Get messages from the database
        messages = await self.memory_manager.get_agent_messages(task_id=task_id)
        assert len(messages) == 1, "Message not stored in database"
        assert messages[0]["message_id"] == message_id, "Wrong message ID"
        assert messages[0]["sender_agent_id"] == self.agent1_id, "Wrong sender ID"
        assert messages[0]["recipient_agent_id"] == self.agent2_id, "Wrong recipient ID"
        assert messages[0]["content"] == "Hello from Agent 1", "Wrong message content"
        
        # Get messages filtered by agent ID
        agent1_messages = await self.memory_manager.get_agent_messages(agent_id=self.agent1_id)
        assert len(agent1_messages) >= 1, "Agent 1 messages not found"
        
        agent2_messages = await self.memory_manager.get_agent_messages(agent_id=self.agent2_id)
        assert len(agent2_messages) >= 1, "Agent 2 messages not found"
        
        # Get messages filtered by session ID
        session_messages = await self.memory_manager.get_agent_messages(session_id="test-session")
        assert len(session_messages) >= 1, "Session messages not found"
        
        # Clean up
        assert await self.memory_manager.clear_memory(self.user_id), "Failed to clear memory"


if __name__ == "__main__":
    asyncio.run(TestMemoryIntegration().test_user_memory_lifecycle())
    asyncio.run(TestMemoryIntegration().test_user_preferences())
    asyncio.run(TestMemoryIntegration().test_agent_message_routing())
