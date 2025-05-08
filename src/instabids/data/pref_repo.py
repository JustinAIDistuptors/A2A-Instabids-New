"""
Preference repository for accessing and modifying user preferences.
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Mock database for testing
_preferences = {}

def get_pref(user_id: str, key: str) -> Optional[Any]:
    """
    Get a user preference.
    
    Args:
        user_id: User ID
        key: Preference key
        
    Returns:
        Preference value or None if not found
    """
    user_prefs = _preferences.get(user_id, {})
    return user_prefs.get(key)

def upsert_pref(user_id: str, key: str, value: Any) -> bool:
    """
    Set a user preference.
    
    Args:
        user_id: User ID
        key: Preference key
        value: Preference value
        
    Returns:
        True if successful
    """
    if user_id not in _preferences:
        _preferences[user_id] = {}
        
    _preferences[user_id][key] = value
    logger.info(f"Set preference {key} for user {user_id}")
    
    return True

def get_all_prefs(user_id: str) -> Dict[str, Any]:
    """
    Get all preferences for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary of preferences
    """
    return _preferences.get(user_id, {}).copy()

def delete_pref(user_id: str, key: str) -> bool:
    """
    Delete a user preference.
    
    Args:
        user_id: User ID
        key: Preference key
        
    Returns:
        True if successful, False if not found
    """
    if user_id not in _preferences or key not in _preferences[user_id]:
        logger.warning(f"Preference {key} not found for user {user_id}")
        return False
        
    del _preferences[user_id][key]
    logger.info(f"Deleted preference {key} for user {user_id}")
    
    return True