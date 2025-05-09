#!/usr/bin/env python
"""
Memory Manager for InstaBids.

Provides a simplified interface to the integrated memory system,
handling database connections and memory instance management.
"""

import logging
import os
from typing import Dict, Optional, Any, List

from supabase import create_client, Client

from .integrated_memory import IntegratedMemory

# Set up logging
logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages memory instances for different users and agents.
    
    This class provides a simplified interface to the integrated memory system,
    handling database connections and memory instance management.
    """
    
    def __init__(self):
        """Initialize the memory manager."""
        self._db: Optional[Client] = None
        self._memory_instances: Dict[str, IntegratedMemory] = {}
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the memory manager with database connection.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Get database credentials from environment variables
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                logger.error("Missing Supabase credentials. Ensure SUPABASE_URL and SUPABASE_KEY are set.")
                return False
            
            # Initialize Supabase client
            self._db = create_client(supabase_url, supabase_key)
            self._initialized = True
            logger.info("Memory manager initialized successfully.")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize memory manager: {e}", exc_info=True)
            return False
    
    async def get_user_memory(self, user_id: str) -> Optional[IntegratedMemory]:
        """Get or create a memory instance for a user.
        
        Args:
            user_id: User ID to get memory for
            
        Returns:
            IntegratedMemory instance or None if initialization failed
        """
        if not self._initialized:
            if not self.initialize():
                logger.error("Cannot get user memory - memory manager not initialized.")
                return None
        
        # Check if memory instance already exists
        if user_id in self._memory_instances:
            return self._memory_instances[user_id]
        
        try:
            # Create new memory instance
            memory = IntegratedMemory(self._db, user_id)
            # Load memory from database
            await memory.load()
            # Store in cache
            self._memory_instances[user_id] = memory
            return memory
        
        except Exception as e:
            logger.error(f"Failed to get memory for user {user_id}: {e}", exc_info=True)
            return None
    
    async def save_all(self) -> bool:
        """Save all memory instances.
        
        Returns:
            bool: True if all memory instances were saved successfully, False otherwise
        """
        if not self._memory_instances:
            logger.info("No memory instances to save.")
            return True
        
        success = True
        for user_id, memory in self._memory_instances.items():
            try:
                if not await memory.save():
                    logger.error(f"Failed to save memory for user {user_id}")
                    success = False
            except Exception as e:
                logger.error(f"Exception saving memory for user {user_id}: {e}", exc_info=True)
                success = False
        
        return success
    
    def get_db(self) -> Optional[Client]:
        """Get the Supabase client instance.
        
        Returns:
            Supabase client instance or None if not initialized
        """
        if not self._initialized:
            if not self.initialize():
                return None
        
        return self._db
    
    async def clear_memory(self, user_id: str) -> bool:
        """Clear memory for a user.
        
        Args:
            user_id: User ID to clear memory for
            
        Returns:
            bool: True if memory was cleared successfully, False otherwise
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            # Remove memory from database
            await self._db.table("user_memories").delete().eq("user_id", user_id).execute()
            
            # Remove from cache
            if user_id in self._memory_instances:
                del self._memory_instances[user_id]
            
            logger.info(f"Memory cleared for user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to clear memory for user {user_id}: {e}", exc_info=True)
            return False
    
    async def get_user_preferences(self, user_id: str, min_confidence: float = 0.5) -> Dict[str, Any]:
        """Get user preferences with minimum confidence level.
        
        Args:
            user_id: User ID to get preferences for
            min_confidence: Minimum confidence level (0-1)
            
        Returns:
            Dictionary of preferences
        """
        if not self._initialized:
            if not self.initialize():
                return {}
        
        try:
            # Query database directly for preferences
            result = await self._db.table("user_preferences") \
                .select("*") \
                .eq("user_id", user_id) \
                .gte("confidence", min_confidence) \
                .execute()
            
            # Format as dictionary
            preferences = {}
            if result.data:
                for pref in result.data:
                    preferences[pref["preference_key"]] = pref["preference_value"]
            
            return preferences
        
        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {e}", exc_info=True)
            return {}
    
    async def get_user_interactions(
        self, 
        user_id: str, 
        interaction_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user interactions.
        
        Args:
            user_id: User ID to get interactions for
            interaction_type: Optional interaction type to filter by
            limit: Maximum number of interactions to return
            
        Returns:
            List of interactions
        """
        if not self._initialized:
            if not self.initialize():
                return []
        
        try:
            # Build query
            query = self._db.table("user_memory_interactions") \
                .select("*") \
                .eq("user_id", user_id)
            
            if interaction_type:
                query = query.eq("interaction_type", interaction_type)
            
            # Execute query
            result = await query \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            return result.data if result.data else []
        
        except Exception as e:
            logger.error(f"Failed to get interactions for user {user_id}: {e}", exc_info=True)
            return []
    
    async def get_agent_messages(
        self,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages exchanged between agents.
        
        Args:
            task_id: Optional task ID to filter by
            session_id: Optional session ID to filter by
            agent_id: Optional agent ID to filter by (as sender or recipient)
            limit: Maximum number of messages to return
            
        Returns:
            List of agent messages
        """
        if not self._initialized:
            if not self.initialize():
                return []
        
        try:
            # Build query
            query = self._db.table("agent_messages").select("*")
            
            if task_id:
                query = query.eq("task_id", task_id)
                
            if session_id:
                query = query.eq("session_id", session_id)
                
            if agent_id:
                # Query for messages where agent is either sender or recipient
                query = query.or_(f"sender_agent_id.eq.{agent_id},recipient_agent_id.eq.{agent_id}")
            
            # Execute query with order and limit
            result = await query.order("created_at", desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error retrieving agent messages: {e}", exc_info=True)
            return []

# Create a singleton instance
memory_manager = MemoryManager()
