#!/usr/bin/env python
"""
Persistent memory implementation using Supabase as backend storage.

This module provides persistent memory capabilities for InstaBids agents.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from supabase import Client

# Set up logging
logger = logging.getLogger(__name__)


class PersistentMemory:
    """Persistent memory with Supabase backend storage.
    
    This class provides persistent memory capabilities for agents, storing user
    preferences, conversation contexts, and interaction history.
    """
    
    def __init__(self, db: Client, user_id: str):
        """Initialize persistent memory for a user.
        
        Args:
            db: Supabase client instance
            user_id: User ID to associate with this memory instance
        """
        self.db = db
        self.user_id = user_id
        self._data = {}
        self._dirty = False
        self._loaded = False
        
    async def load(self) -> bool:
        """Load memory from database.
        
        Returns:
            bool: True if memory was loaded successfully, False otherwise
        """
        try:
            # Convert string user_id to UUID if needed
            user_uuid = self._ensure_uuid(self.user_id)
            
            # Check if memory exists for this user
            response = self.db.table('user_memories').select('*').eq('user_id', user_uuid).execute()
            
            if response.data and len(response.data) > 0:
                # Memory exists, load it
                self._data = response.data[0]['memory_data']
                logger.info(f"Loaded memory for user {self.user_id}")
            else:
                # No memory exists, create a new one
                logger.info(f"No memory found for user {self.user_id}, creating new memory")
                new_memory = {
                    'user_id': user_uuid,
                    'memory_data': {}
                }
                response = self.db.table('user_memories').insert(new_memory).execute()
                self._data = {}
            
            self._loaded = True
            self._dirty = False
            return True
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return False
    
    async def save(self) -> bool:
        """Save memory to database if it has changed.
        
        Returns:
            bool: True if memory was saved successfully, False otherwise
        """
        if not self._loaded:
            logger.warning("Attempted to save memory before loading it")
            return False
        
        if not self._dirty:
            logger.debug("Memory not dirty, skipping save")
            return True
        
        try:
            # Convert string user_id to UUID if needed
            user_uuid = self._ensure_uuid(self.user_id)
            
            # Update memory data
            self.db.table('user_memories').update({
                'memory_data': self._data,
                'updated_at': datetime.now().isoformat()
            }).eq('user_id', user_uuid).execute()
            
            logger.info(f"Saved memory for user {self.user_id}")
            self._dirty = False
            return True
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from memory.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Value associated with the key, or default if not found
        """
        if not self._loaded:
            logger.warning(f"Attempted to access memory key '{key}' before loading")
            return default
        
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in memory.
        
        Args:
            key: Key to set
            value: Value to associate with the key
        """
        if not self._loaded:
            logger.warning(f"Attempted to set memory key '{key}' before loading")
            return
        
        self._data[key] = value
        self._dirty = True
    
    def delete(self, key: str) -> bool:
        """Delete a key from memory.
        
        Args:
            key: Key to delete
            
        Returns:
            bool: True if key was deleted, False if key wasn't found
        """
        if not self._loaded:
            logger.warning(f"Attempted to delete memory key '{key}' before loading")
            return False
        
        if key in self._data:
            del self._data[key]
            self._dirty = True
            return True
        return False
    
    async def add_interaction(self, interaction_type: str, data: Dict[str, Any]) -> bool:
        """Record a user interaction.
        
        Args:
            interaction_type: Type of interaction (e.g., "project_creation", "conversation")
            data: Data associated with the interaction
            
        Returns:
            bool: True if interaction was recorded successfully, False otherwise
        """
        try:
            # Convert string user_id to UUID if needed
            user_uuid = self._ensure_uuid(self.user_id)
            
            # Record interaction
            interaction = {
                'user_id': user_uuid,
                'interaction_type': interaction_type,
                'interaction_data': data
            }
            self.db.table('user_memory_interactions').insert(interaction).execute()
            logger.info(f"Recorded {interaction_type} interaction for user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
            return False
    
    def get_recent_interactions(self, interaction_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent interactions.
        
        Args:
            interaction_type: Optional filter by interaction type
            limit: Maximum number of interactions to return
            
        Returns:
            List of recent interactions with timestamps
        """
        try:
            # Convert string user_id to UUID if needed
            user_uuid = self._ensure_uuid(self.user_id)
            
            # Build query
            query = self.db.table('user_memory_interactions').select('*').eq('user_id', user_uuid)
            
            if interaction_type:
                query = query.eq('interaction_type', interaction_type)
            
            # Execute query with limit and order by created_at
            response = query.order('created_at', desc=True).limit(limit).execute()
            
            # Format interactions for return
            interactions = []
            for item in response.data:
                interactions.append({
                    'type': item['interaction_type'],
                    'data': item['interaction_data'],
                    'timestamp': item['created_at']
                })
            
            return interactions
        except Exception as e:
            logger.error(f"Error retrieving interactions: {e}")
            return []
    
    async def set_preference(self, key: str, value: Any, confidence: float = 0.5, source: str = "extraction") -> bool:
        """Set or update a user preference.
        
        Args:
            key: Preference key (e.g., "preferred_project_types")
            value: Preference value (will be stored as JSON)
            confidence: Confidence score (0-1) for the preference
            source: Source of the preference (e.g., "project_creation")
            
        Returns:
            bool: True if preference was set successfully, False otherwise
        """
        try:
            # Convert string user_id to UUID if needed
            user_uuid = self._ensure_uuid(self.user_id)
            
            # Check if preference exists
            response = self.db.table('user_preferences').select('*').eq('user_id', user_uuid).eq('preference_key', key).execute()
            
            if response.data and len(response.data) > 0:
                # Update existing preference
                pref_id = response.data[0]['id']
                self.db.table('user_preferences').update({
                    'preference_value': value,
                    'confidence': max(0.0, min(1.0, confidence)),  # Clamp to [0, 1]
                    'source': source,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', pref_id).execute()
            else:
                # Create new preference
                preference = {
                    'user_id': user_uuid,
                    'preference_key': key,
                    'preference_value': value,
                    'confidence': max(0.0, min(1.0, confidence)),  # Clamp to [0, 1]
                    'source': source
                }
                self.db.table('user_preferences').insert(preference).execute()
            
            logger.info(f"Set preference '{key}' for user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting preference: {e}")
            return False
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference.
        
        Args:
            key: Preference key to retrieve
            default: Default value if preference doesn't exist
            
        Returns:
            The preference value, or default if not found
        """
        try:
            # Convert string user_id to UUID if needed
            user_uuid = self._ensure_uuid(self.user_id)
            
            # Get preference
            response = self.db.table('user_preferences').select('*').eq('user_id', user_uuid).eq('preference_key', key).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['preference_value']
            return default
        except Exception as e:
            logger.error(f"Error retrieving preference: {e}")
            return default
    
    def get_all_preferences(self, min_confidence: float = 0.0) -> Dict[str, Any]:
        """Get all user preferences with confidence above threshold.
        
        Args:
            min_confidence: Minimum confidence threshold (0-1)
            
        Returns:
            Dictionary of preference key-value pairs
        """
        try:
            # Convert string user_id to UUID if needed
            user_uuid = self._ensure_uuid(self.user_id)
            
            # Get preferences with confidence filter
            response = self.db.table('user_preferences').select('*').eq('user_id', user_uuid).gte('confidence', min_confidence).execute()
            
            preferences = {}
            for pref in response.data:
                preferences[pref['preference_key']] = pref['preference_value']
            
            return preferences
        except Exception as e:
            logger.error(f"Error retrieving preferences: {e}")
            return {}
    
    def _ensure_uuid(self, user_id: Union[str, uuid.UUID]) -> uuid.UUID:
        """Ensure that the user_id is a proper UUID.
        
        Args:
            user_id: User ID as string or UUID
            
        Returns:
            UUID object for the user ID
        """
        if isinstance(user_id, uuid.UUID):
            return user_id
        
        try:
            return uuid.UUID(str(user_id))
        except ValueError:
            # If the user_id is not a valid UUID, log an error and use a default UUID
            logger.error(f"Invalid UUID format for user_id: {user_id}. Using a default UUID.")
            # Generate a deterministic UUID based on the string
            return uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id))