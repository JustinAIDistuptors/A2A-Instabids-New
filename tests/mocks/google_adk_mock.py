"""
Mock module for Google ADK.

This module provides mock implementations of Google ADK classes and functions
for testing purposes.
"""

from unittest.mock import MagicMock
import asyncio
from typing import List, Dict, Any, Optional
import sys

# Mock enable_tracing function
enable_tracing = MagicMock()

# Create a module for google.adk.memory
class Memory:
    """Mock Memory class."""
    
    def __init__(self):
        self.data = {}
        
    def get(self, key, default=None):
        """Get value from memory."""
        return self.data.get(key, default)
        
    def set(self, key, value):
        """Set value in memory."""
        self.data[key] = value
        
    def clear(self):
        """Clear memory."""
        self.data.clear()
    
    async def load(self):
        """Mock async load method."""
        return True
    
    async def save(self):
        """Mock async save method."""
        return True
    
    async def add_interaction(self, interaction_type, data):
        """Mock add_interaction method."""
        return True
    
    def get_recent_interactions(self, interaction_type=None, limit=10):
        """Mock get_recent_interactions method."""
        return []
    
    def get_preference(self, preference_key):
        """Mock get_preference method."""
        return None
    
    def get_all_preferences(self):
        """Mock get_all_preferences method."""
        return {}

# Create the memory module
memory_module = type(sys)("google.adk.memory")
memory_module.Memory = Memory
sys.modules["google.adk.memory"] = memory_module

# Mock LlmAgent class
class LlmAgent:
    """Mock LLM Agent."""
    
    def __init__(self, name=None, tools=None, system_prompt=None, memory=None):
        self.name = name
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.memory = memory or Memory()
    
    async def chat(self, message):
        """Mock chat method."""
        await asyncio.sleep(0.01)  # Simulate async operation
        return AgentMessage(f"Mock response from {self.name}")
    
    async def gather_project_info(self, user_id, description=None):
        """Mock gather_project_info method."""
        return {
            "need_more": True,
            "question": "What specific work is needed for your project?"
        }

# Mock messages module
class UserMessage:
    """Mock User Message."""
    
    def __init__(self, text=None, metadata=None):
        self.text = text or ""
        self.metadata = metadata or {}
        self.content = text
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "text": self.text,
            "role": "user",
            "metadata": self.metadata
        }


class AgentMessage:
    """Mock Agent Message."""
    
    def __init__(self, text=None, metadata=None):
        self.text = text or ""
        self.metadata = metadata or {}
        self.content = text
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "text": self.text,
            "role": "assistant",
            "metadata": self.metadata
        }
