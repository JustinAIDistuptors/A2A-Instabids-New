# tools/search_bidcards.py
import argparse
import json
import os
import sys
import asyncio

# Add src directory to path to allow importing instabids
# This assumes the script is run from the project root or the tools directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

# Attempt to import the necessary functions
try:
    # NOTE: Direct function call is problematic due to FastAPI dependency injection (db: SupabaseDep).
    # This script requires modification or specific environment setup to work correctly.
    from instabids.api.bidcards import search_bidcards, get_supabase_client
    from instabids.tools.gemini_text_embed import embed # Needed by search_bidcards
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Ensure the script is run from the project root or 'tools' directory,")
    print("and that necessary dependencies are installed.")
    sys.exit(1)

async def main():
    ap = argparse.ArgumentParser(description="CLI smoke test for bidcard search function (attempts direct call).")
    ap.add_argument("query", help="The search query term.")
    ap.add_argument("--limit", type=int, default=10, help="Max number of results.")
    args = ap.parse_args()

    print(f"Attempting search for query: '{args.query}' with limit {args.limit}")
    print("NOTE: This script attempts a direct function call and depends on environment variables:")
    print("  SUPABASE_URL, SUPABASE_ANON_KEY, GEMINI_API_KEY")
    print("Consider modifying this to make an HTTP request to the running API server for a true endpoint test.")

    try:
        # Attempt to get a Supabase client instance manually
        db_client = get_supabase_client()
        # Call the function directly, manually passing the client
        # This bypasses FastAPI's DI
        results = search_bidcards(db=db_client, q=args.query, limit=args.limit)
        print("\n--- Results ---")
        print(json.dumps(results, indent=2))
        print("---------------")
    except Exception as e:
        print(f"\nERROR: Failed to execute search function directly: {e}")
        print("Please ensure required environment variables are set and accessible.")
        print("Also ensure the 'vector_search' RPC function exists in your Supabase DB.")

if __name__ == "__main__":
    # The search_bidcards function is async if it uses async libraries like httpx potentially
    # Although the current implementation doesn't strictly require async, running it in an event loop
    # is safer if any underlying calls (like Supabase client) might be async in the future.
    asyncio.run(main())
