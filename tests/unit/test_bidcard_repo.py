"""
Unit tests for the bid card repository.

Tests the functionality of the bid card repository, including:
- Creating bid cards
- Retrieving bid cards
- Updating bid cards
- Deleting bid cards
- Searching for bid cards
"""
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from instabids.data import bidcard_repo

# Test data
TEST_USER_ID = "test-user-123"
TEST_PROJECT_ID = "test-project-456"
TEST_BID_CARD_ID = "test-bidcard-789"
TEST_CATEGORY = "repair"
TEST_JOB_TYPE = "roof repair"

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock_client = MagicMock()
    
    # Mock table method
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    
    # Mock insert method
    mock_table.insert.return_value.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE,
            "budget_min": 1000,
            "budget_max": 5000,
            "timeline": "Next month",
            "location": "123 Main St",
            "group_bidding": False,
            "details": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # Mock select method
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE,
            "budget_min": 1000,
            "budget_max": 5000,
            "timeline": "Next month",
            "location": "123 Main St",
            "group_bidding": False,
            "details": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # Mock update method
    mock_table.update.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE,
            "budget_min": 2000,  # Updated value
            "budget_max": 6000,  # Updated value
            "timeline": "Next month",
            "location": "123 Main St",
            "group_bidding": False,
            "details": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # Mock delete method
    mock_table.delete.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID
        }
    ]
    
    return mock_client

def test_create_bid_card(monkeypatch):
    """Test creating a bid card."""
    # Mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE,
            "budget_min": 1000,
            "budget_max": 5000,
            "timeline": "Next month",
            "location": "123 Main St",
            "group_bidding": False,
            "details": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # Patch the Supabase client
    monkeypatch.setattr(bidcard_repo, "_sb", mock_client)
    
    # Create a bid card
    result = bidcard_repo.create_bid_card(
        homeowner_id=TEST_USER_ID,
        project_id=TEST_PROJECT_ID,
        category=TEST_CATEGORY,
        job_type=TEST_JOB_TYPE,
        budget_min=1000,
        budget_max=5000,
        timeline="Next month",
        location="123 Main St",
        group_bidding=False,
        details={}
    )
    
    # Verify the result
    assert result["id"] == TEST_BID_CARD_ID
    assert result["homeowner_id"] == TEST_USER_ID
    assert result["project_id"] == TEST_PROJECT_ID
    assert result["category"] == TEST_CATEGORY
    assert result["job_type"] == TEST_JOB_TYPE
    assert result["budget_min"] == 1000
    assert result["budget_max"] == 5000
    
    # Verify the insert call
    mock_client.table.assert_called_with("bid_cards")
    mock_table.insert.assert_called_once()
    args, _ = mock_table.insert.call_args
    assert args[0]["homeowner_id"] == TEST_USER_ID
    assert args[0]["project_id"] == TEST_PROJECT_ID
    assert args[0]["category"] == TEST_CATEGORY
    assert args[0]["job_type"] == TEST_JOB_TYPE

def test_get_bid_card(monkeypatch):
    """Test getting a bid card by ID."""
    # Mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE,
            "budget_min": 1000,
            "budget_max": 5000,
            "timeline": "Next month",
            "location": "123 Main St",
            "group_bidding": False,
            "details": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # Patch the Supabase client
    monkeypatch.setattr(bidcard_repo, "_sb", mock_client)
    
    # Get a bid card
    result = bidcard_repo.get_bid_card(TEST_BID_CARD_ID)
    
    # Verify the result
    assert result["id"] == TEST_BID_CARD_ID
    assert result["homeowner_id"] == TEST_USER_ID
    assert result["project_id"] == TEST_PROJECT_ID
    
    # Verify the select call
    mock_client.table.assert_called_with("bid_cards")
    mock_table.select.assert_called_with("*")
    mock_select.eq.assert_called_with("id", TEST_BID_CARD_ID)

def test_get_bid_cards_by_homeowner(monkeypatch):
    """Test getting bid cards by homeowner ID."""
    # Mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_eq = MagicMock()
    mock_select.eq.return_value = mock_eq
    mock_eq.order.return_value.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE
        },
        {
            "id": "test-bidcard-999",
            "homeowner_id": TEST_USER_ID,
            "project_id": "test-project-888",
            "category": "renovation",
            "job_type": "kitchen renovation"
        }
    ]
    
    # Patch the Supabase client
    monkeypatch.setattr(bidcard_repo, "_sb", mock_client)
    
    # Get bid cards by homeowner
    results = bidcard_repo.get_bid_cards_by_homeowner(TEST_USER_ID)
    
    # Verify the results
    assert len(results) == 2
    assert results[0]["id"] == TEST_BID_CARD_ID
    assert results[1]["id"] == "test-bidcard-999"
    assert results[0]["homeowner_id"] == TEST_USER_ID
    assert results[1]["homeowner_id"] == TEST_USER_ID
    
    # Verify the select call
    mock_client.table.assert_called_with("bid_cards")
    mock_table.select.assert_called_with("*")
    mock_select.eq.assert_called_with("homeowner_id", TEST_USER_ID)
    mock_eq.order.assert_called_with("created_at", desc=True)

def test_update_bid_card(monkeypatch):
    """Test updating a bid card."""
    # Mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_update = MagicMock()
    mock_table.update.return_value = mock_update
    mock_eq = MagicMock()
    mock_update.eq.return_value = mock_eq
    mock_eq.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE,
            "budget_min": 2000,  # Updated value
            "budget_max": 6000,  # Updated value
            "timeline": "Next month",
            "location": "123 Main St",
            "group_bidding": False,
            "details": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # Patch the Supabase client
    monkeypatch.setattr(bidcard_repo, "_sb", mock_client)
    
    # Update a bid card
    updates = {
        "budget_min": 2000,
        "budget_max": 6000
    }
    result = bidcard_repo.update_bid_card(TEST_BID_CARD_ID, updates)
    
    # Verify the result
    assert result["id"] == TEST_BID_CARD_ID
    assert result["budget_min"] == 2000
    assert result["budget_max"] == 6000
    
    # Verify the update call
    mock_client.table.assert_called_with("bid_cards")
    mock_table.update.assert_called_once()
    args, _ = mock_table.update.call_args
    assert "budget_min" in args[0]
    assert args[0]["budget_min"] == 2000
    assert "budget_max" in args[0]
    assert args[0]["budget_max"] == 6000
    mock_update.eq.assert_called_with("id", TEST_BID_CARD_ID)

def test_delete_bid_card(monkeypatch):
    """Test deleting a bid card."""
    # Mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_delete = MagicMock()
    mock_table.delete.return_value = mock_delete
    mock_eq = MagicMock()
    mock_delete.eq.return_value = mock_eq
    mock_eq.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID
        }
    ]
    
    # Patch the Supabase client
    monkeypatch.setattr(bidcard_repo, "_sb", mock_client)
    
    # Delete a bid card
    result = bidcard_repo.delete_bid_card(TEST_BID_CARD_ID)
    
    # Verify the result
    assert result is True
    
    # Verify the delete call
    mock_client.table.assert_called_with("bid_cards")
    mock_table.delete.assert_called_once()
    mock_delete.eq.assert_called_with("id", TEST_BID_CARD_ID)

def test_search_bid_cards(monkeypatch):
    """Test searching for bid cards."""
    # Mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_in = MagicMock()
    mock_select.in_.return_value = mock_in
    mock_gte = MagicMock()
    mock_in.gte.return_value = mock_gte
    mock_lte = MagicMock()
    mock_gte.lte.return_value = mock_lte
    mock_or = MagicMock()
    mock_lte.or_.return_value = mock_or
    mock_order = MagicMock()
    mock_or.order.return_value = mock_order
    mock_limit = MagicMock()
    mock_order.limit.return_value = mock_limit
    mock_limit.execute.return_value.data = [
        {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": TEST_CATEGORY,
            "job_type": TEST_JOB_TYPE,
            "budget_min": 1000,
            "budget_max": 5000
        }
    ]
    
    # Patch the Supabase client
    monkeypatch.setattr(bidcard_repo, "_sb", mock_client)
    
    # Search for bid cards
    results = bidcard_repo.search_bid_cards(
        query="roof",
        categories=["repair"],
        min_budget=1000,
        max_budget=5000,
        limit=10
    )
    
    # Verify the results
    assert len(results) == 1
    assert results[0]["id"] == TEST_BID_CARD_ID
    assert results[0]["category"] == TEST_CATEGORY
    assert results[0]["job_type"] == TEST_JOB_TYPE
    
    # Verify the search call
    mock_client.table.assert_called_with("bid_cards")
    mock_table.select.assert_called_with("*")
    mock_select.in_.assert_called_with("category", ["repair"])
    mock_in.gte.assert_called_with("budget_min", 1000)
    mock_gte.lte.assert_called_with("budget_max", 5000)
    mock_lte.or_.assert_called_with("job_type.ilike.%roof%,location.ilike.%roof%")
    mock_or.order.assert_called_with("created_at", desc=True)
    mock_order.limit.assert_called_with(10)

def test_invalid_category(monkeypatch):
    """Test creating a bid card with an invalid category."""
    # Mock Supabase client
    mock_client = MagicMock()
    
    # Patch the Supabase client
    monkeypatch.setattr(bidcard_repo, "_sb", mock_client)
    
    # Try to create a bid card with an invalid category
    with pytest.raises(ValueError) as excinfo:
        bidcard_repo.create_bid_card(
            homeowner_id=TEST_USER_ID,
            project_id=TEST_PROJECT_ID,
            category="invalid_category",  # Invalid category
            job_type=TEST_JOB_TYPE,
            budget_min=1000,
            budget_max=5000
        )
    
    # Verify the error message
    assert "Invalid category" in str(excinfo.value)