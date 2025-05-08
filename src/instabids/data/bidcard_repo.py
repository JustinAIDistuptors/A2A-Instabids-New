"""
Bid-Card Repository (CRUD + search)
Works with Supabase row-level-secured table created in migration above.
"""

from __future__ import annotations
import os, datetime, uuid
from typing import Any, Dict, List, Optional, Union

# Prefer project helper; fall back to supabase-py directly.
try:
    from instabids.data.supabase_client import create_client as _create
    _sb = _create()
except ImportError:
    from supabase import create_client  # type: ignore
    try:
        _sb = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        )
    except KeyError:
        # For local development and testing without env vars
        # This will result in a TypedDict for testing
        _sb = {"function": lambda: None}

_VALID_CATS = {
    "repair", "renovation", "installation",
    "maintenance", "construction", "other",
}

# ───────────────────────────────────────────────────────────────────────
# helpers
# ───────────────────────────────────────────────────────────────────────
def _check_cat(cat: str) -> None:
    if cat not in _VALID_CATS:
        raise ValueError(f"category must be one of {_VALID_CATS}")

def _parse_budget(budget_range: str) -> tuple[float, float]:
    """Parse budget range string ('1000-2000') into budget_min and budget_max floats."""
    try:
        parts = budget_range.replace('$', '').replace(',', '').split('-')
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
        else:
            # Handle single values or invalid formats
            val = float(parts[0])
            return val, val * 1.5  # Default max is 1.5x min if only one value
    except (ValueError, IndexError):
        # Default budget range if parsing fails
        return 0.0, 0.0

# ───────────────────────────────────────────────────────────────────────
# CRUD
# ───────────────────────────────────────────────────────────────────────
def create_bid_card(**kw: Any) -> Dict[str, Any]:
    """Create a new bid card in the database.
    
    Args:
        project_id: UUID of the associated project
        homeowner_id: UUID of the homeowner
        category: Project category (must be one of valid categories)
        job_type: Specific job type/description
        budget_range: String representation of budget range (e.g., "1000-2000")
        timeline: Timeline for project completion
        group_bidding: Whether to allow group bidding
        location: Project location
        scope_json: JSON object with detailed scope
        photo_meta: JSON object with photo metadata
        
    Returns:
        The created bid card record
    
    Raises:
        ValueError: If category is invalid
        RuntimeError: If database operation fails
    """
    # Validate category
    _check_cat(kw["category"])
    
    # Generate UUID if not provided
    if "id" not in kw:
        kw["id"] = str(uuid.uuid4())
    
    # Parse budget range to min/max if provided
    if "budget_range" in kw and not ("budget_min" in kw and "budget_max" in kw):
        kw["budget_min"], kw["budget_max"] = _parse_budget(kw["budget_range"])
    
    # Initialize empty JSONBs if not provided
    kw.setdefault("scope_json", {})
    kw.setdefault("photo_meta", {})
    
    # Execute the insert
    resp = _sb.table("bid_cards").insert(kw).execute()
    if resp.data:
        return resp.data[0]
    raise RuntimeError(resp.error)

def get_bid_card(card_id: str) -> Optional[Dict[str, Any]]:
    """Get a bid card by ID.
    
    Args:
        card_id: UUID of the bid card
        
    Returns:
        The bid card record or None if not found
    """
    resp = _sb.table("bid_cards").select("*").eq("id", card_id).single().execute()
    return resp.data

def list_for_owner(owner_id: str) -> List[Dict[str, Any]]:
    """List all bid cards for a homeowner.
    
    Args:
        owner_id: UUID of the homeowner
        
    Returns:
        List of bid card records
    """
    resp = _sb.table("bid_cards").select("*") \
            .eq("homeowner_id", owner_id) \
            .order("created_at", desc=True).execute()
    return resp.data

def list_for_project(project_id: str) -> List[Dict[str, Any]]:
    """List all bid cards for a project.
    
    Args:
        project_id: UUID of the project
        
    Returns:
        List of bid card records
    """
    resp = _sb.table("bid_cards").select("*") \
            .eq("project_id", project_id) \
            .order("created_at", desc=True).execute()
    return resp.data

def update_bid_card(card_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a bid card.
    
    Args:
        card_id: UUID of the bid card
        updates: Dictionary of fields to update
        
    Returns:
        The updated bid card record
        
    Raises:
        RuntimeError: If card not found or update fails
    """
    # Remove fields that shouldn't be updated
    for k in ("id", "homeowner_id", "project_id", "created_at"):
        updates.pop(k, None)
    
    # Parse budget range to min/max if provided
    if "budget_range" in updates and not ("budget_min" in updates and "budget_max" in updates):
        updates["budget_min"], updates["budget_max"] = _parse_budget(updates["budget_range"])
    
    # Set updated_at timestamp
    updates["updated_at"] = datetime.datetime.utcnow().isoformat()
    
    # Execute the update
    resp = _sb.table("bid_cards").update(updates).eq("id", card_id).execute()
    if resp.data:
        return resp.data[0]
    raise RuntimeError(f"not found or no rights for {card_id}")

def delete_bid_card(card_id: str) -> bool:
    """Delete a bid card.
    
    Args:
        card_id: UUID of the bid card
        
    Returns:
        True if deleted, False otherwise
    """
    resp = _sb.table("bid_cards").delete().eq("id", card_id).execute()
    return bool(resp.data)

def search(
    query: str = "",
    categories: Optional[list[str]] = None,
    min_budget: float | None = None,
    max_budget: float | None = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Search for bid cards matching criteria.
    
    Args:
        query: Text search query
        categories: List of categories to filter by
        min_budget: Minimum budget
        max_budget: Maximum budget
        limit: Maximum number of results
        
    Returns:
        List of matching bid card records
    """
    q = _sb.table("bid_cards").select("*")
    
    # Apply category filter
    if categories:
        q = q.in_("category", categories)
    
    # Apply budget filters
    if min_budget is not None:
        q = q.gte("budget_min", min_budget)
    if max_budget is not None:
        q = q.lte("budget_max", max_budget)
    
    # Apply text search
    if query:
        q = q.or_(f"job_type.ilike.%{query}%,location.ilike.%{query}%")
    
    # Execute query
    return q.order("created_at", desc=True).limit(limit).execute().data
