# instabids/data/project_repo.py

from supabase import create_client, Client
import os

# Initialize Supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

def save_project(project_data: dict):
    """
    Saves a project to the Supabase 'projects' table.
    Returns the API response.
    """
    # Ensure required fields are present if needed, or handle potential errors
    # The .execute() returns an APIResponse object
    response = supabase.table("projects").insert(project_data).execute()
    # You might want to check response.data or handle errors
    if not response.data:
      # Log error or raise exception based on response.error
      print(f"Error saving project: {response.error}")
      # Decide what to return on failure, maybe None or raise?
      # Returning the raw response for now as in the original code
      return response 
    # Return the first element from the data list as per Supabase convention 
    # Also, the original test expected the ID back, not the full response.
    # Let's return the ID from the inserted data if successful.
    # Assuming the ID is the primary key and returned in the data.
    # Adjust 'id' if your primary key column name is different.
    return response.data[0].get('id')

def get_project(project_id: str):
    """
    Retrieves a project from the Supabase 'projects' table by ID.
    Returns the API response.
    """
    response = supabase.table("projects").select("*").eq("id", project_id).execute()
    # Similar error checking as above
    if not response.data and response.error:
        print(f"Error getting project: {response.error}")
        # Decide what to return on failure or if not found
        # Returning the raw response for now
        return response
    # If data exists, return the first (and likely only) record
    return response.data[0] if response.data else None

# Expose the functions through the 'repo' object
# This dictionary allows calling repo['save_project'](data)
repo = {
    "save_project": save_project,
    "get_project": get_project
}
