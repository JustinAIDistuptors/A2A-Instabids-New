"""Unit tests for contractor_profiles data repository."""
import pytest
from instabids.data import contractor_repo as repo
from unittest.mock import MagicMock, patch

# Mock data constants
MOCK_USER_ID = "test-user-uuid-123"
MOCK_CREATE_PAYLOAD = {
    "user_id": MOCK_USER_ID,
    "display_name": "Test Contractor",
    "trade": "Plumbing",
    "location": "Testville",
}
MOCK_DB_ROW = {
    "id": "profile-uuid-456",
    "user_id": MOCK_USER_ID,
    "display_name": "Test Contractor",
    "bio": None,
    "trade": "Plumbing",
    "location": "Testville",
    "license_number": None,
    "insurance_cert": None,
    "google_reviews": [],
    "internal_rating": 0.0,
    "created_at": "2024-01-01T10:00:00+00:00",
    "updated_at": "2024-01-01T10:00:00+00:00",
}
MOCK_UPDATE_PAYLOAD = {"bio": "Experienced plumber"}
MOCK_UPDATED_DB_ROW = {**MOCK_DB_ROW, "bio": "Experienced plumber", "updated_at": "2024-01-01T11:00:00+00:00"}

# Patch the Supabase client instance within the contractor_repo module
@patch('instabids.data.contractor_repo._sb')
def test_crud_roundtrip(mock_supabase_client):
    """Tests the create, get, update, and delete operations via mocked Supabase calls."""

    # --- Mock Supabase API responses ---
    mock_insert_resp = MagicMock()
    mock_insert_resp.data = [MOCK_DB_ROW] # Supabase often returns lists
    mock_insert_resp.error = None

    mock_get_found_resp = MagicMock()
    mock_get_found_resp.data = MOCK_DB_ROW # maybe_single returns dict or None
    mock_get_found_resp.error = None
    
    mock_get_not_found_resp = MagicMock()
    mock_get_not_found_resp.data = None
    mock_get_not_found_resp.error = None

    mock_update_resp = MagicMock()
    mock_update_resp.data = [MOCK_UPDATED_DB_ROW]
    mock_update_resp.error = None

    mock_delete_resp = MagicMock()
    # Delete might return the deleted items or just success marker
    # Assuming it returns empty list on success for this mock
    mock_delete_resp.data = [] 
    mock_delete_resp.error = None
    
    # --- Configure mock call chains ---

    # CREATE
    (mock_supabase_client.table.return_value
     .insert.return_value
     .execute.return_value) = mock_insert_resp

    created = repo.create_profile(MOCK_CREATE_PAYLOAD)
    assert created == MOCK_DB_ROW # Check if the returned data matches mock
    mock_supabase_client.table.assert_called_with(repo._TABLE)
    mock_supabase_client.table().insert.assert_called_with(MOCK_CREATE_PAYLOAD)
    mock_supabase_client.table().insert().execute.assert_called_once()

    # GET (Found)
    # Reset mocks for the next operation chain
    mock_supabase_client.reset_mock() 
    (mock_supabase_client.table.return_value
     .select.return_value
     .eq.return_value
     .maybe_single.return_value
     .execute.return_value) = mock_get_found_resp

    fetched = repo.get_profile(MOCK_USER_ID)
    assert fetched == MOCK_DB_ROW
    mock_supabase_client.table.assert_called_with(repo._TABLE)
    mock_supabase_client.table().select.assert_called_with("*")
    mock_supabase_client.table().select().eq.assert_called_with("user_id", MOCK_USER_ID)
    mock_supabase_client.table().select().eq().maybe_single.assert_called_once()
    mock_supabase_client.table().select().eq().maybe_single().execute.assert_called_once()

    # UPDATE
    mock_supabase_client.reset_mock()
    (mock_supabase_client.table.return_value
     .update.return_value
     .eq.return_value
     .execute.return_value) = mock_update_resp # Changed from single() as update might affect multiple, though eq('user_id') should be unique

    updated = repo.update_profile(MOCK_USER_ID, MOCK_UPDATE_PAYLOAD)
    assert updated == MOCK_UPDATED_DB_ROW
    mock_supabase_client.table.assert_called_with(repo._TABLE)
    mock_supabase_client.table().update.assert_called_with(MOCK_UPDATE_PAYLOAD)
    mock_supabase_client.table().update().eq.assert_called_with("user_id", MOCK_USER_ID)
    mock_supabase_client.table().update().eq().execute.assert_called_once()
    
    # DELETE
    mock_supabase_client.reset_mock()
    (mock_supabase_client.table.return_value
     .delete.return_value
     .eq.return_value
     .execute.return_value) = mock_delete_resp
     
    repo.delete_profile(MOCK_USER_ID)
    mock_supabase_client.table.assert_called_with(repo._TABLE)
    mock_supabase_client.table().delete.assert_called_once()
    mock_supabase_client.table().delete().eq.assert_called_with("user_id", MOCK_USER_ID)
    mock_supabase_client.table().delete().eq().execute.assert_called_once()

    # GET (Not Found after delete)
    mock_supabase_client.reset_mock()
    (mock_supabase_client.table.return_value
     .select.return_value
     .eq.return_value
     .maybe_single.return_value
     .execute.return_value) = mock_get_not_found_resp

    fetched_after_delete = repo.get_profile(MOCK_USER_ID)
    assert fetched_after_delete is None
    mock_supabase_client.table().select().eq().maybe_single().execute.assert_called_once()

# --- Additional Test Ideas ---
# - Test `get_profile` when user_id does not exist (covered by roundtrip's last step)
# - Test `update_profile` when user_id does not exist (should raise ValueError as implemented)
# - Test `create_profile` with missing required fields (depends on DB constraints / repo logic)
# - Test error handling in `_check` by mocking response.error
