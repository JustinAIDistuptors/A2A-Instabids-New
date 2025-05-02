"""DB helpers for bid_cards table."""
from __future__ import annotations
import os
from supabase import create_client  # type: ignore

_sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])

def save_bid_card(row: dict) -> None:
    _sb.table("bid_cards").insert(row).execute()

def get_by_project(project_id: str) -> dict | None:
    res = _sb.table("bid_cards").select("*").eq("project_id", project_id).execute()
    return res.data[0] if res.data else None