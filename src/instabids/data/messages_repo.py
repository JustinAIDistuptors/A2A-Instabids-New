import os
from supabase import create_client  # type: ignore
from typing import Optional, List, Dict, Any

_sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])

def insert_message(project_id: str, role: str, content: str) -> Dict[str, Any]:
    """
    Insert a new message into the messages table.
    
    Args:
        project_id: The UUID of the project this message belongs to
        role: Either 'homeowner' or 'agent'
        content: The message content
        
    Returns:
        The inserted message data
    """
    result = _sb.table("messages").insert(
        {"project_id": project_id, "role": role, "content": content}
    ).execute()
    
    return result.data[0] if result.data else {}

def get_project_messages(project_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all messages for a specific project, ordered by creation time.
    
    Args:
        project_id: The UUID of the project to get messages for
        
    Returns:
        List of message objects
    """
    result = _sb.table("messages") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("created_at") \
        .execute()
        
    return result.data if result.data else []