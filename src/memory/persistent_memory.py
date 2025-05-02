"""
PersistentMemory implementation that provides user-specific memory persistence.
"""

import logging
from typing import Dict, List, Any, Optional
import json
import datetime

# Fix: Update import to use instabids_google.adk.memory instead of google.adk.memory
from instabids_google.adk.memory import Memory
from supabase import Client

logger = logging.getLogger(__name__)


class PersistentMemory(Memory):
    """
    User-specific persistent memory implementation compatible with ADK.
    Stores and retrieves memory from Supabase database.
    """

    def __init__(self, db: Client, user_id: str):
        """Initialize with database client and user ID."""
        super().__init__()  # Initialize base Memory class
        self.db = db
        self.user_id = user_id
        self._memory_cache: Dict[str, Any] = {}  # In-memory cache
        self._is_loaded = False
        self._is_dirty = False  # Track if memory needs to be saved

    async def load(self) -> bool:
        """Load user's memory from database."""
        if self._is_loaded:
            return True

        try:
            logger.info(f"Loading memory for user {self.user_id}")
            result = (
                await self.db.table("user_memories")
                .select("memory_data")
                .eq("user_id", self.user_id)
                .maybe_single()
                .execute()
            )

            if result.data:
                self._memory_cache = json.loads(result.data["memory_data"])
                self._is_loaded = True
                logger.info(f"Memory loaded for user {self.user_id}")
                return True
            else:
                # Initialize empty memory structure
                self._memory_cache = {
                    "interactions": [],
                    "learned_preferences": {},
                    "context": {},
                }
                self._is_loaded = True
                self._is_dirty = True  # Mark as dirty to save the initial structure
                logger.info(f"Initialized new memory for user {self.user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to load memory for user {self.user_id}: {e}")
            return False

    async def save(self) -> bool:
        """Save memory to database if dirty."""
        if not self._is_loaded:
            logger.warning(f"Attempted to save unloaded memory for user {self.user_id}")
            return False

        if not self._is_dirty:
            logger.debug(f"Memory for user {self.user_id} is not dirty, skipping save")
            return True

        try:
            logger.info(f"Saving memory for user {self.user_id}")
            serialized = json.dumps(self._memory_cache)
            
            # Upsert memory data
            result = (
                await self.db.table("user_memories")
                .upsert(
                    {
                        "user_id": self.user_id,
                        "memory_data": serialized,
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            if result.data:
                self._is_dirty = False
                logger.info(f"Memory saved for user {self.user_id}")
                return True
            else:
                logger.error(f"Failed to save memory for user {self.user_id}: No data returned")
                return False

        except Exception as e:
            logger.error(f"Failed to save memory for user {self.user_id}: {e}")
            return False

    def add_interaction(self, interaction_type: str, data: Dict[str, Any]) -> None:
        """Add a user interaction to memory."""
        if not self._is_loaded:
            logger.warning(
                f"Attempted to add interaction to unloaded memory for user {self.user_id}"
            )
            return

        if "interactions" not in self._memory_cache:
            self._memory_cache["interactions"] = []

        # Add timestamp if not provided
        if "timestamp" not in data:
            data["timestamp"] = datetime.datetime.utcnow().isoformat()

        interaction = {
            "type": interaction_type,
            "data": data,
            "timestamp": data["timestamp"],
        }

        self._memory_cache["interactions"].append(interaction)
        self._is_dirty = True

        # Trim interactions if too many (keep most recent 100)
        if len(self._memory_cache["interactions"]) > 100:
            self._memory_cache["interactions"] = sorted(
                self._memory_cache["interactions"],
                key=lambda x: x["timestamp"],
                reverse=True,
            )[:100]

    def set_preference(self, preference_key: str, value: Any, confidence: float = 1.0) -> None:
        """Set a learned user preference with confidence level."""
        if not self._is_loaded:
            logger.warning(
                f"Attempted to set preference to unloaded memory for user {self.user_id}"
            )
            return

        if "learned_preferences" not in self._memory_cache:
            self._memory_cache["learned_preferences"] = {}

        self._memory_cache["learned_preferences"][preference_key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }
        self._is_dirty = True

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value in memory."""
        if not self._is_loaded:
            logger.warning(
                f"Attempted to set key '{key}' to unloaded memory for user {self.user_id}"
            )
            return

        if "context" not in self._memory_cache:
            self._memory_cache["context"] = {}

        self._memory_cache["context"][key] = value
        self._is_dirty = True

    def get_recent_interactions(
        self, interaction_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """Get recent user interactions, optionally filtered by type."""
        if not self._is_loaded:
            return []

        interactions = self._memory_cache.get("interactions", [])

        if interaction_type:
            interactions = [i for i in interactions if i["type"] == interaction_type]

        # Sort by timestamp (newest first) and limit
        return sorted(interactions, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_preference(self, preference_key: str) -> Any:
        """Get a learned user preference."""
        if not self._is_loaded:
            return None

        prefs = self._memory_cache.get("learned_preferences", {})
        if preference_key in prefs:
            return prefs[preference_key]["value"]
        return None

    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all learned preferences with their values."""
        if not self._is_loaded:
            return {}

        prefs = self._memory_cache.get("learned_preferences", {})
        return {k: v["value"] for k, v in prefs.items()}