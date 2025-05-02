"""Supabase data‑access layer with retry + Tx management."""
from __future__ import annotations
from typing import List, Dict, Any, Optional, TypeVar, Callable
import os
import time
import logging
from supabase import create_client  # type: ignore

# Fix: Import Client directly from supabase instead of supabase.lib.client
from supabase import Client  # type: ignore

# Set up logging
logger = logging.getLogger(__name__)

# Environment variables
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_ANON_KEY"]
_sb: Client = create_client(URL, KEY)
_MAX_RETRY = 3

T = TypeVar('T')  # Generic type for retry function

class _Tx:
    """Context‑manager for pseudo‑transactions (Supabase RPC rollback pattern)."""
    
    def __enter__(self):
        """Begin transaction."""
        _sb.postgrest.rpc("begin")
        return self
        
    def __exit__(self, exc, *_):
        """Commit or rollback transaction based on exception."""
        _sb.postgrest.rpc("rollback" if exc else "commit")
        return False  # re‑raise if exc

def _retry(fn: Callable[..., T], *a: Any, **kw: Any) -> T:
    """
    Retry a function with exponential backoff.
    
    Args:
        fn: Function to retry
        *a: Positional arguments to pass to the function
        **kw: Keyword arguments to pass to the function
        
    Returns:
        The result of the function
        
    Raises:
        Exception: If the function fails after max retries
    """
    for i in range(_MAX_RETRY):
        try:
            return fn(*a, **kw)
        except Exception as e:
            # Fix: Log the exception instead of assigning to unused variable
            logger.error(f"Attempt {i+1}/{_MAX_RETRY} failed: {e}")
            sleep_time = 2 ** i  # Exponential backoff
            logger.warning(f"Retry {i+1}/{_MAX_RETRY} after {sleep_time}s: {e}")
            time.sleep(sleep_time)
    
    # This should never be reached due to the raise in the exception handler
    raise RuntimeError("Unexpected error in retry logic")

# ---------------- public helpers ----------------

def save_project(row: Dict[str, Any]) -> str:
    """
    Save a project to the database.
    
    Args:
        row: Project data to save
        
    Returns:
        str: ID of the created project
    """
    res = _retry(_sb.table("projects").insert, row).execute()
    return res.data[0]["id"]

def save_project_photos(pid: str, photos: List[Dict[str, Any]]) -> None:
    """
    Save project photos to the database.
    
    Args:
        pid: Project ID
        photos: List of photo metadata dictionaries
    """
    for p in photos:
        _retry(_sb.table("project_photos").insert, {"project_id": pid, **p}).execute()

def get_project(pid: str) -> Dict[str, Any]:
    """
    Get project by ID.
    
    Args:
        pid: Project ID
        
    Returns:
        Dict: Project data
    """
    res = _retry(_sb.table("projects").select("*", count="exact").eq("id", pid)).execute()
    return res.data[0]

def list_project_photos(pid: str) -> List[Dict[str, Any]]:
    """
    List photos for a project.
    
    Args:
        pid: Project ID
        
    Returns:
        List[Dict]: List of photo data
    """
    return _retry(_sb.table("project_photos").select("*").eq("project_id", pid)).execute().data