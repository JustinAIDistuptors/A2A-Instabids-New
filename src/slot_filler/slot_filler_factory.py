#!/usr/bin/env python
"""
Factory for creating slot fillers with memory integration.

This module provides a factory class for creating slot fillers with persistent memory.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Callable

from ..memory.persistent_memory import PersistentMemory
from ..memory.conversation_state import ConversationState

# Set up logging
logger = logging.getLogger(__name__)


class SlotFiller:
    """Manages slot filling with persistent memory.
    
    Tracks and fills slots from text and multi-modal inputs with memory persistence.
    """
    
    def __init__(self, memory: PersistentMemory, state: ConversationState):
        """Initialize slot filler.
        
        Args:
            memory: PersistentMemory instance for the user
            state: ConversationState instance for this conversation
        """
        self.memory = memory
        self.state = state
    
    async def extract_slots_from_message(self, message: str, extractors: Dict[str, Callable[[str], Optional[Any]]]) -> Dict[str, Any]:
        """Extract slots from a text message.
        
        Args:
            message: Text message to extract slots from
            extractors: Dictionary mapping slot names to extractor functions
            
        Returns:
            Dictionary of extracted slots and their values
        """
        extracted = {}
        for slot_name, extractor in extractors.items():
            if slot_name in self.state.required_slots or slot_name in self.state.optional_slots:
                try:
                    value = extractor(message)
                    if value is not None:
                        self.state.set_slot(slot_name, value)
                        extracted[slot_name] = value
                except Exception as e:
                    logger.error(f"Error extracting slot '{slot_name}': {e}")
        
        # Record interaction if slots were extracted
        if extracted:
            await self.memory.add_interaction("slot_filling", {
                "conversation_id": self.state.conversation_id,
                "extracted_slots": extracted
            })
        
        return extracted
    
    async def process_vision_inputs(self, image_data: Dict[str, Any], extractors: Dict[str, Callable[[Dict[str, Any]], Optional[Any]]]) -> Dict[str, Any]:
        """Process vision inputs for slot filling.
        
        Args:
            image_data: Image data including URL, metadata, etc.
            extractors: Dictionary mapping slot names to vision extractor functions
            
        Returns:
            Dictionary of extracted slots and their values
        """
        # Add image to multi-modal context
        image_id = image_data.get("id", str(id(image_data)))  # Use provided ID or generate one
        self.state.add_multi_modal_input(image_id, "image", image_data)
        
        # Extract slots from image
        extracted = {}
        for slot_name, extractor in extractors.items():
            if slot_name in self.state.required_slots or slot_name in self.state.optional_slots:
                try:
                    value = extractor(image_data)
                    if value is not None:
                        self.state.set_slot(slot_name, value)
                        extracted[slot_name] = value
                except Exception as e:
                    logger.error(f"Error extracting slot '{slot_name}' from image: {e}")
        
        # Record interaction if slots were extracted
        if extracted:
            await self.memory.add_interaction("vision_slot_filling", {
                "conversation_id": self.state.conversation_id,
                "image_id": image_id,
                "extracted_slots": extracted
            })
        
        return extracted
    
    async def update_from_message(self, role: str, content: str) -> None:
        """Update conversation history with a new message.
        
        Args:
            role: Role of the sender (e.g., "user", "assistant")
            content: Message content
        """
        self.state.add_message(role, content)
        
        # Save state in memory
        conversation_states = self.memory.get("conversation_states", {})
        conversation_states[self.state.conversation_id] = self.state.to_dict()
        self.memory.set("conversation_states", conversation_states)
        await self.memory.save()
    
    def get_filled_slots(self) -> Dict[str, Any]:
        """Get all filled slots.
        
        Returns:
            Dictionary of all filled slots
        """
        return self.state.get_all_slots()
    
    def get_missing_required_slots(self) -> Set[str]:
        """Get the set of required slots that haven't been filled.
        
        Returns:
            Set of missing required slot names
        """
        return self.state.get_missing_required_slots()
    
    def all_required_slots_filled(self) -> bool:
        """Check if all required slots are filled.
        
        Returns:
            bool: True if all required slots are filled, False otherwise
        """
        return self.state.all_required_slots_filled()
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history.
        
        Returns:
            List of messages in the conversation
        """
        return self.state.get_history()
    
    async def save(self) -> bool:
        """Save slot filler state to persistent memory.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            conversation_states = self.memory.get("conversation_states", {})
            conversation_states[self.state.conversation_id] = self.state.to_dict()
            self.memory.set("conversation_states", conversation_states)
            return await self.memory.save()
        except Exception as e:
            logger.error(f"Error saving slot filler state: {e}")
            return False


class SlotFillerFactory:
    """Factory for creating SlotFiller instances with memory integration."""
    
    def __init__(self, memory: PersistentMemory):
        """Initialize factory.
        
        Args:
            memory: PersistentMemory instance for the user
        """
        self.memory = memory
    
    async def create_slot_filler(
        self, 
        conversation_id: str,
        required_slots: List[str] = [],
        optional_slots: List[str] = []
    ) -> SlotFiller:
        """Create a new slot filler for a conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            required_slots: List of required slot names
            optional_slots: List of optional slot names
            
        Returns:
            SlotFiller instance
        """
        # Check if state already exists for this conversation
        conversation_states = self.memory.get("conversation_states", {})
        state_dict = conversation_states.get(conversation_id)
        
        if state_dict:
            # Restore existing state
            state = ConversationState.from_dict(state_dict)
            logger.info(f"Restored existing state for conversation {conversation_id}")
        else:
            # Create new state
            state = ConversationState(conversation_id)
            state.set_required_slots(required_slots)
            state.set_optional_slots(optional_slots)
            logger.info(f"Created new state for conversation {conversation_id}")
        
        return SlotFiller(self.memory, state)