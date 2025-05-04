"""
Unit tests for the BidCardAgent.

Tests the functionality of the BidCardAgent class, including:
- Category mapping
- Creating bid cards from project data
- Updating bid cards
- Retrieving bid cards
"""
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from instabids.agents.bidcard_agent import BidCardAgent

# Test data
TEST_USER_ID = "test-user-123"
TEST_PROJECT_ID = "test-project-456"
TEST_BID_CARD_ID = "test-bidcard-789"

@pytest.fixture
def bid_card_agent():
    """Create a BidCardAgent instance."""
    return BidCardAgent(TEST_PROJECT_ID)

@pytest.fixture
def project_data():
    """Create sample project data."""
    return {
        "job_type": "roof repair",
        "budget": "1000-5000",
        "timeline": "Next month",
        "location": "123 Main St, Anytown, USA",
        "group_bidding": False,
        "description": "Need to repair leak in roof before rainy season."
    }

def test_map_category(bid_card_agent):
    """Test mapping job types to categories."""
    # Test direct matches
    assert bid_card_agent.map_category("roof repair") == "repair"
    assert bid_card_agent.map_category("kitchen renovation") == "renovation"
    assert bid_card_agent.map_category("window installation") == "installation"
    assert bid_card_agent.map_category("lawn maintenance") == "maintenance"
    assert bid_card_agent.map_category("new construction") == "construction"
    
    # Test case insensitivity
    assert bid_card_agent.map_category("ROOF REPAIR") == "repair"
    assert bid_card_agent.map_category("Kitchen Renovation") == "renovation"
    
    # Test partial matches
    assert bid_card_agent.map_category("repair my leaking roof") == "repair"
    assert bid_card_agent.map_category("need kitchen renovation work") == "renovation"
    
    # Test fallback to "other"
    assert bid_card_agent.map_category("unknown job type") == "other"
    assert bid_card_agent.map_category("") == "other"

def test_create_bid_card_from_project(bid_card_agent, project_data):
    """Test creating a bid card from project data."""
    # Mock the bidcard_repo.create_bid_card function
    with patch("instabids.data.bidcard_repo.create_bid_card") as mock_create:
        # Set up the mock return value
        mock_create.return_value = {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": "repair",
            "job_type": "roof repair",
            "budget_min": 1000,
            "budget_max": 5000,
            "timeline": "Next month",
            "location": "123 Main St, Anytown, USA",
            "group_bidding": False,
            "details": {"description": "Need to repair leak in roof before rainy season."},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Call the function
        result = bid_card_agent.create_bid_card_from_project(
            homeowner_id=TEST_USER_ID,
            project_data=project_data
        )
        
        # Verify the result
        assert result["id"] == TEST_BID_CARD_ID
        assert result["homeowner_id"] == TEST_USER_ID
        assert result["project_id"] == TEST_PROJECT_ID
        assert result["category"] == "repair"
        assert result["job_type"] == "roof repair"
        assert result["budget_min"] == 1000
        assert result["budget_max"] == 5000
        
        # Verify the call to bidcard_repo.create_bid_card
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert kwargs["homeowner_id"] == TEST_USER_ID
        assert kwargs["project_id"] == TEST_PROJECT_ID
        assert kwargs["category"] == "repair"
        assert kwargs["job_type"] == "roof repair"
        assert kwargs["budget_min"] == 1000
        assert kwargs["budget_max"] == 5000
        assert kwargs["timeline"] == "Next month"
        assert kwargs["location"] == "123 Main St, Anytown, USA"
        assert kwargs["group_bidding"] is False

def test_create_bid_card_with_single_budget_value(bid_card_agent):
    """Test creating a bid card with a single budget value."""
    # Create project data with a single budget value
    project_data = {
        "job_type": "roof repair",
        "budget": "5000",  # Single value
        "timeline": "Next month",
        "location": "123 Main St, Anytown, USA",
        "group_bidding": False
    }
    
    # Mock the bidcard_repo.create_bid_card function
    with patch("instabids.data.bidcard_repo.create_bid_card") as mock_create:
        # Set up the mock return value
        mock_create.return_value = {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": "repair",
            "job_type": "roof repair",
            "budget_min": 4000,  # 80% of 5000
            "budget_max": 6000,  # 120% of 5000
            "timeline": "Next month",
            "location": "123 Main St, Anytown, USA",
            "group_bidding": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Call the function
        result = bid_card_agent.create_bid_card_from_project(
            homeowner_id=TEST_USER_ID,
            project_data=project_data
        )
        
        # Verify the budget range calculation
        args, kwargs = mock_create.call_args
        assert kwargs["budget_min"] == 4000  # 80% of 5000
        assert kwargs["budget_max"] == 6000  # 120% of 5000

def test_create_bid_card_with_budget_format_variations(bid_card_agent):
    """Test creating a bid card with various budget format variations."""
    # Test different budget formats
    budget_formats = [
        ("$1,000-$5,000", 1000, 5000),
        ("1000 to 5000", 1000, 5000),
        ("$1,000 to $5,000", 1000, 5000),
        ("between $1,000 and $5,000", None, None)  # This format isn't supported
    ]
    
    for budget_str, expected_min, expected_max in budget_formats:
        # Create project data with the current budget format
        project_data = {
            "job_type": "roof repair",
            "budget": budget_str,
            "timeline": "Next month",
            "location": "123 Main St, Anytown, USA"
        }
        
        # Mock the bidcard_repo.create_bid_card function
        with patch("instabids.data.bidcard_repo.create_bid_card") as mock_create:
            # Set up the mock return value
            mock_create.return_value = {
                "id": TEST_BID_CARD_ID,
                "homeowner_id": TEST_USER_ID,
                "project_id": TEST_PROJECT_ID,
                "category": "repair",
                "job_type": "roof repair",
                "budget_min": expected_min,
                "budget_max": expected_max,
                "timeline": "Next month",
                "location": "123 Main St, Anytown, USA",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Call the function
            try:
                result = bid_card_agent.create_bid_card_from_project(
                    homeowner_id=TEST_USER_ID,
                    project_data=project_data
                )
                
                # If expected values are None, we don't expect specific values
                if expected_min is not None and expected_max is not None:
                    args, kwargs = mock_create.call_args
                    assert kwargs["budget_min"] == expected_min
                    assert kwargs["budget_max"] == expected_max
            except Exception as e:
                # If expected values are None, we expect an error
                if expected_min is not None and expected_max is not None:
                    pytest.fail(f"Unexpected error: {e}")

def test_update_bid_card(bid_card_agent):
    """Test updating a bid card."""
    # Mock the bidcard_repo.update_bid_card function
    with patch("instabids.data.bidcard_repo.update_bid_card") as mock_update:
        # Set up the mock return value
        mock_update.return_value = {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": "repair",
            "job_type": "roof repair",
            "budget_min": 2000,  # Updated value
            "budget_max": 6000,  # Updated value
            "timeline": "Next month",
            "location": "123 Main St, Anytown, USA",
            "group_bidding": True,  # Updated value
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Call the function
        updates = {
            "budget": "2000-6000",
            "group_bidding": True
        }
        result = bid_card_agent.update_bid_card(TEST_BID_CARD_ID, updates)
        
        # Verify the result
        assert result["id"] == TEST_BID_CARD_ID
        assert result["budget_min"] == 2000
        assert result["budget_max"] == 6000
        assert result["group_bidding"] is True
        
        # Verify the call to bidcard_repo.update_bid_card
        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        assert args[0] == TEST_BID_CARD_ID
        assert "budget_min" in args[1]
        assert args[1]["budget_min"] == 2000
        assert "budget_max" in args[1]
        assert args[1]["budget_max"] == 6000
        assert "group_bidding" in args[1]
        assert args[1]["group_bidding"] is True

def test_update_job_type_updates_category(bid_card_agent):
    """Test that updating job_type also updates category."""
    # Mock the bidcard_repo.update_bid_card function
    with patch("instabids.data.bidcard_repo.update_bid_card") as mock_update:
        # Set up the mock return value
        mock_update.return_value = {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": "renovation",  # Updated category
            "job_type": "kitchen renovation",  # Updated job_type
            "budget_min": 1000,
            "budget_max": 5000,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Call the function
        updates = {
            "job_type": "kitchen renovation"  # Changed from "roof repair"
        }
        result = bid_card_agent.update_bid_card(TEST_BID_CARD_ID, updates)
        
        # Verify that category was updated
        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        assert args[0] == TEST_BID_CARD_ID
        assert "category" in args[1]
        assert args[1]["category"] == "renovation"
        assert "job_type" in args[1]
        assert args[1]["job_type"] == "kitchen renovation"

def test_get_bid_card(bid_card_agent):
    """Test getting a bid card."""
    # Mock the bidcard_repo.get_bid_card function
    with patch("instabids.data.bidcard_repo.get_bid_card") as mock_get:
        # Set up the mock return value
        mock_get.return_value = {
            "id": TEST_BID_CARD_ID,
            "homeowner_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "category": "repair",
            "job_type": "roof repair",
            "budget_min": 1000,
            "budget_max": 5000,
            "timeline": "Next month",
            "location": "123 Main St, Anytown, USA",
            "group_bidding": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Call the function
        result = bid_card_agent.get_bid_card(TEST_BID_CARD_ID)
        
        # Verify the result
        assert result["id"] == TEST_BID_CARD_ID
        assert result["homeowner_id"] == TEST_USER_ID
        assert result["project_id"] == TEST_PROJECT_ID
        
        # Verify the call to bidcard_repo.get_bid_card
        mock_get.assert_called_once_with(TEST_BID_CARD_ID)

def test_get_bid_cards_for_project(bid_card_agent):
    """Test getting bid cards for a project."""
    # Mock the bidcard_repo.get_bid_cards_by_project function
    with patch("instabids.data.bidcard_repo.get_bid_cards_by_project") as mock_get:
        # Set up the mock return value
        mock_get.return_value = [
            {
                "id": TEST_BID_CARD_ID,
                "homeowner_id": TEST_USER_ID,
                "project_id": TEST_PROJECT_ID,
                "category": "repair",
                "job_type": "roof repair"
            },
            {
                "id": "test-bidcard-999",
                "homeowner_id": TEST_USER_ID,
                "project_id": TEST_PROJECT_ID,
                "category": "repair",
                "job_type": "gutter repair"
            }
        ]
        
        # Call the function
        results = bid_card_agent.get_bid_cards_for_project()
        
        # Verify the results
        assert len(results) == 2
        assert results[0]["id"] == TEST_BID_CARD_ID
        assert results[1]["id"] == "test-bidcard-999"
        
        # Verify the call to bidcard_repo.get_bid_cards_by_project
        mock_get.assert_called_once_with(TEST_PROJECT_ID)

def test_delete_bid_card(bid_card_agent):
    """Test deleting a bid card."""
    # Mock the bidcard_repo.delete_bid_card function
    with patch("instabids.data.bidcard_repo.delete_bid_card") as mock_delete:
        # Set up the mock return value
        mock_delete.return_value = True
        
        # Call the function
        result = bid_card_agent.delete_bid_card(TEST_BID_CARD_ID)
        
        # Verify the result
        assert result is True
        
        # Verify the call to bidcard_repo.delete_bid_card
        mock_delete.assert_called_once_with(TEST_BID_CARD_ID)

def test_extract_details(bid_card_agent, project_data):
    """Test extracting details from project data."""
    # Call the function
    details = bid_card_agent._extract_details(project_data)
    
    # Verify that excluded fields are not in details
    assert "job_type" not in details
    assert "budget" not in details
    assert "timeline" not in details
    assert "location" not in details
    assert "group_bidding" not in details
    
    # Verify that other fields are in details
    assert "description" in details
    assert details["description"] == "Need to repair leak in roof before rainy season."