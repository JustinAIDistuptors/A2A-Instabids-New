"""Mock implementation of Google ADK classes for testing."""
from typing import Dict, Any, List, Optional


class LlmAgent:
    """Mock LlmAgent class for testing."""
    
    def __init__(self, name: str = "MockAgent", system_prompt: str = "", tools: Optional[List[Any]] = None):
        """Initialize a mock LlmAgent."""
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []


def enable_tracing(output: str = "stdout"):
    """Mock enable_tracing function for testing."""
    return None
