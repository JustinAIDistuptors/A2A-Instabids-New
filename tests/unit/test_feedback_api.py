"""
Unit tests for the feedback API.

Tests the functionality of the feedback API routes, including:
- Submitting feedback
- Retrieving feedback
- Error handling
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

from instabids.api.routes.feedback import router as feedback_router

# Create test app
app = FastAPI()
app.include_router(feedback_router)
client = TestClient(app)

# Test data
TEST_USER_ID = "test-user-123"
TEST_RATING = 4
TEST_COMMENTS = "Great service!"

# Mock response
MOCK_RESPONSE = MagicMock()
MOCK_RESPONSE.data = [
    {
        "id": "1",
        "user_id": TEST_USER_ID,
        "rating": TEST_RATING,
        "comments": TEST_COMMENTS,
        "created_at": "2025-05-04T00:00:00Z"
    }
]

@pytest.fixture
def mock_supabase():
    """Mock the Supabase client."""
    with patch("instabids.data.pref_repo._sb") as mock_sb:
        # Set up the mock table method and chain
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        
        # Set up the mock insert method and chain
        mock_table.insert.return_value.execute.return_value = MOCK_RESPONSE
        
        # Set up the mock select method and chain
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_select
        mock_select.order.return_value = mock_select
        mock_select.execute.return_value = MOCK_RESPONSE
        
        yield mock_sb

def test_give_feedback(mock_supabase):
    """Test submitting feedback."""
    # Prepare request data
    data = {
        "user_id": TEST_USER_ID,
        "rating": TEST_RATING,
        "comments": TEST_COMMENTS
    }
    
    # Make request
    response = client.post("/", json=data)
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["ok"] is True
    
    # Verify Supabase call
    mock_supabase.table.assert_called_once_with("user_feedback")
    mock_supabase.table().insert.assert_called_once()
    mock_supabase.table().insert().execute.assert_called_once()
    
    # Verify data passed to insert
    args, kwargs = mock_supabase.table().insert.call_args
    assert args[0]["user_id"] == TEST_USER_ID
    assert args[0]["rating"] == TEST_RATING
    assert args[0]["comments"] == TEST_COMMENTS

def test_give_feedback_invalid_rating():
    """Test submitting feedback with an invalid rating."""
    # Prepare request data with invalid rating
    data = {
        "user_id": TEST_USER_ID,
        "rating": 6,  # Invalid rating (> 5)
        "comments": TEST_COMMENTS
    }
    
    # Make request
    response = client.post("/", json=data)
    
    # Verify response
    assert response.status_code == 422  # Validation error

def test_get_user_feedback(mock_supabase):
    """Test retrieving user feedback."""
    # Make request
    response = client.get(f"/{TEST_USER_ID}")
    
    # Verify response
    assert response.status_code == 200
    assert "feedback" in response.json()
    assert len(response.json()["feedback"]) == 1
    assert response.json()["feedback"][0]["user_id"] == TEST_USER_ID
    
    # Verify Supabase call
    mock_supabase.table.assert_called_once_with("user_feedback")
    mock_supabase.table().select.assert_called_once_with("*")
    mock_supabase.table().select().eq.assert_called_once_with("user_id", TEST_USER_ID)
    mock_supabase.table().select().eq().order.assert_called_once_with("created_at", desc=True)
    mock_supabase.table().select().eq().order().execute.assert_called_once()

def test_get_user_feedback_error(mock_supabase):
    """Test error handling when retrieving feedback."""
    # Set up mock to raise an exception
    mock_supabase.table().select().eq().order().execute.side_effect = Exception("Database error")
    
    # Make request
    response = client.get(f"/{TEST_USER_ID}")
    
    # Verify response
    assert response.status_code == 500
    assert "detail" in response.json()