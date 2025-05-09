from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from supabase import create_client  # type: ignore
from instabids.tools.gemini_text_embed import embed # ADDED IMPORT
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Supabase client
_sb_url = os.getenv("SUPABASE_URL")
_sb_key = os.getenv("SUPABASE_ANON_KEY")

if not _sb_url or not _sb_key:
    logger.warning("SUPABASE_URL or SUPABASE_ANON_KEY environment variables not set. Bidcard repo operations might fail.")
    _sb = None
else:
    try:
        _sb = create_client(_sb_url, _sb_key)
        logger.info("Supabase client initialized successfully for bidcard_repo.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        _sb = None

def create_bid_card(homeowner_id: str, project_id: str, category: str, job_type: str, **kwargs) -> dict | None:
    """Creates a new bid card record, including a job type embedding.

    Args:
        homeowner_id: The ID of the homeowner.
        project_id: The ID of the project.
        category: The project category.
        job_type: The specific job type.
        **kwargs: Additional fields to include in the bid card.

    Returns:
        The created bid card data as a dict, or None if creation fails.
    """
    if not _sb:
        logger.error("Cannot create bid card: Supabase client not initialized.")
        return None

    # Generate embedding from category and job_type
    embedding_text = f"{category} {job_type}"
    logger.info(f"Generating embedding for text: '{embedding_text}'")
    job_embed = embed(embedding_text)

    if job_embed is None:
        logger.warning(f"Could not generate embedding for project {project_id}. Proceeding without embedding.")
        # Embedding failed, store None or handle as needed

    bid_card_data = {
        "homeowner_id": homeowner_id,
        "project_id": project_id,
        "category": category,
        "job_type": job_type,
        "job_embed": job_embed,  # Include the generated embedding (or None if failed)
        **kwargs  # Include any other provided data
    }

    try:
        # Use insert for creating a new record
        logger.debug(f"Inserting bid card data for project {project_id}")
        response = _sb.table("bid_cards").insert(bid_card_data).execute()

        # Check response for success/errors (Supabase API v2+)
        if response.data:
            logger.info(f"Successfully created bid card for project {project_id} with embedding.")
            return response.data[0]
        else:
             # Log Supabase specific errors if available in response
            error_info = getattr(response, 'error', None)
            logger.error(f"Failed to create bid card for project {project_id}. Response status: {getattr(response, 'status_code', 'N/A')}, Error: {error_info}")
            return None
    except Exception as e:
        logger.exception(f"Exception occurred while creating bid card for project {project_id}: {e}")
        return None

def upsert(row: dict) -> None:
    """Upserts a bid card record."""
    if not _sb:
        logger.error("Cannot upsert bid card: Supabase client not initialized.")
        return
    project_id = row.get('project_id', 'unknown')
    try:
        logger.debug(f"Upserting bid card for project {project_id}")
        _sb.table("bid_cards").upsert(row).execute()
        logger.info(f"Successfully upserted bid card for project {project_id}")
    except Exception as e:
        logger.exception(f"Exception occurred while upserting bid card for project {project_id}: {e}")

def list_for_project(project_id: str) -> List[Dict[str, Any]]:
    """List bid cards for a specific project."""
    if not _sb:
        logger.error("Cannot list bid cards: Supabase client not initialized.")
        return []
    try:
        res = _sb.table("bid_cards").select("*").eq("project_id", project_id).execute()
        return res.data
    except Exception as e:
        logger.exception(f"Error listing bid cards for project {project_id}: {e}")
        return []

def list_for_owner(owner_id: str) -> List[Dict[str, Any]]:
    """List bid cards for a specific homeowner."""
    # This assumes there's a relationship between bid_cards and projects tables
    # with owner_id in the projects table
    if not _sb:
        logger.error("Cannot list bid cards: Supabase client not initialized.")
        return []
    try:
        res = _sb.table("bid_cards").select("*").eq("owner_id", owner_id).execute()
        return res.data
    except Exception as e:
        logger.exception(f"Error listing bid cards for owner {owner_id}: {e}")
        return []

def fetch(project_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a bid card by project ID."""
    if not _sb:
        logger.error("Cannot fetch bid card: Supabase client not initialized.")
        return None
    try:
        logger.debug(f"Fetching bid card for project {project_id}")
        res = _sb.table("bid_cards").select("*").eq("project_id", project_id).limit(1).execute()
        if res.data:
            logger.debug(f"Found bid card for project {project_id}")
            return res.data[0]
        else:
            logger.debug(f"No bid card found for project {project_id}")
            return None
    except Exception as e:
        logger.exception(f"Exception occurred while fetching bid card for project {project_id}: {e}")
        return None

# Add alias functions for compatibility
def get_bid_cards_by_project(project_id: str) -> List[Dict[str, Any]]:
    """Get bid cards for a project."""
    return list_for_project(project_id)

def get_bid_cards_by_homeowner(owner_id: str) -> List[Dict[str, Any]]:
    """Get bid cards for a homeowner."""
    return list_for_owner(owner_id)