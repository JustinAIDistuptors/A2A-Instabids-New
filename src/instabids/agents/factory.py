"""Agent singleton factory & cache."""
from typing import Optional
from instabids_google.adk import LlmAgent, enable_tracing
from memory.persistent_memory import PersistentMemory
from .homeowner_agent import HomeownerAgent

# Initialize tracing
enable_tracing("stdout")

# Singleton instances
_homeowner_singleton: Optional[HomeownerAgent] = None
_contractor_singleton = None

def get_homeowner_agent(memory: Optional[PersistentMemory] = None) -> HomeownerAgent:
    """
    Return singleton HomeownerAgent with optional memory injection.
    
    Args:
        memory: Optional persistent memory instance to use
        
    Returns:
        HomeownerAgent: The singleton instance
    """
    global _homeowner_singleton
    if _homeowner_singleton is None:
        _homeowner_singleton = HomeownerAgent(memory=memory or PersistentMemory())
    return _homeowner_singleton