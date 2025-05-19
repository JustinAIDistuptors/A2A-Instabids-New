from google.adk import Agent
from instabids.tools import get_supabase_tools
from instabids.memory.persistent_memory import PersistentMemory

# Create a function to get the contractor agent with memory injection
def create_contractor_agent(memory: PersistentMemory = None) -> Agent:
    return Agent(
        name="ContractorDispatcher",
        tools=get_supabase_tools(),
        instruction=(
            "You represent a network of contractors. "
            "Given a project description, decide whether it matches your trade and, "
            "if so, submit a bid via the create_bid tool."
        ),
    )

# Default instance without memory for backward compatibility
ContractorAgent = create_contractor_agent()
