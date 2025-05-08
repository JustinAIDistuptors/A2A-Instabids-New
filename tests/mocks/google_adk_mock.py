""" 
Mock module for Google ADK.

This module provides mock implementations of Google ADK classes and functions
for testing purposes.
"""

from unittest.mock import MagicMock
import asyncio

# Mock enable_tracing function
enable_tracing = MagicMock()

# Mock LlmAgent class
class LlmAgent:
    """Mock LLM Agent."""
    
    def __init__(self, name=None, tools=None, system_prompt=None, memory=None):
        self.name = name
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.memory = memory
    
    async def chat(self, message):
        """Mock chat method."""
        await asyncio.sleep(0.01)  # Simulate async operation
        return AgentMessage(f"Mock response from {self.name}")

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