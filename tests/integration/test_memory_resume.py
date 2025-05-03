"""
Integration test for memory and preference recall functionality.
Tests that preferences are stored and recalled across sessions.
"""
import pytest
import asyncio
from unittest.mock import patch
from instabids.agents.factory import get_homeowner_agent
from instabids.data.pref_repo import get_pref, upsert_pref

@pytest.mark.integration
@pytest.mark.asyncio
async def test_resume_context(monkeypatch):
    """Test that agent can recall budget preferences from previous sessions."""
    # Mock the preference repository to avoid actual DB calls
    with patch('instabids.agents.homeowner_agent.upsert_pref') as mock_upsert, \
         patch('instabids.agents.homeowner_agent.get_pref') as mock_get:
        
        # Setup the mock to store and retrieve preferences in memory
        preferences = {}
        
        def mock_upsert_impl(user_id, key, value, confidence=0.5):
            preferences[(user_id, key)] = value
            return {"user_id": user_id, "pref_key": key, "pref_value": value}
        
        def mock_get_impl(user_id, key):
            return preferences.get((user_id, key))
        
        mock_upsert.side_effect = mock_upsert_impl
        mock_get.side_effect = mock_get_impl
        
        # Get a fresh agent instance
        agent = get_homeowner_agent()
        
        # First turn - user mentions budget in description
        # This should trigger preference learning
        await agent.gather_project_info(
            user_id="u222", 
            description="Need roof fix ~$8000"
        )
        
        # Verify preference was stored
        assert mock_upsert.called
        assert preferences.get(("u222", "default_budget")) == 8000
        
        # Second turn - new session should recall budget and not ask about it
        res = await agent.gather_project_info(
            user_id="u222", 
            description="continue"
        )
        
        # Verify preference was retrieved
        assert mock_get.called
        
        # Verify the question doesn't ask about budget
        if "need_more" in res and res["need_more"]:
            assert "budget" not in res.get("question", "").lower()
        
        # Additional check: if we have all slots filled, need_more should be False
        # If not all slots are filled, the next question should not be about budget
        if res.get("need_more", False):
            assert "budget" not in res.get("question", "").lower()