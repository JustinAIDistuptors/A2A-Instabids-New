from supabase import create_client, Client
import os, json, asyncio
import logging
from typing import Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Import pgvector and asyncpg with error handling
try:
    from pgvector.asyncpg import register_vector
    import asyncpg
except ImportError as e:
    logger.error(f"Failed to import asyncpg or pgvector: {e}")
    logger.error("Please install required packages: pip install asyncpg pgvector")
    
    # Create dummy asyncpg module for type checking
    class DummyConnection:
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
        async def execute(self, *args, **kwargs):
            logger.error("Attempted to execute query with dummy connection")
            return None
            
    class DummyPool:
        async def acquire(self):
            logger.error("Attempted to acquire connection from dummy pool")
            return DummyConnection()
            
    if "asyncpg" not in globals():
        class asyncpg:
            Pool = DummyPool
            Connection = DummyConnection

_supabase: Optional[Client] = None
_pgpool: Optional[asyncpg.Pool] = None


def supabase() -> Client:
    global _supabase
    if _supabase is None:
        try:
            _supabase = create_client(
                os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]
            )
        except KeyError as e:
            logger.error(f"Missing environment variable: {e}")
            raise RuntimeError(f"Missing required environment variable: {e}")
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            raise
    return _supabase


async def pg() -> asyncpg.Connection:
    global _pgpool
    if _pgpool is None:
        try:
            _pgpool = await asyncpg.create_pool(os.environ["SUPABASE_DB_URL"])
            await register_vector(_pgpool)
        except KeyError as e:
            logger.error(f"Missing environment variable: {e}")
            raise RuntimeError(f"Missing required environment variable: {e}")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL pool: {e}")
            raise
    return await _pgpool.acquire()


# -- Project helpers --
async def create_project(task_id: str, payload: dict) -> None:
    await supabase().table("projects").insert(
        {"id": task_id, "payload": json.dumps(payload)}
    ).execute()


async def get_project_status(task_id: str) -> dict[str, Any] | None:
    res = (
        await supabase()
        .table("projects")
        .select("status,bids")
        .eq("id", task_id)
        .single()
        .execute()
    )
    return res.data if res.data else None