"""CRUD helpers for contractor_profiles table."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

# Attempt to import the shared client, handle potential circularity or refactor later
try:
    from instabids.data.supabase_client import create_client
    _sb = create_client()
except ImportError:
    # Fallback or raise error if structure doesn't allow direct import yet
    # For now, assume it will work or needs refactoring
    print("Warning: Could not import create_client from instabids.data.supabase_client")
    # Provide a dummy/mock client for basic structure if needed, or raise
    # raise ImportError("Supabase client import failed") 
    _sb = None # Or some mock object

_TABLE = "contractor_profiles"

# ────────────────────────────────────────────────────────────────────────────
# Basic operations
# ────────────────────────────────────────────────────────────────────────────

def create_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    if not _sb: raise RuntimeError("Supabase client not initialized")
    resp = _sb.table(_TABLE).insert(row).execute()
    _check(resp)
    return resp.data[0]  # type: ignore[index]

def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    if not _sb: raise RuntimeError("Supabase client not initialized")
    # Assuming user_id is the UUID from the users table, linked in contractor_profiles
    resp = _sb.table(_TABLE).select("*").eq("user_id", user_id).maybe_single().execute() 
    # Use maybe_single() to gracefully handle 0 or 1 result without error
    # It returns None if no rows match, or the single row dict if one matches.
    _check(resp) # Check for actual errors even with maybe_single
    return resp.data

def update_profile(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    if not _sb: raise RuntimeError("Supabase client not initialized")
    # Ensure user_id is used for lookup, return the updated row
    resp = _sb.table(_TABLE).update(updates).eq("user_id", user_id).execute()
    # Check if update actually happened and return the updated data
    _check(resp)
    if not resp.data:
        # This case means the update matched 0 rows (user_id not found)
        # Depending on desired behavior, either return None or raise an error
        raise ValueError(f"Profile with user_id {user_id} not found for update.")
    return resp.data[0] # Return the first (and only) updated row

def delete_profile(user_id: str) -> None:
    if not _sb: raise RuntimeError("Supabase client not initialized")
    resp = _sb.table(_TABLE).delete().eq("user_id", user_id).execute()
    _check(resp) # Check for errors during delete
    # No return value needed

# ────────────────────────────────────────────────────────────────────────────
# Util
# ────────────────────────────────────────────────────────────────────────────

def _check(resp):
    # Check if the response object itself indicates an error
    # Supabase client library might structure errors differently depending on version
    # Adapting based on common patterns (e.g., PostgrestAPIResponse having an 'error' attribute)
    if hasattr(resp, 'error') and resp.error:
        # Log the error for debugging
        # import logging; logging.error(f"Supabase error: {resp.error}")
        # Raise a more specific exception if possible
        raise RuntimeError(f"Supabase API error: {resp.error}")
    # Add checks for HTTP status if available and relevant
    # if hasattr(resp, 'status_code') and not (200 <= resp.status_code < 300):
    #    raise RuntimeError(f"Supabase HTTP error {resp.status_code}: {resp.data}")
