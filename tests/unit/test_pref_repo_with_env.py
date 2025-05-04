"""
Unit tests for the preference repository with environment setup.

Tests the functionality of the preference repository with proper environment setup,
including:
- Setting up environment variables
- Mocking Supabase client
- Testing upsert and get functions
"""
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from instabids.data.pref_repo import upsert_pref, get_prefs

# Test data
TEST_USER_ID = "test-user-123"
TEST_PREF_KEY = "test-pref"
TEST_PREF_VALUE = {"setting": "value", "enabled": True}

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock_client = MagicMock()
    
    # Mock table method
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    
    # Mock insert/upsert method
    mock_table.upsert.return_value.execute.return_value.data = [
        {
            "user_id": TEST_USER_ID,
            "preference_key": TEST_PREF_KEY,
            "preference_value": json.dumps(TEST_PREF_VALUE)
        }
    ]
    
    # Mock select method
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value.execute.return_value.data = [
        {
            "preference_key": TEST_PREF_KEY,
            "preference_value": json.dumps(TEST_PREF_VALUE)
        }
    ]
    
    return mock_client

def test_upsert_and_get(tmp_path, monkeypatch):
    """Test upserting and retrieving preferences with environment setup."""
    # Set up environment variables
    monkeypatch.setenv("SUPABASE_URL", "http://stub")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "stub")
    
    # Mock Supabase client creation
    with patch("instabids.data.pref_repo.create_client") as mock_create_client:
        # Set up mock client
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Mock table method
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock upsert method
        mock_table.upsert.return_value.execute.return_value.data = [
            {
                "user_id": TEST_USER_ID,
                "preference_key": TEST_PREF_KEY,
                "preference_value": json.dumps(TEST_PREF_VALUE)
            }
        ]
        
        # Mock select method
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value.data = [
            {
                "preference_key": TEST_PREF_KEY,
                "preference_value": json.dumps(TEST_PREF_VALUE)
            }
        ]
        
        # Test upsert_pref
        result = upsert_pref(TEST_USER_ID, TEST_PREF_KEY, TEST_PREF_VALUE)
        
        # Verify upsert was called correctly
        mock_client.table.assert_called_with("user_preferences")
        mock_table.upsert.assert_called_once()
        
        # Get the arguments passed to upsert
        args, kwargs = mock_table.upsert.call_args
        assert args[0]["user_id"] == TEST_USER_ID
        assert args[0]["preference_key"] == TEST_PREF_KEY
        assert json.loads(args[0]["preference_value"]) == TEST_PREF_VALUE
        
        # Test get_prefs
        prefs = get_prefs(TEST_USER_ID)
        
        # Verify select was called correctly
        mock_client.table.assert_called_with("user_preferences")
        mock_table.select.assert_called_once_with("*")
        mock_select.eq.assert_called_once_with("user_id", TEST_USER_ID)
        
        # Verify the returned preferences
        assert TEST_PREF_KEY in prefs
        assert prefs[TEST_PREF_KEY] == TEST_PREF_VALUE

def test_upsert_and_get_with_temp_file(tmp_path, monkeypatch):
    """Test upserting and retrieving preferences with a temporary file."""
    # Create a temporary directory for test files
    test_dir = tmp_path / "test_prefs"
    test_dir.mkdir()
    test_file = test_dir / "test_pref.json"
    
    # Write test data to file
    test_file.write_text(json.dumps(TEST_PREF_VALUE))
    
    # Set up environment variables
    monkeypatch.setenv("SUPABASE_URL", "http://stub")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "stub")
    
    # Mock Supabase client creation
    with patch("instabids.data.pref_repo.create_client") as mock_create_client:
        # Set up mock client
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Mock table method
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock upsert method
        mock_table.upsert.return_value.execute.return_value.data = [
            {
                "user_id": TEST_USER_ID,
                "preference_key": TEST_PREF_KEY,
                "preference_value": json.dumps(TEST_PREF_VALUE)
            }
        ]
        
        # Mock select method
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value.data = [
            {
                "preference_key": TEST_PREF_KEY,
                "preference_value": json.dumps(TEST_PREF_VALUE)
            }
        ]
        
        # Test upsert_pref with file content
        with open(test_file, "r") as f:
            file_data = json.load(f)
            result = upsert_pref(TEST_USER_ID, TEST_PREF_KEY, file_data)
        
        # Verify upsert was called correctly
        mock_client.table.assert_called_with("user_preferences")
        mock_table.upsert.assert_called_once()
        
        # Get the arguments passed to upsert
        args, kwargs = mock_table.upsert.call_args
        assert args[0]["user_id"] == TEST_USER_ID
        assert args[0]["preference_key"] == TEST_PREF_KEY
        assert json.loads(args[0]["preference_value"]) == TEST_PREF_VALUE