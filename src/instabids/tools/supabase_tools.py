"""
Supabase tools for accessing data in the database.
"""
from typing import List, Dict, Any, Optional
from .supabase import supabase_client as _sb

# List of tools exposed for agent use
supabase_tools = []

async def get_user_info(user_id: str) -> Dict[str, Any]:
    """
    Get user information from the database.
    
    Args:
        user_id: User ID to get information for
        
    Returns:
        User information
    """
    result = _sb.from_("users").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else {}

async def get_project_info(project_id: str) -> Dict[str, Any]:
    """
    Get project information from the database.
    
    Args:
        project_id: Project ID to get information for
        
    Returns:
        Project information
    """
    result = _sb.from_("projects").select("*").eq("id", project_id).execute()
    return result.data[0] if result.data else {}

async def get_message_history(project_id: str) -> List[Dict[str, Any]]:
    """
    Get message history for a project.
    
    Args:
        project_id: Project ID to get messages for
        
    Returns:
        List of messages
    """
    result = _sb.from_("messages").select("*").eq("project_id", project_id).order("created_at").execute()
    return result.data

async def save_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a message to the database.
    
    Args:
        message: Message to save
        
    Returns:
        Saved message
    """
    result = _sb.from_("messages").insert(message).execute()
    return result.data[0] if result.data else {}
