import uuid, os
import pytest
from instabids.data import bidcard_repo

# Mock Supabase environment variables if not running against real Supabase
# Consider using pytest-dotenv or fixtures for managing env vars

# Basic fixture to ensure necessary env vars are checked (optional)
@pytest.fixture(autouse=True)
def check_supabase_env_vars():
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"):
        pytest.skip("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required for this test")

def test_create_and_get_bid_card_roundtrip():
    """Tests basic creation and retrieval of a bid card."""
    homeowner_id = str(uuid.uuid4()) # Generate a unique ID for the test user
    project_id = str(uuid.uuid4())   # Generate a unique ID for the test project

    card_data = {
        "homeowner_id": homeowner_id,
        "project_id": project_id,
        "category": "repair", # Use a valid category
        "job_type": "Leaky faucet repair",
        "budget_min": 50.0,
        "budget_max": 150.0,
        "timeline": "Next week",
        "location": "123 Test St, Anytown, CA 90210",
        "group_bidding": False,
        "details": {"urgency": "high", "preferred_time": "morning"}
    }

    # Create the bid card
    created_bid = bidcard_repo.create_bid_card(**card_data)

    # Assertions on the created bid card
    assert created_bid is not None
    assert "id" in created_bid
    assert created_bid["homeowner_id"] == homeowner_id
    assert created_bid["project_id"] == project_id
    assert created_bid["category"] == "repair"
    assert created_bid["job_type"] == "Leaky faucet repair"
    assert created_bid["budget_min"] == 50.0
    assert created_bid["budget_max"] == 150.0
    assert created_bid["details"]["urgency"] == "high"

    # Fetch the bid card using its ID
    fetched_bid = bidcard_repo.get_bid_card(created_bid["id"])

    # Assertions on the fetched bid card
    assert fetched_bid is not None
    assert fetched_bid["id"] == created_bid["id"]
    assert fetched_bid["homeowner_id"] == homeowner_id
    # Compare relevant fields
    assert fetched_bid["category"] == card_data["category"]
    assert fetched_bid["job_type"] == card_data["job_type"]
    assert float(fetched_bid["budget_min"]) == card_data["budget_min"] # Supabase might return Decimal
    assert float(fetched_bid["budget_max"]) == card_data["budget_max"]
    assert fetched_bid["details"] == card_data["details"]

    # Clean up (optional, depends on test DB strategy)
    # deleted = bidcard_repo.delete_bid_card(created_bid["id"])
    # assert deleted is True

# Add more tests for other repository functions (list_for_owner, list_for_project, update, delete, search)
# Consider testing edge cases like invalid category, missing fields, RLS (requires test users/roles)

def test_invalid_category_raises_error():
    """Tests that creating a card with an invalid category raises ValueError."""
    with pytest.raises(ValueError, match="category must be one of"): 
        bidcard_repo.create_bid_card(
            homeowner_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            category="invalid_category", # This should fail
            job_type="Some job",
        )

# Note: Testing RLS might require setting up test users with specific roles
# or running tests with the service key which bypasses RLS.
