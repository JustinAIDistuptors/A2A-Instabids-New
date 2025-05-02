"""Supabase helpers."""
from __future__ import annotations
from typing import List
import os
from supabase import create_client  # type: ignore

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_ANON_KEY"]
_sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_project(row: dict) -> str:
    res = _sb.table("projects").insert(row).execute()
    return res.data[0]["id"]

def save_project_photos(pid: str, photos: List[dict]) -> None:
    for p in photos:
        _sb.table("project_photos").insert(
            {"project_id": pid, **p}
        ).execute()