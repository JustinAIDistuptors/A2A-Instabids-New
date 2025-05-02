import os, uuid, pytest
from instabids.data import project_repo as repo

pytest.skip("Needs SUPABASE_URL", allow_module_level=True) if "SUPABASE_URL" not in os.environ else None

def test_project_roundtrip():
    pid = repo.save_project({
        "id": str(uuid.uuid4()),
        "homeowner_id": "u1", "title": "test", "description": "t", "category": "other"})
    row = repo.get_project(pid)
    assert row["id"] == pid