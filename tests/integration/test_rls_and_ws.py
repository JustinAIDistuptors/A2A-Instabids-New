"""
Integration tests for WebSocket functionality and Row-Level Security (RLS).

These tests verify that:
1. WebSocket communication works correctly for authorized users
2. Row-Level Security prevents unauthorized access to messages
"""
import os
import json
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from instabids.api.app import app
from supabase import create_client

# Create test client
client = TestClient(app)

# Use service role client for admin operations
_sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])  # service role

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ws_and_rls(monkeypatch):
    """Test WebSocket communication and Row-Level Security."""
    # Mock the agent's process_input method to return a predictable response
    with patch('instabids.agents.homeowner_agent.HomeownerAgent.process_input', 
               new_callable=AsyncMock) as mock_process:
        
        # Set up the mock response
        mock_process.return_value = {
            "need_more": True,
            "question": "What specific work is needed for your repair?"
        }
        
        try:
            # Seed project row for u50
            proj = _sb.table("projects").insert(
                {"id": "proj50", "homeowner_id": "u50", "title": "tmp", "status": "open"}
            ).execute().data[0]
            
            # Test WebSocket communication
            with client.websocket_connect("/ws/chat/proj50") as ws:
                ws.send_json({"user_id": "u50", "text": "Repair $7,000"})
                resp = json.loads(ws.receive_text())
                assert resp["need_more"]
                assert "question" in resp
            
            # Verify RLS: anon cannot fetch other user's messages
            anon = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
            res = anon.table("messages").select("*").eq("project_id", "proj50").execute()
            assert res.data == []  # blocked by RLS
            
            # Verify service role can access the messages (bypass RLS)
            service_res = _sb.table("messages").select("*").eq("project_id", "proj50").execute()
            assert len(service_res.data) > 0  # Service role can see the messages
            
            # Verify the content of the messages
            assert any(msg["role"] == "homeowner" and "Repair $7,000" in msg["content"] 
                      for msg in service_res.data)
            
        finally:
            # Clean up test data
            try:
                # Delete messages first (due to foreign key constraints)
                _sb.table("messages").delete().eq("project_id", "proj50").execute()
                # Then delete the project
                _sb.table("projects").delete().eq("id", "proj50").execute()
            except Exception as e:
                print(f"Cleanup error (can be ignored in CI): {e}")