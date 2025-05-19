"""Factory functions for creating agent instances."""
from typing import Optional
from instabids.agents.homeowner_agent import HomeownerAgent
from supabase import create_client, Client

# Debug: Print the path of instabids.memory before trying to import from it
try:
    import instabids.memory
    print(f"DEBUG [factory.py]: instabids.memory loaded from: {instabids.memory.__file__}")
except ImportError as e:
    print(f"DEBUG [factory.py]: Could not import instabids.memory: {e}")
except AttributeError:
    print(f"DEBUG [factory.py]: instabids.memory is a namespace package or __file__ is not set.")

from instabids.memory.persistent_memory import PersistentMemory
from instabids.db import supabase

# Singleton instance for efficient reuse
_homeowner_agent: Optional[HomeownerAgent] = None

def get_homeowner_agent(user_id_for_memory: Optional[str] = None) -> HomeownerAgent:
    """
    Get a HomeownerAgent instance, reusing the singleton if available.
    Args:
        user_id_for_memory: The user ID for whom the agent/memory is being fetched/created.
    Returns:
        HomeownerAgent instance
    """
    global _homeowner_agent
    
    # This simplified singleton will create one agent with one memory instance.
    # If called again, it returns the same agent.
    # A multi-user system would need a more sophisticated factory.
    if _homeowner_agent is None:
        db_client = supabase()
        # If no user_id is provided, use a default. 
        # In a real app, user_id should come from the request's authentication context.
        current_user_id = user_id_for_memory or "default_agent_user"
        
        mem_instance = PersistentMemory(db=db_client, user_id=current_user_id)
        _homeowner_agent = HomeownerAgent(memory=mem_instance)
        
    return _homeowner_agent