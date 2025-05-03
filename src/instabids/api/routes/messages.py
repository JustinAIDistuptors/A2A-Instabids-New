"""
API routes for retrieving message history.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from instabids.data.messages_repo import get_project_messages

router = APIRouter(prefix="/projects")

@router.get("/{project_id}/messages")
def get_messages(project_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all messages for a specific project.
    
    Args:
        project_id: The UUID of the project
        
    Returns:
        List of message objects
        
    Raises:
        HTTPException: If no messages are found (404)
    """
    messages = get_project_messages(project_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this project")
    return messages