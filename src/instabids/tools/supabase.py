"""
Supabase client configuration.
"""
import os
import logging
from contextlib import contextmanager
from supabase import create_client, Client

# Set up logging
logger = logging.getLogger(__name__)

# Get Supabase credentials from environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL or SUPABASE_KEY not set in environment variables")

# Initialize Supabase client
try:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    supabase_client = None

# Function to get admin client with service role when needed
def get_admin_client() -> Client:
    """
    Get Supabase client with service role for admin operations.
    
    Returns:
        Supabase client with service role
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
        logger.error("Cannot create admin client: missing credentials")
        raise ValueError("Supabase service role credentials not configured")
        
    try:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase admin client: {str(e)}")
        raise