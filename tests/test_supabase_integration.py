import os, uuid, pytest
# from instabids.data import project_repo as repo  <- Incorrect import
from instabids.data.project_repo import repo # <- Correct import

pytest.skip("Needs SUPABASE_URL", allow_module_level=True) if "SUPABASE_URL" not in os.environ else None

def test_project_roundtrip():
    # Call the save_project function via the imported repo dictionary
    project_data = {
        "id": str(uuid.uuid4()),
        "homeowner_id": "u1", # Assuming this user exists or FK is handled
        "title": "test integration", 
        "description": "testing repo roundtrip", 
        "category": "other",
        # Add other necessary fields based on your 'projects' table schema
    }
    # Use the dictionary access method
    pid = repo['save_project'](project_data)
    
    # Ensure pid is returned correctly (was modified to return ID)
    assert pid is not None, "save_project did not return a project ID"
    
    # Use the dictionary access method
    row = repo['get_project'](pid)
    
    assert row is not None, f"get_project did not find project with ID {pid}"
    assert row["id"] == pid, f"Returned project ID {row.get('id')} does not match expected {pid}"