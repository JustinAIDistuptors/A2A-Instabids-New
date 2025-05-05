from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Dict, Any, Annotated
# from instabids.data import bidcard_repo # Not used directly in search endpoint
from instabids.tools.gemini_text_embed import embed
from supabase import create_client, Client
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bidcards", tags=["bidcards"])

# Dependency to get Supabase client
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_ANON_KEY not set in environment.")
        raise HTTPException(status_code=500, detail="Server configuration error.")
    try:
        return create_client(url, key)
    except Exception as e:
        logger.exception(f"Failed to create Supabase client: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to database.")

SupabaseDep = Annotated[Client, Depends(get_supabase_client)]

@router.get("/search")
def search_bidcards(db: SupabaseDep, q: str = Query(..., min_length=3, description="Search query for job type or category"), limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return")) -> List[Dict[str, Any]]:
    """Search for bid cards using hybrid text and vector similarity.

    Performs a search based on:
    1. Text matching (ILIKE) on 'job_type' or 'category'.
    2. Vector similarity (cosine distance) on 'job_embed'.

    Results are ordered by similarity score (higher is better).
    """
    logger.info(f"Received bidcard search request: q='{q}', limit={limit}")

    # 1. Generate embedding for the query
    logger.debug(f"Generating embedding for query: '{q}'")
    query_vector = embed(q)
    if query_vector is None:
        logger.error(f"Failed to generate embedding for query: '{q}'")
        raise HTTPException(status_code=500, detail="Failed to process search query.")
    logger.debug(f"Generated query vector (first 10 dims): {query_vector[:10]}...")

    # 2. Construct SQL query for hybrid search using pgvector's <=> operator
    # <=> calculates cosine distance (0=identical, 1=orthogonal, 2=opposite)
    # We want cosine similarity, so we use (1 - distance).
    # Note: Ensure the 'exec_sql' RPC function exists in your Supabase setup or use direct query.
    # Parameterizing properly is crucial to prevent SQL injection if not using RPC.
    # This example uses string formatting for simplicity but RPC or ORM parameterization is safer.
    # Ensure 'q' is sanitized if not using parameterized queries.

    # Basic sanitization for ILIKE (replace single quotes)
    sanitized_q = q.replace("'", "''")

    # WARNING: Direct string formatting is risky. Use parameterized queries or RPCs in production.
    sql = f"""
    SELECT
        *,
        (1 - (job_embed <=> '{query_vector}')) AS score
    FROM
        bid_cards
    WHERE
        job_type ILIKE '%%{sanitized_q}%%'
        OR category ILIKE '%%{sanitized_q}%%'
        OR (1 - (job_embed <=> '{query_vector}')) > 0.7 -- Example threshold for vector search relevance
    ORDER BY
        score DESC
    LIMIT {limit};
    """
    logger.debug(f"Executing hybrid search SQL:
{sql}
")

    try:
        # Assuming 'exec_sql' RPC function exists for executing raw SQL
        # If not, you'd use the PostgREST client's standard query methods if possible,
        # or a direct DB connection pool (like asyncpg) for raw SQL.
        # res = db.rpc("exec_sql", {"sql": sql}).execute() 

        # Alternative: Use PostgREST select with filters and order (might be complex for hybrid)
        # This requires more complex filter construction.
        # For now, sticking with the RPC approach as implied by the original snippet.

        # Using PostgREST's rpc call (ensure 'exec_sql' function is defined in Supabase SQL Editor)
        res = db.rpc('vector_search', {
            'query_embedding': query_vector,
            'match_threshold': 0.7, # Cosine similarity threshold
            'query_text': f'%%{sanitized_q}%%',
            'match_count': limit
        }).execute()

        if res.data:
            logger.info(f"Found {len(res.data)} bidcards matching query '{q}'.")
            return res.data
        else:
            # Check for errors in Supabase response
            if hasattr(res, 'error') and res.error:
                logger.error(f"Supabase RPC error during search: {res.error}")
                raise HTTPException(status_code=500, detail=f"Database search error: {res.error['message']}")
            logger.info(f"No bidcards found matching query '{q}'.")
            return [] # Return empty list if no results
    except HTTPException as e:
        raise e # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Unexpected error during bidcard search for query '{q}': {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during search.")
