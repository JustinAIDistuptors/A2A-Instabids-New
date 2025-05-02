from instabids_google.adk import LlmAgent as Agent
from instabids.tools import supabase_tools
from memory.persistent_memory import PersistentMemory

# Create a function to get the contractor agent with memory injection
def create_contractor_agent(memory: PersistentMemory = None) -> Agent:
    """
    Create a contractor agent with optional memory injection.
    
    Args:
        memory: Optional persistent memory system
        
    Returns:
        Agent instance configured for contractor operations
    """
    return Agent(
        name="ContractorDispatcher",
        tools=[*supabase_tools],
        system_prompt=(
            "You represent a network of contractors. "
            "Given a project description, decide whether it matches your trade and, "
            "if so, submit a bid via the create_bid tool."
        ),
        memory=memory,
    )

# Default instance without memory for backward compatibility
contractor_agent = create_contractor_agent()