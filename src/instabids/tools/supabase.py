from pathlib import Path
from supabase import create_client, Client

# Load the spec that sits next to this file
_SPEC_PATH = Path(__file__).with_name("openapi_supabase.yaml")

# Create Supabase client instance
def create_supabase_client():
    """Create and return a configured Supabase client instance."""
    return create_client(
        supabase_url=__import__("os").environ["SUPABASE_URL"],
        supabase_key=__import__("os").environ["SUPABASE_ANON_KEY"]
    )

# Export client factory function
supabase_client = create_supabase_client
