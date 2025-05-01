"""Unit tests for HomeownerAgent (vision mocked)."""
from unittest.mock import AsyncMock, patch

import pytest

from instabids.agents.factory import get_homeowner_agent


@pytest.mark.asyncio
async def test_homeowner_agent_classification(monkeypatch):
    # Mock the vision tool
    with patch("instabids.agents.homeowner_agent.openai_vision_tool") as mock_vision:
        mock_vision.call = AsyncMock(return_value={"type": "kitchen"})
        agent = get_homeowner_agent()
        res = await agent.process_input(
            user_id="user123",
            description="I want a dream kitchen remodel",
            image_paths=[],
        )
        assert res["category"] == "Multi‑Phase Project"
        assert res["urgency"] == "Dream"
