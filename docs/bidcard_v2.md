# BidCard V2 - Embeddings and Search

This document outlines the enhancements made to the BidCard functionality, specifically focusing on the integration of job type embeddings and a hybrid search endpoint.

## 1. Job Type Embeddings

To enable semantic understanding and similarity searches for bid cards, we now generate and store vector embeddings for job descriptions.

### Embedding Generation

-   **Model:** Google Gemini API (`text-embedding-004` model, generating 384-dimensional vectors).
-   **Tool:** A dedicated wrapper `src/instabids/tools/gemini_text_embed.py` handles interactions with the Gemini API.
    -   It includes logging for monitoring.
    -   It requires the `GEMINI_API_KEY` environment variable.
    -   It handles potential API errors gracefully.
-   **Process:**
    -   When a new bid card is created via `src/instabids/data/bidcard_repo.py::create_bid_card`, the `category` and `job_type` fields are concatenated into a single string (e.g., "repair roof leak").
    -   This combined string is passed to the `gemini_text_embed.embed()` function.
    -   The resulting 384-dimensional vector is stored in the `job_embed` column of the `bid_cards` table.

### Database Changes

-   **Extension:** The `pgvector` extension is enabled in the Supabase database (migration `supabase/migrations/20240527_add_bidcard_embedding.sql`).
-   **Column:** A new column `job_embed` of type `vector(384)` was added to the `bid_cards` table.
-   **Index:** An IVFFLAT index was created on the `job_embed` column to optimize Approximate Nearest Neighbor (ANN) searches using cosine distance (`vector_cosine_ops`).

## 2. Hybrid Search Endpoint

A new API endpoint allows searching for bid cards using a combination of traditional text matching and vector similarity.

-   **Endpoint:** `GET /bidcards/search`
-   **Implementation:** `src/instabids/api/bidcards.py`
-   **Parameters:**
    -   `q` (query string, required, min length 3): The search term.
    -   `limit` (int, optional, default 20, max 100): Maximum number of results.
-   **Logic:**
    1.  The search query `q` is embedded using the `gemini_text_embed.embed()` function to get a `query_vector`.
    2.  A Supabase RPC function `vector_search` is called (see below).
    3.  This function performs a hybrid search:
        -   Text Search: Matches `q` against `job_type` and `category` using `ILIKE`.
        -   Vector Search: Finds bid cards whose `job_embed` vector is similar to the `query_vector` (cosine similarity >= `match_threshold`).
    4.  Results matching either condition are combined.
    5.  Results are ordered by similarity `score` (cosine similarity, higher is better), descending.
    6.  The top `limit` results are returned.

### Required Supabase Function (`vector_search`)

The search endpoint relies on a PostgreSQL function defined in Supabase. Create this function using the Supabase SQL Editor:

```sql
-- Supabase SQL function for hybrid search
CREATE OR REPLACE FUNCTION vector_search (
  query_embedding vector(384),
  match_threshold float,
  query_text text,       -- Should contain ILIKE wildcards (e.g., '%term%')
  match_count int
) RETURNS TABLE (
    -- List ALL columns from bid_cards table you want returned
    id bigint,
    project_id uuid,
    homeowner_id text,
    created_at timestamptz,
    updated_at timestamptz,
    category text,
    job_type text,
    details jsonb,
    status text,
    job_embed vector(384),
    -- Add other columns...
    score float -- Similarity score
) LANGUAGE sql STABLE AS $$
  SELECT
    bc.*, -- Select all columns from bid_cards aliased as bc
    (1 - (bc.job_embed <=> query_embedding)) AS score -- Cosine Similarity
  FROM
    bid_cards bc
  WHERE
    -- Match either text OR vector similarity threshold
    (bc.job_type ILIKE query_text OR bc.category ILIKE query_text)
    OR
    (1 - (bc.job_embed <=> query_embedding)) >= match_threshold
  ORDER BY
    score DESC
  LIMIT match_count;
$$;
```

**Note:** Ensure the `RETURNS TABLE (...)` part accurately lists all columns you need from the `bid_cards` table.

## 3. Environment Variables

The following environment variables are now required:

-   `GEMINI_API_KEY`: For generating embeddings.
-   `SUPABASE_URL`: For database connection.
-   `SUPABASE_ANON_KEY`: For database connection.

## 4. Testing

-   **Unit Test:** `tests/test_bidcard_embedding.py` verifies that the embedding is generated and included correctly when `create_bid_card` is called (using mocks).
-   **Integration Test:** `tests/test_search_endpoint.py` tests the `/bidcards/search` endpoint using `FastAPI.TestClient` and mocks for external services (Gemini embed, Supabase RPC).
-   **CLI Smoke Test:** `tools/search_bidcards.py` provides a basic command-line interface to *attempt* calling the search logic directly (requires environment variables and careful setup).

