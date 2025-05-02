import pytest
from instabids.agents.factory import get_homeowner_agent

@pytest.mark.asyncio
async def test_slot_loop(monkeypatch):
    agent = get_homeowner_agent()
    r1 = await agent.process_input("u1", description="Need lawn mowing")
    assert r1["need_more"] and "specific work" in r1["question"].lower()