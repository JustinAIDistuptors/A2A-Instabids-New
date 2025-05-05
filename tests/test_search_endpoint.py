# tests/test_search_endpoint.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Add src directory to path before importing app
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

# --- Mocks --- >
# Mock the embedding function *before* it's imported by api.bidcards
MOCK_QUERY_VECTOR = [0.5] * 384
mock_embed_func = MagicMock(return_value=MOCK_QUERY_VECTOR)

# Mock the Supabase client and its RPC call
mock_supabase_client = MagicMock()
mock_rpc_execute = MagicMock()
mock_rpc_data = MagicMock()
# Define the expected structure of successful RPC result
mock_rpc_data.data = [
    {
        "id": 1,
        "project_id": "proj_abc",
        "homeowner_id": "ho_123",
        "category": "Landscaping",
        "job_type": "Install new garden bed",
        "job_embed": [0.45] * 384,
        "details": {},
        "status": "open",
        "score": 0.95 # Example score
    },
    {
        "id": 2,
        "project_id": "proj_def",
        "homeowner_id": "ho_456",
        "category": "Gardening",
        "job_type": "Plant flowers",
        "job_embed": [0.55] * 384,
        "details": {},
        "status": "open",
        "score": 0.85
    }
]
mock_rpc_execute.return_value = mock_rpc_data

# Set up the mock RPC call chain
# db.rpc('vector_search', {...}).execute()
mock_rpc_call = MagicMock()
mock_rpc_call.execute = mock_rpc_execute
mock_supabase_client.rpc.return_value = mock_rpc_call

# Patch modules *before* importing the FastAPI app
modules_to_patch = {
    # Patch the embed function where it's used (in api.bidcards)
    'instabids.api.bidcards.embed': mock_embed_func,
    # Patch the Supabase client factory where it's used (in api.bidcards)
    'instabids.api.bidcards.create_client': MagicMock(return_value=mock_supabase_client)
}

# Apply patches
with patch.dict('sys.modules', modules_to_patch):
    # Import the app *after* patches are applied
    from instabids.app import app

# --- Test Setup ---
@pytest.fixture(scope="module")
def test_client():
    """Provides a TestClient instance for the FastAPI app."""
    client = TestClient(app)
    yield client # Use yield for potential teardown

@pytest.fixture(autouse=True)
def reset_mocks_before_each_test():
    """Ensure mocks are reset before each test function runs."""
    mock_embed_func.reset_mock()
    mock_supabase_client.rpc.reset_mock()
    mock_rpc_call.reset_mock()
    mock_rpc_execute.reset_mock()
    # Re-assign return values if they were modified in tests
    mock_embed_func.return_value = MOCK_QUERY_VECTOR
    mock_rpc_execute.return_value = mock_rpc_data
    mock_supabase_client.rpc.return_value = mock_rpc_call

# --- Tests --- >
def test_search_bidcards_success(test_client):
    """Test successful search returning results."""
    search_query = "garden work"
    limit = 5

    response = test_client.get(f"/bidcards/search?q={search_query}&limit={limit}")

    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 2 # Based on mock_rpc_data
    assert results[0]["job_type"] == "Install new garden bed"
    assert results[1]["score"] == 0.85

    # Verify embed was called with the query
    mock_embed_func.assert_called_once_with(search_query)

    # Verify Supabase RPC was called with correct parameters
    mock_supabase_client.rpc.assert_called_once_with('vector_search', {
        'query_embedding': MOCK_QUERY_VECTOR,
        'match_threshold': 0.7, # Default threshold in endpoint
        'query_text': f'%%{search_query}%%', # Check text transformation
        'match_count': limit
    })
    mock_rpc_call.execute.assert_called_once()

def test_search_bidcards_no_results(test_client):
    """Test search returning no results."""
    search_query = "obscure query"
    limit = 10

    # Configure mock RPC to return empty data
    empty_rpc_data = MagicMock()
    empty_rpc_data.data = []
    mock_rpc_execute.return_value = empty_rpc_data

    response = test_client.get(f"/bidcards/search?q={search_query}&limit={limit}")

    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 0

    # Verify mocks were still called
    mock_embed_func.assert_called_once_with(search_query)
    mock_supabase_client.rpc.assert_called_once()
    mock_rpc_call.execute.assert_called_once()

def test_search_bidcards_embedding_failure(test_client):
    """Test handling of failure during query embedding."""
    search_query = "fail embed"

    # Configure embed mock to simulate failure
    mock_embed_func.return_value = None

    response = test_client.get(f"/bidcards/search?q={search_query}")

    assert response.status_code == 500
    assert "Failed to process search query" in response.text
    # Ensure RPC was not called if embedding failed
    mock_supabase_client.rpc.assert_not_called()

def test_search_bidcards_rpc_error(test_client):
    """Test handling of an error returned by the Supabase RPC call."""
    search_query = "rpc error"

    # Configure mock RPC to simulate an error response
    error_rpc_data = MagicMock()
    error_rpc_data.data = None # No data on error
    error_rpc_data.error = {'message': 'Database timeout', 'code': '54321'}
    mock_rpc_execute.return_value = error_rpc_data

    response = test_client.get(f"/bidcards/search?q={search_query}")

    assert response.status_code == 500
    assert "Database search error: Database timeout" in response.text

    # Verify mocks up to the RPC execute were called
    mock_embed_func.assert_called_once_with(search_query)
    mock_supabase_client.rpc.assert_called_once()
    mock_rpc_call.execute.assert_called_once()

def test_search_bidcards_query_too_short(test_client):
    """Test validation for minimum query length."""
    search_query = "hi"
    response = test_client.get(f"/bidcards/search?q={search_query}")

    assert response.status_code == 422 # Unprocessable Entity
    # Check for FastAPI validation error details
    assert "ensure this value has at least 3 characters" in response.text
    mock_embed_func.assert_not_called()
    mock_supabase_client.rpc.assert_not_called()

