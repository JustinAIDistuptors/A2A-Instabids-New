"""Supabase data‑access layer with retry + Tx management."""
from __future__ import annotations
from typing import List, Dict, Any
import os, time
from supabase import Client  # type: ignore

URL  = os.environ["SUPABASE_URL"]
KEY  = os.environ["SUPABASE_ANON_KEY"]
_sb: Client = Client(URL, KEY)
_MAX_RETRY = 3

class _Tx:
    """Context‑manager for pseudo‑transactions (Supabase RPC rollback pattern)."""
    def __enter__(self):
        _sb.postgrest.rpc("begin")
        return self
    def __exit__(self, exc, *_):
        _sb.postgrest.rpc("rollback" if exc else "commit")
        return False  # re‑raise if exc

def _retry(fn, *a, **kw):
    for i in range(_MAX_RETRY):
        try:
            return fn(*a, **kw)
        except Exception:
            if i == _MAX_RETRY-1:
                raise
            time.sleep(0.5 * (i+1))

# ---------------- public helpers ----------------

def save_project(row: Dict[str,Any]) -> str:
    res = _retry(_sb.table("projects").insert, row).execute()
    return res.data[0]["id"]

def save_project_photos(pid: str, photos: List[Dict[str,Any]]) -> None:
    for p in photos:
        _retry(_sb.table("project_photos").insert, {"project_id": pid, **p}).execute()

def get_project(pid: str) -> Dict[str,Any]:
    res = _retry(_sb.table("projects").select("*", count="exact").eq("id", pid)).execute()
    return res.data[0]

def list_project_photos(pid: str):
    return _retry(_sb.table("project_photos").select("*").eq("project_id", pid)).execute().data