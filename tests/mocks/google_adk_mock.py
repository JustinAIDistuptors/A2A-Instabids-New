"""
Mock module for Google ADK.

This module provides mock implementations of Google ADK classes and functions
for testing purposes.
"""

from unittest.mock import MagicMock

# Mock enable_tracing function
enable_tracing = MagicMock()


class MockADKMessage:
    """Mock ADK Message."""
    
    def __init__(self, text=None, role=None, metadata=None):
        self.text = text or ""
        self.role = role or "user"
        self.metadata = metadata or {}
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "text": self.text,
            "role": self.role,
            "metadata": self.metadata
        }


class MockADKResponse:
    """Mock ADK Response."""
    
    def __init__(self, text=None, metadata=None):
        self.text = text or ""
        self.metadata = metadata or {}
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "text": self.text,
            "metadata": self.metadata
        }


class MockUserMessage(MockADKMessage):
    """Mock User Message."""
    
    def __init__(self, text=None, metadata=None):
        super().__init__(text=text, role="user", metadata=metadata)


class MockAgentMessage(MockADKMessage):
    """Mock Agent Message."""
    
    def __init__(self, text=None, metadata=None):
        super().__init__(text=text, role="assistant", metadata=metadata)


# Export mock classes
__all__ = [
    "enable_tracing",
    "MockADKMessage",
    "MockADKResponse",
    "MockUserMessage",
    "MockAgentMessage"
]
