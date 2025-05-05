"""
Bid-Card Repository (CRUD + search)
Works with Supabase row-level-secured table created in migration above.
"""

from __future__ import annotations
import os, datetime
from typing import Any, Dict, List, Optional

# Prefer project helper; fall back to supabase-py directly.
try:
    from instabids.data.supabase_client import create_client as _create
    _sb = _create()
except ImportError:
    from supabase import create_client  # type: ignore
    _sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )

_VALID_CATS = {
    "repair", "renovation", "installation",
    "maintenance", "construction", "other",
}

# ────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────
def _check_cat(cat: str) -> None:
    if cat not in _VALID_CATS:
        raise ValueError(f"category must be one of {_VALID_CATS}")

# ────────────────────────────────────────────────
# CRUD
# ────────────────────────────────────────────────
def create_bid_card(**kw: Any) -> Dict[str, Any]:
    _check_cat(kw["category"])
    kw.setdefault("details", {})
    resp = _sb.table("bid_cards").insert(kw).execute()
    if resp.data:
        return resp.data[0]
    raise RuntimeError(resp.error)

def get_bid_card(card_id: str) -> Optional[Dict[str, Any]]:
    resp = _sb.table("bid_cards").select("*").eq("id", card_id).single().execute()
    return resp.data

def list_for_owner(owner_id: str) -> List[Dict[str, Any]]:
    resp = _sb.table("bid_cards").select("*") \
             .eq("homeowner_id", owner_id) \
             .order("created_at", desc=True).execute()
    return resp.data

def list_for_project(project_id: str) -> List[Dict[str, Any]]:
    resp = _sb.table("bid_cards").select("*") \
             .eq("project_id", project_id) \
             .order("created_at", desc=True).execute()
    return resp.data

def update_bid_card(card_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    for k in ("id", "homeowner_id", "project_id", "created_at"):
        updates.pop(k, None)
    updates["updated_at"] = datetime.datetime.utcnow().isoformat()
    resp = _sb.table("bid_cards").update(updates).eq("id", card_id).execute()
    if resp.data:
        return resp.data[0]
    raise RuntimeError(f"not found or no rights for {card_id}")

def delete_bid_card(card_id: str) -> bool:
    resp = _sb.table("bid_cards").delete().eq("id", card_id).execute()
    return bool(resp.data)

def search(
    query: str = "",
    categories: Optional[list[str]] = None,
    min_budget: float | None = None,
    max_budget: float | None = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    q = _sb.table("bid_cards").select("*")
    if categories:
        q = q.in_("category", categories)
    if min_budget is not None:
        q = q.gte("budget_min", min_budget)
    if max_budget is not None:
        q = q.lte("budget_max", max_budget)
    if query:
        q = q.or_(f"job_type.ilike.%{query}%,location.ilike.%{query}%")
    return q.order("created_at", desc=True).limit(limit).execute().data