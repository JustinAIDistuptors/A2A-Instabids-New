# tests/test_bidcard_embedding.py
import pytest
from unittest.mock import patch, MagicMock
import os
import sys # Need sys for path manipulation and patch.dict

# Add src directory to path before importing instabids modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Mock the Supabase client *before* importing the repo
mock_supabase_client = MagicMock()
mock_execute = MagicMock()
mock_data = MagicMock()
mock_data.data = [{
    "homeowner_id": "u1",
    "project_id": "p1",
    "category": "repair",
    "job_type": "roof leak",
    "job_embed": [0.0] * 384, # Simulate returned embedding
    # Add other fields returned by insert if necessary
}]
# Correctly chain the mock assignments
mock_insert_result = MagicMock()
mock_insert_result.execute = mock_execute
mock_execute.return_value = mock_data # execute() returns the data wrapper
mock_supabase_client.table.return_value.insert.return_value = mock_insert_result # insert() returns an object with execute()

# Mock the embed function used by the repo
mock_embed_func = MagicMock(return_value=[0.1] * 384) # Use a distinct value for clarity

# Patch the client creation and embed function within bidcard_repo's scope
modules_to_patch = {
    # Patch where create_client is *called* if it's directly in bidcard_repo,
    # or patch it globally if imported there. Assuming global import for simplicity.
    'supabase.create_client': MagicMock(return_value=mock_supabase_client),
    'instabids.tools.gemini_text_embed.embed': mock_embed_func
}

# Use patch.dict to apply mocks *before* importing bidcard_repo
# Ensure the target dictionary 'sys.modules' is correctly specified
with patch.dict('sys.modules', modules_to_patch):
    # Import the repo module *after* patches are applied
    from instabids.data import bidcard_repo

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set necessary environment variables for Supabase client init mock."""
    monkeypatch.setenv("SUPABASE_URL", "http://mock.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "mock_key")
    # No need to set GEMINI_API_KEY here as embed is mocked

# Test function
# No need for outer patch decorator if already patched via patch.dict
def test_embed_added_during_creation():
    """Test that job_embed is added when creating a bid card."""
    homeowner_id = "u1"
    project_id = "p1"
    category = "repair"
    job_type = "roof leak"

    # Reset mocks specific to this test run if necessary
    mock_embed_func.reset_mock()
    mock_supabase_client.table.return_value.insert.reset_mock()
    mock_execute.reset_mock()

    # Call the function that uses the embed tool
    # Ensure create_bid_card itself isn't async if not defined as such
    created_row = bidcard_repo.create_bid_card(
        homeowner_id=homeowner_id,
        project_id=project_id,
        category=category,
        job_type=job_type
    )

    # 1. Assert the embed function was called correctly
    mock_embed_func.assert_called_once_with(f"{category} {job_type}")

    # 2. Assert the DB insert function was called
    mock_supabase_client.table.return_value.insert.assert_called_once()

    # 3. Assert the data passed to the DB insert contained the embedding from the mock embed
    insert_call_args = mock_supabase_client.table.return_value.insert.call_args
    assert insert_call_args is not None, "Supabase insert was not called with arguments"
    inserted_data = insert_call_args[0][0] # First positional argument of insert() is the data dict/list
    assert isinstance(inserted_data, dict), "Data passed to insert should be a dictionary"
    assert "job_embed" in inserted_data
    assert inserted_data["job_embed"] == [0.1] * 384 # Assert against value returned by embed mock in *this* test run

    # 4. Assert the returned row (from mocked DB response) is correct
    # Note: The mock_data dictates what's in 'created_row'
    assert created_row is not None, "create_bid_card returned None"
    assert isinstance(created_row, dict), "create_bid_card should return a dictionary"
    assert "job_embed" in created_row, "'job_embed' key missing in returned data"
    # Check against the value returned by the *mocked* DB execute call
    assert created_row["job_embed"] == [0.0] * 384 # From mock_data.data[0]

