import os
from supabase import create_async_client, AsyncClient

async def get_supabase_client() -> AsyncClient:
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")

    if not url:
        raise ValueError(
            "SUPABASE_URL environment variable not found or not accessible. "
            "Please ensure it is correctly set (e.g., system-wide or in .env file if used)."
        )
    if not key:
        raise ValueError(
            "SUPABASE_KEY environment variable not found or not accessible. "
            "Please ensure it is correctly set (e.g., system-wide or in .env file if used)."
        )
    
    return await create_async_client(url, key)
