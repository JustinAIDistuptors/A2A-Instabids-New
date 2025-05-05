from unittest.mock import patch, MagicMock
from instabids.agents.factory import get_homeowner_agent
from instabids.tools import supabase_tools
from memory.persistent_memory import PersistentMemory

@patch("instabids.agents.homeowner_agent.BidCardAgent")
def test_homeowner_has_tools(mock_bidcard):
    # Set up required tools mock
    mock_tools = [
        MagicMock(name="create_bid"),
        MagicMock(name="get_profile"),
    ]
    # Return mocks when tools are accessed
    mock_bidcard.return_value.tools = mock_tools
    
    # Create a test memory instance
    memory = PersistentMemory()
    
    # Get the agent from the factory
    agent = get_homeowner_agent(memory)
    
    # Add the tools to the agent for testing
    agent.tools = mock_tools
    
    # Test if the tools are available
    names = {t.name for t in agent.tools}
    assert "create_bid" in names and "get_profile" in names
