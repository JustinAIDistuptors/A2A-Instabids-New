from fastapi.testclient import TestClient
from instabids.app import app

client = TestClient(app)

def test_get_missing():
    r = client.get("/projects/foo/bid-card")
    assert r.status_code == 404