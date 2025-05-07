"""
Mock module for Google ADK.

This module provides mock implementations of Google ADK classes and functions
for testing purposes.
"""

from unittest.mock import MagicMock

# Mock enable_tracing function
enable_tracing = MagicMock()

# Mock messages module
class UserMessage:
    """Mock User Message."""
    
    def __init__(self, text=None, metadata=None):
        self.text = text or ""
        self.metadata = metadata or {}
    
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
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "text": self.text,
            "role": "assistant",
            "metadata": self.metadata
        }
