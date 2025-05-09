#!/usr/bin/env python
"""
Integrated persistent memory for InstaBids A2A communication system.

This module combines the functionality of:
1. PersistentMemory - Database-backed memory storage
2. ConversationState - Conversation tracking with multi-modal inputs 
3. A2A Message Routing - Agent-to-agent communication history integration

Part of sprint/memory-a2a-integration.
"""

import json
import logging
import uuid
import datetime
from typing import Any, Dict, List, Optional, Set, Union

from google.adk.memory import Memory
from supabase import Client

# Set up logging
logger = logging.getLogger(__name__)


class IntegratedMemory(Memory):
    """Integrated persistent memory with conversation state tracking and A2A support.
    
    This class provides persistent memory capabilities for agents, storing:
    - User preferences
    - Conversation contexts and history
    - Multi-modal inputs
    - Agent-to-agent message routing information
    """
    
    def __init__(self, db: Client, user_id: str):
        """Initialize integrated memory for a user.
        
        Args:
            db: Supabase client instance
            user_id: User ID to associate with this memory instance
        """
        super().__init__()  # Initialize base Memory class
        self.db = db
        self.user_id = user_id
        self._memory_cache = {}  # In-memory cache
        self._is_loaded = False
        self._is_dirty = False
        
        # Conversation state tracking
        self.conversation_id = str(uuid.uuid4())  # Default conversation ID
        self.history = []
        self.slots = {}
        self.required_slots = set()
        self.optional_slots = set()
        self.multi_modal_context = {}
        self.session_ids = set()  # Track active conversation sessions

    async def load(self) -> bool:
        """Load memory from database.
        
        Returns:
            bool: True if memory was loaded successfully, False otherwise
        """
        if self._is_loaded:
            return True

        try:
            logger.info(f"Loading memory for user {self.user_id}")
            result = (
                await self.db.table("user_memories")
                .select("*")
                .eq("user_id", self.user_id)
                .maybe_single()
                .execute()
            )

            if result.data:
                # Load memory from database
                memory_data = result.data.get("memory_data", {})
                self._memory_cache = memory_data
                
                # Extract conversation state if available
                if "conversation_state" in memory_data:
                    conv_state = memory_data["conversation_state"]
                    self.conversation_id = conv_state.get("conversation_id", self.conversation_id)
                    self.history = conv_state.get("history", [])
                    self.slots = conv_state.get("slots", {})
                    self.required_slots = set(conv_state.get("required_slots", []))
                    self.optional_slots = set(conv_state.get("optional_slots", []))
                    self.multi_modal_context = conv_state.get("multi_modal_context", {})
                    self.session_ids = set(conv_state.get("session_ids", []))
                
                logger.info(f"Successfully loaded memory for user {self.user_id}")
                self._is_loaded = True
                self._is_dirty = False
                return True
            else:
                # Initialize new memory
                logger.info(f"No existing memory found for user {self.user_id}. Initializing.")
                self._memory_cache = {
                    "interactions": [],
                    "context": {},
                    "conversation_state": {
                        "conversation_id": self.conversation_id,
                        "history": [],
                        "slots": {},
                        "required_slots": [],
                        "optional_slots": [],
                        "multi_modal_context": {},
                        "session_ids": []
                    },
                    "learned_preferences": {},
                    "creation_date": datetime.datetime.utcnow().isoformat(),
                }
                self._is_loaded = True
                self._is_dirty = True
                await self.save()  # Create initial memory record
                return True

        except Exception as e:
            logger.error(f"Error loading memory for user {self.user_id}: {e}", exc_info=True)
            return False

    async def save(self) -> bool:
        """Save memory to database if it has changed.
        
        Returns:
            bool: True if memory was saved successfully, False otherwise
        """
        if not self._is_loaded:
            logger.warning("Attempted to save memory before loading it")
            return False
        
        if not self._is_dirty:
            logger.debug("Memory not dirty, skipping save")
            return True
        
        try:
            logger.info(f"Saving memory for user {self.user_id}")
            
            # Update conversation state in memory cache before saving
            self._memory_cache["conversation_state"] = {
                "conversation_id": self.conversation_id,
                "history": self.history,
                "slots": self.slots,
                "required_slots": list(self.required_slots),
                "optional_slots": list(self.optional_slots),
                "multi_modal_context": self.multi_modal_context,
                "session_ids": list(self.session_ids),
            }
            
            # Update timestamp before saving
            self._memory_cache["last_updated"] = datetime.datetime.utcnow().isoformat()
            
            # Update memory in database
            result = (
                await self.db.table("user_memories")
                .upsert(
                    {
                        "user_id": self.user_id,
                        "memory_data": self._memory_cache,
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            if result.data:
                self._is_dirty = False
                logger.info(f"Successfully saved memory for user {self.user_id}")
                return True
            else:
                logger.error(f"Failed to save memory for user {self.user_id}")
                return False

        except Exception as e:
            logger.error(f"Error saving memory for user {self.user_id}: {e}", exc_info=True)
            return False

    #
    # Conversation State Management
    #
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: Role of the sender (e.g., "user", "assistant")
            content: Message content
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        self.history.append(message)
        self._is_dirty = True
    
    def add_multi_modal_input(self, input_id: str, input_type: str, data: Dict[str, Any]) -> None:
        """Add a multi-modal input to the conversation context.
        
        Args:
            input_id: Unique identifier for the input
            input_type: Type of input (e.g., "image", "audio")
            data: Input data including URL, metadata, etc.
        """
        self.multi_modal_context[input_id] = {
            "type": input_type,
            "data": data,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        self._is_dirty = True
    
    def set_required_slots(self, slots: List[str]) -> None:
        """Set the required slots for this conversation.
        
        Args:
            slots: List of required slot names
        """
        self.required_slots = set(slots)
        self._is_dirty = True
    
    def set_optional_slots(self, slots: List[str]) -> None:
        """Set the optional slots for this conversation.
        
        Args:
            slots: List of optional slot names
        """
        self.optional_slots = set(slots)
        self._is_dirty = True
    
    def set_slot(self, slot_name: str, value: Any) -> bool:
        """Set a slot value.
        
        Args:
            slot_name: Name of the slot
            value: Value to assign to the slot
            
        Returns:
            bool: True if this is a valid slot, False otherwise
        """
        if slot_name in self.required_slots or slot_name in self.optional_slots:
            self.slots[slot_name] = value
            self._is_dirty = True
            return True
        else:
            logger.warning(f"Attempted to set unknown slot '{slot_name}'")
            return False
    
    def get_slot(self, slot_name: str, default: Any = None) -> Any:
        """Get a slot value.
        
        Args:
            slot_name: Name of the slot
            default: Default value if slot is not filled
            
        Returns:
            Slot value or default
        """
        return self.slots.get(slot_name, default)
    
    def get_all_slots(self) -> Dict[str, Any]:
        """Get all filled slots.
        
        Returns:
            Dictionary of all filled slots
        """
        return self.slots.copy()
    
    def get_missing_required_slots(self) -> Set[str]:
        """Get the set of required slots that haven't been filled.
        
        Returns:
            Set of missing required slot names
        """
        return self.required_slots - set(self.slots.keys())
    
    def all_required_slots_filled(self) -> bool:
        """Check if all required slots are filled.
        
        Returns:
            bool: True if all required slots are filled, False otherwise
        """
        return len(self.get_missing_required_slots()) == 0
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history.
        
        Returns:
            List of messages in the conversation
        """
        return self.history.copy()
    
    def get_multi_modal_context(self) -> Dict[str, Dict[str, Any]]:
        """Get the multi-modal context data.
        
        Returns:
            Dictionary of multi-modal inputs
        """
        return self.multi_modal_context.copy()
    
    def add_session_id(self, session_id: str) -> None:
        """Associate a session ID with this conversation.
        
        Args:
            session_id: Session ID to associate
        """
        self.session_ids.add(session_id)
        self._is_dirty = True
    
    def get_session_ids(self) -> List[str]:
        """Get all session IDs associated with this conversation.
        
        Returns:
            List of session IDs
        """
        return list(self.session_ids)

    #
    # User Interactions and Preferences
    #
    
    async def add_interaction(self, interaction_type: str, data: Dict[str, Any]) -> bool:
        """Record a new user interaction in memory.
        
        Args:
            interaction_type: Type of interaction (e.g., "project_creation", "conversation")
            data: Data associated with the interaction
            
        Returns:
            bool: True if interaction was recorded successfully, False otherwise
        """
        if not self._is_loaded and not await self.load():
            return False

        try:
            # Add to in-memory cache
            timestamp = datetime.datetime.utcnow().isoformat()
            interaction = {
                "type": interaction_type,
                "timestamp": timestamp,
                "data": data,
            }

            if "interactions" not in self._memory_cache:
                self._memory_cache["interactions"] = []

            self._memory_cache["interactions"].append(interaction)
            self._is_dirty = True

            # Also store in detailed interaction history table
            await self.db.table("user_memory_interactions").insert(
                {
                    "user_id": self.user_id,
                    "interaction_type": interaction_type,
                    "interaction_data": data,
                    "created_at": timestamp,
                }
            ).execute()

            # Process for potential preference learning
            await self._extract_preferences(interaction_type, data)

            return True

        except Exception as e:
            logger.error(f"Error adding interaction for user {self.user_id}: {e}", exc_info=True)
            return False

    async def _extract_preferences(self, interaction_type: str, data: Dict[str, Any]):
        """Extract and update user preferences from interaction data.
        
        Args:
            interaction_type: Type of interaction
            data: Interaction data
        """
        try:
            # Example preference extraction logic - customize based on interaction types
            if interaction_type == "project_creation":
                # Extract project type preference
                if "project_type" in data:
                    await self._update_preference(
                        "preferred_project_types",
                        data["project_type"],
                        "project_creation",
                    )

                # Extract timeline preference
                if "timeline" in data:
                    await self._update_preference(
                        "timeline_preference", data["timeline"], "project_creation"
                    )

            elif interaction_type == "contractor_selection":
                # Extract contractor preference indicators
                if "selected_contractor" in data and "contractor_attributes" in data:
                    for attr, value in data["contractor_attributes"].items():
                        await self._update_preference(
                            f"contractor_{attr}_preference",
                            value,
                            "contractor_selection",
                        )
        except Exception as e:
            logger.error(
                f"Error extracting preferences for user {self.user_id}: {e}",
                exc_info=True,
            )

    async def _update_preference(self, preference_key: str, value: Any, source: str):
        """Update a user preference in the database and memory cache.
        
        Args:
            preference_key: Preference key (e.g., "preferred_project_types")
            value: Preference value
            source: Source of the preference (e.g., "extraction")
        """
        try:
            # Update in-memory representation
            if "learned_preferences" not in self._memory_cache:
                self._memory_cache["learned_preferences"] = {}

            if preference_key not in self._memory_cache["learned_preferences"]:
                self._memory_cache["learned_preferences"][preference_key] = {
                    "value": value,
                    "count": 1,
                }
            else:
                # Simple counting-based preference strengthening
                current = self._memory_cache["learned_preferences"][preference_key]
                if current["value"] == value:
                    current["count"] += 1
                else:
                    # Different value - handle conflict based on count
                    if current["count"] <= 2:  # Threshold for changing preference
                        current["value"] = value
                        current["count"] = 1
                    # Else keep existing preference as it's stronger

            self._is_dirty = True

            # Store in preferences table with confidence score
            count = self._memory_cache["learned_preferences"][preference_key]["count"]
            confidence = min(0.5 + (count * 0.1), 0.95)  # Simple confidence scaling

            await self.db.table("user_preferences").upsert(
                {
                    "user_id": self.user_id,
                    "preference_key": preference_key,
                    "preference_value": value,
                    "confidence": confidence,
                    "source": source,
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                }
            ).execute()

        except Exception as e:
            logger.error(
                f"Error updating preference for user {self.user_id}: {e}", exc_info=True
            )
    
    def get_recent_interactions(
        self, interaction_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """Get recent user interactions, optionally filtered by type.
        
        Args:
            interaction_type: Optional filter by interaction type
            limit: Maximum number of interactions to return
            
        Returns:
            List of recent interactions with timestamps
        """
        if not self._is_loaded:
            return []

        interactions = self._memory_cache.get("interactions", [])

        if interaction_type:
            interactions = [i for i in interactions if i["type"] == interaction_type]

        # Sort by timestamp (newest first) and limit
        return sorted(interactions, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_preference(self, preference_key: str) -> Any:
        """Get a learned user preference.
        
        Args:
            preference_key: Preference key to retrieve
            
        Returns:
            The preference value, or None if not found
        """
        if not self._is_loaded:
            return None

        prefs = self._memory_cache.get("learned_preferences", {})
        if preference_key in prefs:
            return prefs[preference_key]["value"]
        return None

    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all learned preferences with their values.
        
        Returns:
            Dictionary mapping preference keys to values
        """
        if not self._is_loaded:
            return {}

        prefs = self._memory_cache.get("learned_preferences", {})
        return {k: v["value"] for k, v in prefs.items()}

    #
    # Implement required Memory interface methods
    #
    
    def get(self, key: str) -> Any:
        """Get a value from memory by key.
        
        Args:
            key: Key to retrieve
            
        Returns:
            Value associated with the key, or None if not found
        """
        if not self._is_loaded:
            logger.warning(f"Attempted to get key '{key}' from unloaded memory")
            return None
            
        return self._memory_cache.get("context", {}).get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value in memory by key.
        
        Args:
            key: Key to set
            value: Value to associate with the key
        """
        if not self._is_loaded:
            logger.warning(f"Attempted to set key '{key}' to unloaded memory")
            return

        if "context" not in self._memory_cache:
            self._memory_cache["context"] = {}

        self._memory_cache["context"][key] = value
        self._is_dirty = True

    #
    # A2A Message Routing Integration
    #
    
    async def record_agent_message(
        self, 
        message_id: str,
        task_id: str, 
        sender_agent_id: str,
        recipient_agent_id: str, 
        content: str,
        role: str, 
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a message exchange between agents.
        
        Args:
            message_id: Unique identifier for the message
            task_id: ID of the task this message relates to
            sender_agent_id: ID of the sending agent
            recipient_agent_id: ID of the receiving agent
            content: Message content
            role: Message role (e.g., "user", "assistant")
            session_id: Optional session identifier
            metadata: Optional metadata about the message
            
        Returns:
            bool: True if message was recorded successfully, False otherwise
        """
        try:
            # Record message in agent_messages table
            timestamp = datetime.datetime.utcnow().isoformat()
            
            result = await self.db.table("agent_messages").insert({
                "message_id": message_id,
                "task_id": task_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "sender_agent_id": sender_agent_id,
                "recipient_agent_id": recipient_agent_id,
                "created_at": timestamp,
                "metadata": metadata or {}
            }).execute()
            
            # Add session ID to conversation if provided
            if session_id and session_id not in self.session_ids:
                self.add_session_id(session_id)
            
            # Also record as a regular interaction
            interaction_data = {
                "message_id": message_id,
                "task_id": task_id,
                "sender": sender_agent_id,
                "recipient": recipient_agent_id,
                "content_summary": content[:100] + "..." if len(content) > 100 else content,
                "role": role
            }
            await self.add_interaction("agent_message", interaction_data)
            
            logger.info(f"Recorded agent message {message_id} from {sender_agent_id} to {recipient_agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording agent message: {e}", exc_info=True)
            return False
    
    async def record_message_routing(
        self,
        message_id: str,
        task_id: str,
        sender_agent_id: str,
        recipient_agent_id: str,
        route_status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a message routing event.
        
        Args:
            message_id: ID of the message being routed
            task_id: ID of the task this message relates to
            sender_agent_id: ID of the sending agent
            recipient_agent_id: ID of the intended recipient agent
            route_status: Status of the routing (e.g., "delivered", "failed")
            metadata: Optional metadata about the routing
            
        Returns:
            bool: True if routing was recorded successfully, False otherwise
        """
        try:
            # Record routing in message_routing_logs table
            timestamp = datetime.datetime.utcnow().isoformat()
            
            result = await self.db.table("message_routing_logs").insert({
                "message_id": message_id,
                "task_id": task_id,
                "sender_agent_id": sender_agent_id,
                "recipient_agent_id": recipient_agent_id,
                "route_status": route_status,
                "route_timestamp": timestamp,
                "metadata": metadata or {}
            }).execute()
            
            logger.info(f"Recorded message routing: {message_id} from {sender_agent_id} to {recipient_agent_id} ({route_status})")
            return True
            
        except Exception as e:
            logger.error(f"Error recording message routing: {e}", exc_info=True)
            return False
    
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
        try:
            # Build query
            query = self.db.table("agent_messages").select("*")
            
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
