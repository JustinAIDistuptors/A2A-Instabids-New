from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_create_project():
    r = client.post("/projects", json={"description": "replace fence"})
    assert r.status_code == 201
    assert "project_id" in r.json()