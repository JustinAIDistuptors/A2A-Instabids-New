#!/usr/bin/env python
"""
Base agent class with memory and slot filling capabilities.

This module provides a base agent class that integrates persistent memory and slot filling.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Set, Callable, Tuple, Union

from google.adk.conversation import Message, Response

from ..memory.persistent_memory import PersistentMemory
from ..slot_filler.slot_filler_factory import SlotFillerFactory, SlotFiller

# Set up logging
logger = logging.getLogger(__name__)


class MemoryEnabledAgent:
    """Base agent class with memory and slot filling capabilities.
    
    This class provides a foundation for building agents that use persistent memory
    and slot filling to maintain context across conversations.
    """
    
    def __init__(self, db):
        """Initialize agent.
        
        Args:
            db: Database client (Supabase)
        """
        self.db = db
        self._memories = {}  # Cache of PersistentMemory instances by user_id
        self._slot_filler_factories = {}  # Cache of SlotFillerFactory instances by user_id
    
    async def process_message(self, message: Message) -> Response:
        """Process an incoming message.
        
        Args:
            message: Input message from A2A
            
        Returns:
            Response: Agent response
        """
        user_id = message.get_user_id()
        conversation_id = message.get_conversation_id()
        
        if not user_id:
            # Generate a temporary user ID if none is provided
            user_id = str(uuid.uuid4())
            logger.warning(f"No user ID provided, using temporary ID: {user_id}")
        
        if not conversation_id:
            # Generate a temporary conversation ID if none is provided
            conversation_id = str(uuid.uuid4())
            logger.warning(f"No conversation ID provided, using temporary ID: {conversation_id}")
        
        # Process message with memory
        response_text = await self._process_message_with_memory(
            message=message,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        # Create response
        return Response(text=response_text)
    
    async def _get_memory(self, user_id: str) -> PersistentMemory:
        """Get or create a memory instance for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            PersistentMemory instance
        """
        if user_id not in self._memories:
            memory = PersistentMemory(self.db, user_id)
            await memory.load()
            self._memories[user_id] = memory
        return self._memories[user_id]
    
    async def _get_slot_filler_factory(self, user_id: str) -> SlotFillerFactory:
        """Get or create a slot filler factory for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            SlotFillerFactory instance
        """
        if user_id not in self._slot_filler_factories:
            memory = await self._get_memory(user_id)
            self._slot_filler_factories[user_id] = SlotFillerFactory(memory)
        return self._slot_filler_factories[user_id]
    
    async def _process_message_with_memory(self, message: Message, user_id: str, conversation_id: str) -> str:
        """Process a message with memory integration.
        
        This method should be overridden by subclasses to implement agent-specific logic.
        
        Args:
            message: Input message
            user_id: User ID
            conversation_id: Conversation ID
            
        Returns:
            str: Response text
        """
        # Default implementation just echoes the message
        text = message.get_text() or "No text provided"
        return f"Received: {text}"
    
    async def _process_with_slot_filling(
        self,
        message: Message,
        user_id: str,
        conversation_id: str,
        required_slots: List[str],
        optional_slots: List[str],
        text_extractors: Dict[str, Callable[[str], Optional[Any]]],
        vision_extractors: Optional[Dict[str, Callable[[Dict[str, Any]], Optional[Any]]]] = None
    ) -> Dict[str, Any]:
        """Process a message with slot filling.
        
        Args:
            message: Input message
            user_id: User ID
            conversation_id: Conversation ID
            required_slots: List of required slot names
            optional_slots: List of optional slot names
            text_extractors: Dictionary mapping slot names to text extractor functions
            vision_extractors: Optional dictionary mapping slot names to vision extractor functions
            
        Returns:
            Dict containing slot filling results and state
        """
        factory = await self._get_slot_filler_factory(user_id)
        slot_filler = await factory.create_slot_filler(conversation_id, required_slots, optional_slots)
        
        # Get message text
        text = message.get_text() or ""
        
        # Update conversation history
        await slot_filler.update_from_message("user", text)
        
        # Extract slots from text
        extracted_from_text = await slot_filler.extract_slots_from_message(text, text_extractors)
        
        # Process vision inputs if provided
        extracted_from_vision = {}
        if vision_extractors and message.has_media():
            for media_item in message.get_media() or []:
                try:
                    media_data = {
                        "id": media_item.get("id", str(uuid.uuid4())),
                        "url": media_item.get("url", ""),
                        "metadata": media_item.get("metadata", {})
                    }
                    vision_results = await slot_filler.process_vision_inputs(media_data, vision_extractors)
                    extracted_from_vision.update(vision_results)
                except Exception as e:
                    logger.error(f"Error processing vision input: {e}")
        
        # Get slot filling results
        filled_slots = slot_filler.get_filled_slots()
        missing_slots = list(slot_filler.get_missing_required_slots())
        all_required_filled = slot_filler.all_required_slots_filled()
        
        # Return slot filling results and state
        return {
            "filled_slots": filled_slots,
            "missing_slots": missing_slots,
            "all_required_slots_filled": all_required_filled,
            "extracted_from_text": extracted_from_text,
            "extracted_from_vision": extracted_from_vision,
            "slot_filler": slot_filler
        }
        
    async def _update_conversation(self, slot_filler: SlotFiller, role: str, content: str) -> None:
        """Update conversation with a new message.
        
        Args:
            slot_filler: SlotFiller instance
            role: Role of the sender (e.g., "user", "assistant")
            content: Message content
        """
        await slot_filler.update_from_message(role, content)