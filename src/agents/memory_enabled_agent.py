"""Base class for agents with integrated memory and slot filling capabilities."""

import logging
from typing import Dict, Any, List, Optional, Callable
import asyncio

from supabase import Client
from google.adk.conversation import Agent, Response, Message, ConversationHandler

from src.memory.persistent_memory import PersistentMemory
from src.slot_filler.slot_filler_factory import SlotFillerFactory, SlotFiller

logger = logging.getLogger(__name__)


class MemoryEnabledAgent(Agent):
    """Base agent class with integrated persistent memory and slot filling."""

    def __init__(self, db: Client):
        """Initialize with database connection."""
        super().__init__()
        self.db = db
        self._memory_instances: Dict[str, PersistentMemory] = {}
        self._slot_filler_instances: Dict[str, SlotFiller] = {}
        self._slot_filler_factory = None

    async def _ensure_memory(self, user_id: str) -> PersistentMemory:
        """Ensure a memory instance exists for the user and return it."""
        if user_id not in self._memory_instances:
            memory = PersistentMemory(self.db, user_id)
            await memory.load()
            self._memory_instances[user_id] = memory
        return self._memory_instances[user_id]

    async def _ensure_slot_filler_factory(self, user_id: str) -> SlotFillerFactory:
        """Ensure a slot filler factory exists for the user and return it."""
        if self._slot_filler_factory is None:
            memory = await self._ensure_memory(user_id)
            self._slot_filler_factory = SlotFillerFactory(memory)
        return self._slot_filler_factory

    async def _get_or_create_slot_filler(
        self, user_id: str, conversation_id: str, required_slots: List[str], optional_slots: Optional[List[str]] = None
    ) -> SlotFiller:
        """Get an existing slot filler or create a new one."""
        key = f"{user_id}:{conversation_id}"
        if key not in self._slot_filler_instances:
            factory = await self._ensure_slot_filler_factory(user_id)
            slot_filler = await factory.create_slot_filler(conversation_id, required_slots, optional_slots)
            self._slot_filler_instances[key] = slot_filler
        return self._slot_filler_instances[key]

    async def handle(self, message: Message, handler: ConversationHandler) -> Response:
        """Handle an incoming message with memory and slot filling capabilities."""
        user_id = message.sender_id or "anonymous"
        conversation_id = message.conversation_id or "default"

        # Ensure memory is loaded for this user
        memory = await self._ensure_memory(user_id)
        
        # Process the message and generate a response
        try:
            response_text = await self._process_message_with_memory(message, user_id, conversation_id)
            response = Response(text=response_text)
            
            # Record the interaction in memory
            await memory.add_interaction(
                "conversation",
                {
                    "user_message": message.text,
                    "agent_response": response_text,
                    "conversation_id": conversation_id,
                    "has_attachments": bool(message.attachments)
                }
            )
            
            return response
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await memory.add_interaction(
                "error",
                {
                    "error_type": str(type(e)),
                    "error_message": str(e),
                    "user_message": message.text,
                    "conversation_id": conversation_id
                }
            )
            return Response(text="I'm sorry, I encountered an error processing your message. Please try again.")

    async def _process_message_with_memory(self, message: Message, user_id: str, conversation_id: str) -> str:
        """Process a message using memory and slot filling.
        
        Override this method in derived classes to implement specific agent logic.
        """
        raise NotImplementedError("Subclasses must implement this method")

    async def _process_with_slot_filling(
        self,
        message: Message,
        user_id: str,
        conversation_id: str,
        required_slots: List[str],
        optional_slots: Optional[List[str]] = None,
        text_extractors: Optional[Dict[str, Callable]] = None,
        vision_extractors: Optional[Dict[str, Callable]] = None,
        slot_filled_handler: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process a message with slot filling.
        
        Args:
            message: The incoming message
            user_id: ID of the user
            conversation_id: ID of the conversation
            required_slots: List of required slot names
            optional_slots: Optional list of optional slot names
            text_extractors: Optional dict mapping slot names to text extractor functions
            vision_extractors: Optional dict mapping slot names to vision extractor functions
            slot_filled_handler: Optional function called when all required slots are filled
            
        Returns:
            Dictionary with slot filling results
        """
        # Get or create slot filler
        slot_filler = await self._get_or_create_slot_filler(
            user_id, conversation_id, required_slots, optional_slots
        )
        
        # Update conversation history
        await slot_filler.update_from_message("user", message.text, message.attachments)
        
        # Extract slots from text
        extracted_from_text = {}
        if message.text and text_extractors:
            extracted_from_text = await slot_filler.extract_slots_from_message(
                message.text, text_extractors
            )
        
        # Extract slots from images/attachments
        extracted_from_vision = {}
        if message.attachments and vision_extractors:
            for attachment in message.attachments:
                if attachment.get("type") == "image":
                    vision_results = await slot_filler.process_vision_inputs(
                        attachment, vision_extractors
                    )
                    extracted_from_vision.update(vision_results)
        
        # Check if all required slots are filled
        all_filled = slot_filler.all_required_slots_filled()
        
        # Call handler if all slots are filled and handler is provided
        if all_filled and slot_filled_handler is not None:
            try:
                await slot_filled_handler(slot_filler)
            except Exception as e:
                logger.error(f"Error in slot filled handler: {e}", exc_info=True)
        
        # Prepare result
        result = {
            "all_required_slots_filled": all_filled,
            "missing_slots": slot_filler.get_missing_required_slots(),
            "filled_slots": slot_filler.get_filled_slots(),
            "extracted_from_text": extracted_from_text,
            "extracted_from_vision": extracted_from_vision,
            "slot_filler": slot_filler
        }
        
        return result