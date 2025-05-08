"""
Project repository for accessing and modifying project data.
"""
from typing import Dict, Any, List, Optional, Generator, ContextManager
from contextlib import contextmanager
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Mock database for testing
_projects = {}
_photos = {}
_current_transaction = None

@contextmanager
def _Tx() -> Generator[None, None, None]:
    """
    Context manager for transactions.
    
    Yields:
        None
    """
    global _current_transaction
    
    old_tx = _current_transaction
    _current_transaction = {}
    
    try:
        yield
        _current_transaction = old_tx  # Commit by restoring old tx
    except Exception as e:
        _current_transaction = old_tx  # Rollback by restoring old tx
        raise e

def save_project(project_data: Dict[str, Any]) -> str:
    """
    Save a project to the database.
    
    Args:
        project_data: Project data to save
        
    Returns:
        Project ID
    """
    project_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    project = {
        "id": project_id,
        "created_at": now,
        "updated_at": now,
        **project_data
    }
    
    _projects[project_id] = project
    logger.info(f"Saved project: {project_id}")
    
    return project_id

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a project by ID.
    
    Args:
        project_id: Project ID to retrieve
        
    Returns:
        Project data or None if not found
    """
    project = _projects.get(project_id)
    if not project:
        logger.warning(f"Project not found: {project_id}")
        return None
        
    # Include photo URLs if any exist
    if project_id in _photos:
        project["photos"] = _photos[project_id]
        
    return project

def list_projects(user_id: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List projects, optionally filtered by user.
    
    Args:
        user_id: Optional user ID to filter by
        limit: Maximum number of projects to return
        offset: Offset for pagination
        
    Returns:
        List of projects
    """
    projects = list(_projects.values())
    
    # Filter by user if specified
    if user_id:
        projects = [p for p in projects if p.get("homeowner_id") == user_id]
        
    # Sort by created_at (newest first)
    projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    
    # Apply pagination
    paged = projects[offset:offset + limit]
    
    return paged

def update_project(project_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a project.
    
    Args:
        project_id: Project ID to update
        updates: Fields to update
        
    Returns:
        True if successful, False otherwise
    """
    project = _projects.get(project_id)
    if not project:
        logger.warning(f"Project not found for update: {project_id}")
        return False
        
    # Update the project
    project.update(updates)
    project["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"Updated project: {project_id}")
    return True

def delete_project(project_id: str) -> bool:
    """
    Delete a project.
    
    Args:
        project_id: Project ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    if project_id not in _projects:
        logger.warning(f"Project not found for deletion: {project_id}")
        return False
        
    # Delete the project
    del _projects[project_id]
    
    # Delete associated photos
    if project_id in _photos:
        del _photos[project_id]
        
    logger.info(f"Deleted project: {project_id}")
    return True

def save_project_photos(project_id: str, photos: List[Dict[str, Any]]) -> List[str]:
    """
    Save photos associated with a project.
    
    Args:
        project_id: Project ID to associate photos with
        photos: List of photo data
        
    Returns:
        List of photo IDs
    """
    if project_id not in _projects:
        logger.warning(f"Project not found for adding photos: {project_id}")
        return []
        
    # Initialize photos list for this project if it doesn't exist
    if project_id not in _photos:
        _photos[project_id] = []
        
    photo_ids = []
    for photo in photos:
        photo_id = str(uuid.uuid4())
        photo_data = {
            "id": photo_id,
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            **photo
        }
        _photos[project_id].append(photo_data)
        photo_ids.append(photo_id)
        
    logger.info(f"Saved {len(photo_ids)} photos for project: {project_id}")
    return photo_ids