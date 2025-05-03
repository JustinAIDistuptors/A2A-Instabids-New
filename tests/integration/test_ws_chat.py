"""
Integration tests for WebSocket chat functionality.
"""
import pytest
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from instabids.api.app import app

# Create test client
client = TestClient(app)

@pytest.mark.integration
def test_ws_roundtrip():
    """Test a basic WebSocket chat round-trip with the agent."""
    # Mock the agent's process_input method to return a predictable response
    with patch('instabids.agents.homeowner_agent.HomeownerAgent.gather_project_info', 
               new_callable=AsyncMock) as mock_process:
        
        # Set up the mock response
        mock_process.return_value = {
            "need_more": True,
            "question": "What specific work is needed for your roof?"
        }
        
        # Connect to the WebSocket
        with client.websocket_connect("/ws/chat/proj1") as ws:  # pytest WS pattern
            # Send a message
            ws.send_json({"user_id": "u1", "text": "Need roof fix $8k"})
            
            # Receive the response
            data = json.loads(ws.receive_text())
            
            # Verify the response
            assert data["need_more"] is True
            assert "question" in data
            assert "roof" in data["question"].lower()
            
            # Verify the mock was called with the correct parameters
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args["user_id"] == "u1"
            assert "roof fix $8k" in call_args["description"]

@pytest.mark.integration
def test_ws_missing_user_id():
    """Test error handling when user_id is missing."""
    with client.websocket_connect("/ws/chat/proj1") as ws:
        # Send a message without user_id
        ws.send_json({"text": "Need roof fix"})
        
        # Receive the error response
        data = json.loads(ws.receive_text())
        
        # Verify the error response
        assert "error" in data
        assert "user_id" in data["error"]
        assert data["status"] == 400

@pytest.mark.integration
def test_ws_conversation_completion():
    """Test that WebSocket closes when conversation is complete."""
    with patch('instabids.agents.homeowner_agent.HomeownerAgent.gather_project_info', 
               new_callable=AsyncMock) as mock_process:
        
        # Set up the mock to indicate conversation is complete
        mock_process.return_value = {
            "need_more": False,
            "project": {"id": "proj1", "title": "Roof Fix", "budget_range": "$8000"}
        }
        
        # Connect to the WebSocket
        with client.websocket_connect("/ws/chat/proj1") as ws:
            # Send a message
            ws.send_json({"user_id": "u1", "text": "Complete my project details"})
            
            # Receive the response
            data = json.loads(ws.receive_text())
            
            # Verify the response indicates completion
            assert data["need_more"] is False
            assert "project" in data
            
            # The WebSocket should close automatically
            # Testing this is tricky, but we can check that the next receive would fail
            with pytest.raises(Exception):
                ws.receive_text(timeout=1.0)