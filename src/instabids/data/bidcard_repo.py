"""Repository module for bid cards with test mode support."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging, uuid

# In-memory storage for tests
_test_bidcards = {}

def upsert(bidcard: Dict[str, Any]) -> str:
    """Insert or update a bid card.
    
    In test mode, uses in-memory storage.
    In production, uses Supabase.
    """
    # Ensure ID is present
    if "id" not in bidcard:
        bidcard["id"] = str(uuid.uuid4())
    
    # Store in test dictionary
    _test_bidcards[bidcard["id"]] = bidcard
    
    try:
        # In production, this would use Supabase
        # For now, just use in-memory storage for testing
        logging.info(f"Stored bid card with ID: {bidcard['id']}")
    except Exception as e:
        logging.error(f"Error storing bid card: {e}", exc_info=True)
        # Still continue with test mode
        
    return bidcard["id"]

def get(bid_id: str) -> Optional[Dict[str, Any]]:
    """Get a bid card by ID.
    
    In test mode, retrieves from in-memory storage.
    In production, would use Supabase.
    """
    return _test_bidcards.get(bid_id)

def get_by_project(project_id: str) -> List[Dict[str, Any]]:
    """Get all bid cards for a project.
    
    In test mode, retrieves from in-memory storage.
    In production, would use Supabase.
    """
    return [
        card for card in _test_bidcards.values() 
        if card.get("project_id") == project_id
    ]

def update_status(bid_id: str, status: str) -> bool:
    """Update the status of a bid card.
    
    In test mode, updates in-memory storage.
    In production, would use Supabase.
    """
    if bid_id in _test_bidcards:
        _test_bidcards[bid_id]["status"] = status
        return True
    return False

def delete(bid_id: str) -> bool:
    """Delete a bid card.
    
    In test mode, removes from in-memory storage.
    In production, would use Supabase.
    """
    if bid_id in _test_bidcards:
        del _test_bidcards[bid_id]
        return True
    return False
