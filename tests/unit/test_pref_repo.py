"""
Unit tests for the preference and feedback repository.

Tests the functionality of the preference repository, including:
- Creating and updating preferences
- Retrieving preferences
- Deleting preferences
- Saving user feedback
"""
import pytest
import os
import json
from unittest.mock import patch, MagicMock

from instabids.data.pref_repo import (
    upsert_pref,
    get_pref,
    get_prefs,
    get_all_prefs,
    delete_pref,
    save_feedback
)

# Test data
TEST_USER_ID = "test-user-123"
TEST_PREF_KEY = "test-pref"
TEST_PREF_VALUE = {"setting": "value", "enabled": True}

# Mock Supabase response
MOCK_RESPONSE = MagicMock()
MOCK_RESPONSE.data = [
    {
        "id": "1",
        "user_id": TEST_USER_ID,
        "preference_key": TEST_PREF_KEY,
        "preference_value": json.dumps(TEST_PREF_VALUE),
        "confidence": 0.8,
        "updated_at": "2025-05-04T00:00:00Z"
    }
]

@pytest.fixture
def mock_supabase():
    """Mock the Supabase client."""
    with patch("instabids.data.pref_repo._sb") as mock_sb:
        # Set up the mock table method and chain
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        
        # Set up the mock select method and chain
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        
        # Set up the mock eq method and chain
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.eq.return_value = mock_eq
        mock_eq.execute.return_value = MOCK_RESPONSE
        
        # Set up the mock insert/upsert method and chain
        mock_table.upsert.return_value.execute.return_value = MOCK_RESPONSE
        mock_table.insert.return_value.execute.return_value = MOCK_RESPONSE
        
        # Set up the mock delete method and chain
        mock_table.delete.return_value = mock_eq
        
        yield mock_sb

def test_upsert_pref(mock_supabase):
    """Test creating or updating a preference."""
    result = upsert_pref(TEST_USER_ID, TEST_PREF_KEY, TEST_PREF_VALUE)
    
    # Verify the result
    assert result == MOCK_RESPONSE.data[0]
    
    # Verify the Supabase call
    mock_supabase.table.assert_called_once_with("user_preferences")
    mock_supabase.table().upsert.assert_called_once()
    mock_supabase.table().upsert().execute.assert_called_once()
    
    # Verify the data passed to upsert
    args, kwargs = mock_supabase.table().upsert.call_args
    assert args[0]["user_id"] == TEST_USER_ID
    assert args[0]["preference_key"] == TEST_PREF_KEY
    assert json.loads(args[0]["preference_value"]) == TEST_PREF_VALUE

def test_get_pref(mock_supabase):
    """Test retrieving a specific preference."""
    result = get_pref(TEST_USER_ID, TEST_PREF_KEY)
    
    # Verify the result
    assert result == TEST_PREF_VALUE
    
    # Verify the Supabase call
    mock_supabase.table.assert_called_once_with("user_preferences")
    mock_supabase.table().select.assert_called_once()
    mock_supabase.table().select().eq.assert_called_once_with("user_id", TEST_USER_ID)
    mock_supabase.table().select().eq().eq.assert_called_once_with("preference_key", TEST_PREF_KEY)
    mock_supabase.table().select().eq().eq().execute.assert_called_once()

def test_get_pref_not_found(mock_supabase):
    """Test retrieving a non-existent preference."""
    # Set up the mock to return empty data
    mock_supabase.table().select().eq().eq().execute.return_value.data = []
    
    result = get_pref(TEST_USER_ID, TEST_PREF_KEY)
    
    # Verify the result is None
    assert result is None

def test_get_prefs(mock_supabase):
    """Test retrieving all preferences as a simple dictionary."""
    # Set up the mock to return multiple preferences
    mock_supabase.table().select().eq().execute.return_value.data = [
        {
            "preference_key": "pref1",
            "preference_value": json.dumps("value1")
        },
        {
            "preference_key": "pref2",
            "preference_value": json.dumps({"nested": "value2"})
        }
    ]
    
    result = get_prefs(TEST_USER_ID)
    
    # Verify the result
    assert result == {
        "pref1": "value1",
        "pref2": {"nested": "value2"}
    }
    
    # Verify the Supabase call
    mock_supabase.table.assert_called_once_with("user_preferences")
    mock_supabase.table().select.assert_called_once_with("*")
    mock_supabase.table().select().eq.assert_called_once_with("user_id", TEST_USER_ID)
    mock_supabase.table().select().eq().execute.assert_called_once()

def test_get_all_prefs(mock_supabase):
    """Test retrieving all preferences with metadata."""
    # Set up the mock to return multiple preferences with metadata
    mock_supabase.table().select().eq().execute.return_value.data = [
        {
            "preference_key": "pref1",
            "preference_value": json.dumps("value1"),
            "confidence": 0.7,
            "updated_at": "2025-05-03T00:00:00Z"
        },
        {
            "preference_key": "pref2",
            "preference_value": json.dumps({"nested": "value2"}),
            "confidence": 0.9,
            "updated_at": "2025-05-04T00:00:00Z"
        }
    ]
    
    result = get_all_prefs(TEST_USER_ID)
    
    # Verify the result includes metadata
    assert "pref1" in result
    assert "pref2" in result
    assert result["pref1"]["value"] == "value1"
    assert result["pref1"]["confidence"] == 0.7
    assert result["pref2"]["value"] == {"nested": "value2"}
    assert result["pref2"]["confidence"] == 0.9

def test_delete_pref(mock_supabase):
    """Test deleting a preference."""
    result = delete_pref(TEST_USER_ID, TEST_PREF_KEY)
    
    # Verify the result
    assert result is True
    
    # Verify the Supabase call
    mock_supabase.table.assert_called_once_with("user_preferences")
    mock_supabase.table().delete.assert_called_once()
    mock_supabase.table().delete().eq.assert_called_once_with("user_id", TEST_USER_ID)
    mock_supabase.table().delete().eq().eq.assert_called_once_with("preference_key", TEST_PREF_KEY)
    mock_supabase.table().delete().eq().eq().execute.assert_called_once()

def test_delete_pref_not_found(mock_supabase):
    """Test deleting a non-existent preference."""
    # Set up the mock to return empty data
    mock_supabase.table().delete().eq().eq().execute.return_value.data = []
    
    result = delete_pref(TEST_USER_ID, TEST_PREF_KEY)
    
    # Verify the result is False
    assert result is False

def test_save_feedback(mock_supabase):
    """Test saving user feedback."""
    result = save_feedback(TEST_USER_ID, 5, "Great service!")
    
    # Verify the result
    assert result == MOCK_RESPONSE.data[0]
    
    # Verify the Supabase call
    mock_supabase.table.assert_called_once_with("user_feedback")
    mock_supabase.table().insert.assert_called_once()
    mock_supabase.table().insert().execute.assert_called_once()
    
    # Verify the data passed to insert
    args, kwargs = mock_supabase.table().insert.call_args
    assert args[0]["user_id"] == TEST_USER_ID
    assert args[0]["rating"] == 5
    assert args[0]["comments"] == "Great service!"

def test_save_feedback_invalid_rating():
    """Test saving feedback with an invalid rating."""
    with pytest.raises(ValueError):
        save_feedback(TEST_USER_ID, 6, "Invalid rating")
    
    with pytest.raises(ValueError):
        save_feedback(TEST_USER_ID, 0, "Invalid rating")