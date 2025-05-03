"""
Tests for the user preferences repository.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from instabids.data.pref_repo import upsert_pref, get_pref, get_all_prefs, delete_pref

@pytest.fixture
def mock_supabase():
    """Mock the Supabase client for testing."""
    with patch("instabids.data.pref_repo._sb") as mock_sb:
        # Setup mock responses
        mock_execute = MagicMock()
        mock_sb.table.return_value.upsert.return_value.execute = mock_execute
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = mock_execute
        mock_sb.table.return_value.select.return_value.eq.return_value.execute = mock_execute
        mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute = mock_execute
        
        yield mock_sb, mock_execute

def test_upsert_pref(mock_supabase):
    """Test creating/updating a user preference."""
    mock_sb, mock_execute = mock_supabase
    mock_execute.return_value.data = [{"pref_key": "theme", "pref_value": "\"dark\""}]
    
    # Test with simple string value
    result = upsert_pref("user123", "theme", "dark")
    
    # Verify correct table and data
    mock_sb.table.assert_called_with("user_preferences")
    mock_sb.table.return_value.upsert.assert_called_once()
    
    # Check the data being inserted
    call_args = mock_sb.table.return_value.upsert.call_args[0][0]
    assert call_args["user_id"] == "user123"
    assert call_args["pref_key"] == "theme"
    assert json.loads(call_args["pref_value"]) == "dark"
    
    # Test with complex object
    complex_pref = {"colors": {"primary": "#ff0000", "secondary": "#00ff00"}}
    upsert_pref("user123", "ui_settings", complex_pref)
    
    # Check the data being inserted
    call_args = mock_sb.table.return_value.upsert.call_args[0][0]
    assert call_args["pref_key"] == "ui_settings"
    assert json.loads(call_args["pref_value"]) == complex_pref

def test_get_pref(mock_supabase):
    """Test retrieving a user preference."""
    mock_sb, mock_execute = mock_supabase
    
    # Test successful retrieval
    mock_execute.return_value.data = [{"pref_value": "\"dark\""}]
    result = get_pref("user123", "theme")
    assert result == "dark"
    
    # Test complex object retrieval
    complex_obj = {"colors": {"primary": "#ff0000"}}
    mock_execute.return_value.data = [{"pref_value": json.dumps(complex_obj)}]
    result = get_pref("user123", "ui_settings")
    assert result == complex_obj
    
    # Test non-existent preference
    mock_execute.return_value.data = []
    result = get_pref("user123", "nonexistent")
    assert result is None

def test_get_all_prefs(mock_supabase):
    """Test retrieving all preferences for a user."""
    mock_sb, mock_execute = mock_supabase
    
    # Setup mock data
    mock_execute.return_value.data = [
        {"pref_key": "theme", "pref_value": "\"dark\""},
        {"pref_key": "notifications", "pref_value": "true"},
        {"pref_key": "ui_settings", "pref_value": "{\"colors\":{\"primary\":\"#ff0000\"}}"}
    ]
    
    # Get all preferences
    result = get_all_prefs("user123")
    
    # Verify results
    assert result["theme"] == "dark"
    assert result["notifications"] == True
    assert result["ui_settings"]["colors"]["primary"] == "#ff0000"
    
    # Test with empty result
    mock_execute.return_value.data = []
    result = get_all_prefs("user123")
    assert result == {}

def test_delete_pref(mock_supabase):
    """Test deleting a user preference."""
    mock_sb, mock_execute = mock_supabase
    
    # Test successful deletion
    mock_execute.return_value.data = [{"pref_key": "theme"}]
    result = delete_pref("user123", "theme")
    assert result is True
    
    # Test deletion of non-existent preference
    mock_execute.return_value.data = []
    result = delete_pref("user123", "nonexistent")
    assert result is False