import pytest
import asyncio
from instabids.agents.bid_card_agent import BidCardAgent

TEST_PROJECT_ID = "test-project-123"

@pytest.fixture
def bid_card_agent():
    """Create a BidCardAgent instance."""
    agent = BidCardAgent()
    agent.project_id = TEST_PROJECT_ID
    return agent

@pytest.mark.asyncio
async def test_agent_refresh(bid_card_agent):
    """Test that the agent can refresh a bid card."""
    result = await bid_card_agent.process_input("user123", description="REFRESH")
    assert result["project_id"] == TEST_PROJECT_ID
