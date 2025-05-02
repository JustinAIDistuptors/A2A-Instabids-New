"""Tests for API routes."""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_create_project() -> None:
    """Test the project creation endpoint.
    
    Verifies that:
    1. The endpoint returns a 201 status code
    2. The response contains a project_id
    """
    response = client.post("/projects", json={"description": "replace fence"})
    assert response.status_code == 201
    assert "project_id" in response.json()