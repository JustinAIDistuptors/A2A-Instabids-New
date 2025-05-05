# src/instabids/data/photo_repo.py
"""Persist photo meta + embedding."""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional

# Assuming create_client is correctly located here
# If it's elsewhere (e.g., a shared data module), adjust the import
from instabids.data.supabase_client import create_client

logger = logging.getLogger(__name__)

# Initialize Supabase client globally or within functions as needed
# Global initialization can be efficient but might have implications in some environments
_sb = None
try:
    _sb = create_client()
    if not _sb:
        logger.error("Failed to initialize Supabase client in photo_repo.")
except Exception as e:
    logger.error(f"Error initializing Supabase client in photo_repo: {e}", exc_info=True)
    _sb = None


def save_photo_meta(project_id: str, storage_path: str, meta: Optional[Dict[str, Any]]) -> None:
    """
    Saves vision metadata associated with a project photo to the database.

    Args:
        project_id: The ID of the project the photo belongs to.
        storage_path: The path where the photo is stored (e.g., in Supabase storage).
        meta: A dictionary containing vision metadata ('labels', 'embedding', 'confidence').
              Can be None if analysis failed.
    """
    if not _sb:
        logger.error("Supabase client not available. Cannot save photo metadata.")
        return
    if not meta:
        logger.warning(f"Received None for metadata for photo {storage_path}. Skipping DB save.")
        return
    if not project_id:
        logger.error("project_id is required to save photo metadata.")
        return
    if not storage_path:
         logger.error("storage_path is required to save photo metadata.")
         return


    # Prepare row data, handling potential missing keys in meta gracefully
    row = {
        "project_id": project_id,
        "storage_path": storage_path,
        # Use .get() with defaults for robustness
        "vision_labels": meta.get("labels", []),
        "embed": meta.get("embedding"), # Assumes 'embedding' key exists if meta is not None
        "confidence": meta.get("confidence"), # Assumes 'confidence' key exists
        # 'photo_type' was in the sprint snippet - assuming it's relevant
        "photo_type": meta.get("photo_type", "current"), # Default to 'current' if not provided
    }

    # Validate embedding format if necessary (e.g., check length)
    embedding = row.get("embed")
    if embedding is not None:
        if not isinstance(embedding, list):
            logger.error(f"Invalid embedding format for {storage_path}: Expected list, got {type(embedding)}. Skipping save.")
            return
        # Optional: Check embedding dimensions if required by DB schema
        # expected_dims = 256
        # if len(embedding) != expected_dims:
        #     logger.error(f"Invalid embedding dimension for {storage_path}: Expected {expected_dims}, got {len(embedding)}. Skipping save.")
        #     return

    logger.debug(f"Attempting to save photo metadata for project {project_id}, path {storage_path}")
    try:
        # Insert data into the 'project_photos' table
        response = _sb.table("project_photos").insert(row).execute()
        # Optional: Check response for errors
        # Supabase Python V2 uses postgrest exceptions for errors primarily
        # Check if data was returned as an indicator of success
        if response.data:
             logger.info(f"Successfully saved photo metadata for {storage_path}")
        else:
            # This path might be hit if RLS prevents insert but doesn't raise an exception
            logger.warning(f"Supabase insert for photo meta {storage_path} did not return data or failed silently (check RLS/policy?).")

    except Exception as e:
        # Catch PostgrestError or other specific exceptions if needed
        logger.error(f"Exception saving photo meta for project {project_id}, path {storage_path}: {e}", exc_info=True)
