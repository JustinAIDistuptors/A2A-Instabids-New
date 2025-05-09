"""Persistent memory implementation for InstaBids agents."""
import json
import logging
from typing import Any, Dict, Optional, List, Set

logger = logging.getLogger(__name__)

class PersistentMemory:
    """Persistent memory for storing and retrieving user preferences and context."""
    
    def __init__(self, db, user_id: str):
        """Initialize persistent memory.
        
        Args:
            db: Supabase client instance
            user_id: User ID for memory retrieval
        """
        self.db = db
        self.user_id = user_id
        self._memory_cache: Dict[str, Any] = {}
        self._is_loaded = False
        self._is_dirty = False
        
    async def load(self) -> bool:
        """Load memory from database.
        
        Returns:
            True if successfully loaded, False otherwise
        """
        logger.info(f"Loading memory for user {self.user_id}")
        try:
            result = self.db.table("user_memories").select("memory_data").eq("user_id", self.user_id).execute()
            if result.data and len(result.data) > 0:
                self._memory_cache = result.data[0].get("memory_data", {})
            self._is_loaded = True
            self._is_dirty = False
            logger.info(f"Successfully loaded memory for user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error loading memory for user {self.user_id}: {e}")
            return False
    
    async def save(self) -> bool:
        """Save memory to database.
        
        Returns:
            True if successfully saved, False otherwise
        """
        if not self._is_dirty:
            logger.debug(f"No changes to memory for user {self.user_id}, skipping save")
            return True
            
        logger.info(f"Saving memory for user {self.user_id}")
        try:
            result = self.db.table("user_memories").upsert({
                "user_id": self.user_id,
                "memory_data": self._memory_cache,
                "updated_at": "now()"
            }).execute()
            self._is_dirty = False
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error saving memory for user {self.user_id}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a memory value by key.
        
        Args:
            key: Memory key
            default: Default value if key not found
            
        Returns:
            Memory value or default if not found
        """
        return self._memory_cache.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a memory value.
        
        Args:
            key: Memory key
            value: Memory value to store
        """
        self._memory_cache[key] = value
        self._is_dirty = True
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update memory with multiple values.
        
        Args:
            data: Dictionary of key-value pairs to update
        """
        self._memory_cache.update(data)
        self._is_dirty = True
    
    def delete(self, key: str) -> bool:
        """Delete a memory value.
        
        Args:
            key: Memory key to delete
            
        Returns:
            True if key was deleted, False if key wasn't found
        """
        if key in self._memory_cache:
            del self._memory_cache[key]
            self._is_dirty = True
            return True
        return False
    
    def clear(self) -> None:
        """Clear all memory values."""
        self._memory_cache.clear()
        self._is_dirty = True
    
    async def load_state(self, state: 'ConversationState') -> None:
        """Load conversation state from memory.
        
        Args:
            state: Conversation state object to load into
        """
        if not self._is_loaded:
            await self.load()
        
        # Load conversation history
        history = self.get("conversation_history", [])
        state.history = history
        
        # Load slots/project data
        project_data = self.get("project_data", {})
        if project_data:
            state.slots.update(project_data)
        
        # Load vision data if available
        vision_data = self.get("vision_data", {})
        if vision_data:
            state.vision_context = vision_data
    
    async def save_state(self, state: 'ConversationState') -> None:
        """Save conversation state to memory.
        
        Args:
            state: Conversation state object to save
        """
        # Limit history to most recent 20 exchanges
        history = state.history[-20:] if len(state.history) > 20 else state.history
        self.set("conversation_history", history)
        
        # Save slots/project data
        self.set("project_data", state.slots)
        
        # Save vision data if available
        if hasattr(state, 'vision_context') and state.vision_context:
            self.set("vision_data", state.vision_context)
        
        # Persist to database
        await self.save()
