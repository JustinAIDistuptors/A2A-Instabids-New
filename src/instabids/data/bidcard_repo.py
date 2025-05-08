from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from supabase import create_client  # type: ignore

_sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def upsert(row: dict) -> None:
    _sb.table("bid_cards").upsert(row).execute()

def list_for_project(project_id: str) -> List[Dict[str, Any]]:
    """List bid cards for a specific project."""
    res = _sb.table("bid_cards").select("*").eq("project_id", project_id).execute()
    return res.data

def list_for_owner(owner_id: str) -> List[Dict[str, Any]]:
    """List bid cards for a specific homeowner."""
    # This assumes there's a relationship between bid_cards and projects tables
    # with owner_id in the projects table
    res = _sb.table("bid_cards").select("*").eq("owner_id", owner_id).execute()
    return res.data

def fetch(project_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a bid card by project ID."""
    res = _sb.table("bid_cards").select("*").eq("project_id", project_id).execute()
    return res.data[0] if res.data else None

# Add alias functions for compatibility
def get_bid_cards_by_project(project_id: str) -> List[Dict[str, Any]]:
    """Get bid cards for a project."""
    return list_for_project(project_id)

def get_bid_cards_by_homeowner(owner_id: str) -> List[Dict[str, Any]]:
    """Get bid cards for a homeowner."""
    return list_for_owner(owner_id)
