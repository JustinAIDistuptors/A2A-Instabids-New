"""Integration test requiring local Supabase."""
import os
import pytest
from pathlib import Path

from instabids.agents.factory import get_homeowner_agent


@pytest.mark.skipif(
    "SUPABASE_URL" not in os.environ,
    reason="Supabase not configured for integration test",
)
@pytest.mark.asyncio
async def test_agent_supabase_roundtrip():
    agent = get_homeowner_agent()
    res = await agent.process_input(
        user_id="user123",
        description="Replace roof ASAP",
    )
    assert "project_id" in res, "Project should be persisted to Supabase"
    assert res["category"] == "One-Off Project"
    assert res["urgency"] == "Urgent"
