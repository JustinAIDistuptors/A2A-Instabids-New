"""Repository for managing project photos and vision metadata in the database."""
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from supabase import create_client
import os

logger = logging.getLogger(__name__)

# Lazy-loaded Supabase client
_sb = None

def get_supabase_client():
    """Get or create a Supabase client instance."""
    global _sb
    if _sb is None:
        _sb = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE"]
        )
    return _sb

def save_photo_meta(project_id: str, storage_path: str, meta: Optional[Dict[str, Any]]) -> bool:
    """Save photo metadata to the database.
    
    Args:
        project_id: Project ID
        storage_path: Storage path of the image
        meta: Vision metadata (labels, embedding, confidence)
        
    Returns:
        True if successfully saved, False otherwise
        
    Raises:
        Exception: If there's an error communicating with the database
    """
    if not meta or not isinstance(meta, dict):
        logger.warning(f"No valid metadata to save for {storage_path}")
        return False
        
    logger.info(f"Saving vision metadata for project {project_id}, image {storage_path}")
    
    # Extract fields from metadata, defaulting to None if missing
    labels = meta.get("labels")
    embedding = meta.get("embedding")
    confidence = meta.get("confidence")
    
    # Update the project_photos table
    sb = get_supabase_client()
    result = sb.table("project_photos").update({
        "vision_labels": labels,
        "embed": embedding,
        "confidence": confidence
    }).eq("project_id", project_id).eq("storage_path", storage_path).execute()
    
    return bool(result.data)

def get_photo_meta(project_id: str, storage_path: str) -> Optional[Dict[str, Any]]:
    """Get photo metadata from the database.
    
    Args:
        project_id: Project ID
        storage_path: Storage path of the image
        
    Returns:
        Metadata dictionary or None if not found
    """
    sb = get_supabase_client()
    result = sb.table("project_photos").select(
        "vision_labels", "embed", "confidence"
    ).eq("project_id", project_id).eq("storage_path", storage_path).execute()
    
    if not result.data:
        return None
        
    return {
        "labels": result.data[0].get("vision_labels"),
        "embedding": result.data[0].get("embed"),
        "confidence": result.data[0].get("confidence")
    }

async def find_similar_photos(project_id: str, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    """Find photos with similar embeddings using vector search.
    
    Args:
        project_id: Project ID
        embedding: Vector embedding to match
        limit: Maximum number of results to return
        
    Returns:
        List of photos with similarity scores
    """
    sb = get_supabase_client()
    
    # Using SQL directly since we don't have the custom function yet
    query = f"""
    SELECT storage_path, embed <=> '{json.dumps(embedding)}' as distance
    FROM project_photos
    WHERE project_id = '{project_id}' AND embed IS NOT NULL
    ORDER BY distance ASC
    LIMIT {limit}
    """
    
    try:
        result = sb.sql(query).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error finding similar photos: {e}")
        return []