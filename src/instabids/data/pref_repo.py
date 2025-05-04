"""
Repository for managing user preferences in the database.
"""
import os
import json
from typing import Any, Dict, Optional, List, Union
from supabase import create_client  # type: ignore

_sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

def upsert_pref(user_id: str, key: str, value: Any, confidence: float = 0.5) -> Dict[str, Any]:
    """
    Create or update a user preference.
    
    Args:
        user_id: The user's ID
        key: Preference key
        value: Preference value (will be JSON serialized)
        confidence: Confidence score for this preference (0.0-1.0)
        
    Returns:
        The inserted/updated preference data
    """
    result = _sb.table("user_preferences").upsert({
        "user_id": user_id,
        "preference_key": key,
        "preference_value": json.dumps(value),
        "confidence": confidence,
        "updated_at": "now()"  # Use server timestamp
    }).execute()
    
    return result.data[0] if result.data else {}

def get_pref(user_id: str, key: str) -> Any:
    """
    Retrieve a specific user preference.
    
    Args:
        user_id: The user's ID
        key: Preference key to retrieve
        
    Returns:
        The preference value (deserialized from JSON) or None if not found
    """
    result = _sb.table("user_preferences").select("preference_value") \
             .eq("user_id", user_id).eq("preference_key", key).execute()
    
    if not result.data:
        return None
        
    # Parse JSON value
    try:
        return json.loads(result.data[0]["preference_value"])
    except (json.JSONDecodeError, KeyError):
        return None

def get_prefs(user_id: str) -> dict:
    """
    Retrieve all preferences for a user as a dictionary.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with preference_key as keys and preference_value as values
    """
    rows = _sb.table("user_preferences").select("*").eq("user_id", user_id).execute().data
    return {r["preference_key"]: json.loads(r["preference_value"]) for r in rows}

def get_all_prefs(user_id: str) -> Dict[str, Any]:
    """
    Retrieve all preferences for a user with additional metadata.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary of all user preferences with metadata
    """
    result = _sb.table("user_preferences").select("*") \
             .eq("user_id", user_id).execute()
    
    prefs = {}
    for item in result.data:
        try:
            prefs[item["preference_key"]] = {
                "value": json.loads(item["preference_value"]),
                "confidence": item.get("confidence", 0.5),
                "updated_at": item.get("updated_at")
            }
        except (json.JSONDecodeError, KeyError):
            continue
            
    return prefs

def delete_pref(user_id: str, key: str) -> bool:
    """
    Delete a user preference.
    
    Args:
        user_id: The user's ID
        key: Preference key to delete
        
    Returns:
        True if successful, False otherwise
    """
    result = _sb.table("user_preferences").delete() \
             .eq("user_id", user_id).eq("preference_key", key).execute()
    
    return len(result.data) > 0

def save_feedback(user_id: str, rating: int, comments: str = "") -> Dict[str, Any]:
    """
    Save user feedback.
    
    Args:
        user_id: The user's ID
        rating: Rating from 1-5
        comments: Optional feedback comments
        
    Returns:
        The inserted feedback data
    
    Raises:
        ValueError: If rating is not between 1 and 5
    """
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
        
    result = _sb.table("user_feedback").insert({
        "user_id": user_id,
        "rating": rating,
        "comments": comments
    }).execute()
    
    return result.data[0] if result.data else {}