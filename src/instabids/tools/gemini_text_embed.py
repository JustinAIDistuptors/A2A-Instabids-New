"""Gemini text-embedding-004 wrapper (384-dim)."""
from __future__ import annotations
import os
import logging
from google.generativeai import configure, embed_content
from google.api_core import exceptions as google_exceptions

# Configure logging
logger = logging.getLogger(__name__)

_API_KEY = os.getenv("GEMINI_API_KEY")
if not _API_KEY:
    logger.warning("GEMINI_API_KEY environment variable not set. Text embedding will not function.")
    # Allow module to load but functions will fail if called without key
else:
    try:
        configure(api_key=_API_KEY)
        logger.info("Gemini API configured successfully for text embedding.")
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        _API_KEY = None # Prevent usage if configuration fails

def embed(text: str) -> list[float] | None:
    """Generates a 384-dimension embedding for the given text.

    Args:
        text: The input text string.

    Returns:
        A list of 384 floats representing the embedding, or None if an error occurs.
    """
    if not _API_KEY:
        logger.error("Cannot generate embedding: GEMINI_API_KEY not configured.")
        return None
    if not text:
        logger.warning("Attempted to embed empty string. Returning None.")
        return None

    try:
        # Using text-embedding-004 model (check if correct model name)
        resp = embed_content(
            model="models/text-embedding-004", # Verify this model name
            content=text,
            task_type="RETRIEVAL_DOCUMENT" # Or CLUSTERING, SEMANTIC_SIMILARITY, etc.
            # Consider "RETRIEVAL_QUERY" if embedding search terms
        )
        embedding = resp.get("embedding")
        if not embedding or len(embedding) != 384:
             logger.error(f"Invalid embedding received from API for text: '{text[:50]}...'. Received: {embedding}")
             return None
        return embedding
    except google_exceptions.GoogleAPIError as e:
        logger.error(f"Google API error during text embedding: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during text embedding for '{text[:50]}...': {e}")
        return None
