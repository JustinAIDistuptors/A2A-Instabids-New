"""
Repository for managing user preferences in the database.
"""
import os
import json
from typing import Any, Dict, Optional, List, Union
from supabase import create_client  # type: ignore

_sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])

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
        "pref_key": key,
        "pref_value": json.dumps(value),
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
    result = _sb.table("user_preferences").select("pref_value") \
             .eq("user_id", user_id).eq("pref_key", key).execute()
    
    if not result.data:
        return None
        
    # Parse JSON value
    try:
        return json.loads(result.data[0]["pref_value"])
    except (json.JSONDecodeError, KeyError):
        return None

def get_all_prefs(user_id: str) -> Dict[str, Any]:
    """
    Retrieve all preferences for a user.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary of all user preferences
    """
    result = _sb.table("user_preferences").select("pref_key", "pref_value") \
             .eq("user_id", user_id).execute()
    
    prefs = {}
    for item in result.data:
        try:
            prefs[item["pref_key"]] = json.loads(item["pref_value"])
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
             .eq("user_id", user_id).eq("pref_key", key).execute()
    
    return len(result.data) > 0