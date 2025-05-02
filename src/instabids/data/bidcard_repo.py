from __future__ import annotations
import os
from supabase import create_client  # type: ignore

_sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def upsert(row: dict) -> None:
    _sb.table("bid_cards").upsert(row).execute()

def fetch(project_id: str) -> dict | None:
    res = _sb.table("bid_cards").select("*").eq("project_id", project_id).execute()
    return res.data[0] if res.data else None