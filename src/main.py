"""Main entry point for the InstaBids application with memory integration."""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from google.adk.runtime import agent_service
from supabase import create_client, Client

from src.agents.homeowner_agent import HomeownerAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def create_supabase_client() -> Client:
    """Create and return a Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE")
    
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE environment variables must be set"
        )
    
    return create_client(url, key)


async def main():
    """Main entry point for the application."""
    try:
        # Create Supabase client
        db = create_supabase_client()
        logger.info("Supabase client created successfully")
        
        # Create agent
        agent = HomeownerAgent(db)
        logger.info("HomeownerAgent created successfully")
        
        # Start the agent service
        await agent_service.run(agent)
    except Exception as e:
        logger.error(f"Error starting application: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())