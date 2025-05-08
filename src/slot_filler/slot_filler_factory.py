"""Factory to create and configure SlotFiller instances with memory integration."""

import logging
from typing import Dict, Any, List, Optional, Set

from src.memory.conversation_state import ConversationState
from src.memory.persistent_memory import PersistentMemory

logger = logging.getLogger(__name__)


class SlotFillerFactory:
    """Factory for creating and configuring slot fillers with memory integration."""

    def __init__(self, persistent_memory: PersistentMemory):
        """Initialize with persistent memory for storing slot state."""
        self.memory = persistent_memory

    async def create_slot_filler(
        self, conversation_id: str, required_slots: List[str], optional_slots: Optional[List[str]] = None
    ) -> "SlotFiller":
        """Create a slot filler with the specified required and optional slots."""
        # Create conversation state for tracking slot values
        state = ConversationState(self.memory, conversation_id)
        await state.load()

        # Configure slot requirements
        state.set_required_slots(required_slots)
        if optional_slots:
            state.set_optional_slots(optional_slots)

        # Create and return the slot filler
        return SlotFiller(state)


class SlotFiller:
    """Manages slot filling process with persistence and history tracking."""

    def __init__(self, state: ConversationState):
        """Initialize with conversation state for slot value persistence."""
        self.state = state
        self._on_slot_filled_callbacks = {}

    def get_slot(self, slot_name: str, default: Any = None) -> Any:
        """Get the value of a filled slot."""
        return self.state.get_slot(slot_name, default)

    def set_slot(self, slot_name: str, value: Any) -> None:
        """Set a slot value manually."""
        self.state.set_slot(slot_name, value)
        self._trigger_slot_filled_callback(slot_name, value)

    def clear_slot(self, slot_name: str) -> None:
        """Clear a slot value."""
        self.state.clear_slot(slot_name)

    def clear_all_slots(self) -> None:
        """Clear all slot values."""
        self.state.clear_all_slots()

    def has_slot(self, slot_name: str) -> bool:
        """Check if a slot has been filled."""
        return self.state.has_slot(slot_name)

    def get_missing_required_slots(self) -> List[str]:
        """Get list of required slots that haven't been filled."""
        return self.state.get_missing_required_slots()

    def all_required_slots_filled(self) -> bool:
        """Check if all required slots are filled."""
        return self.state.all_required_slots_filled()

    def get_filled_slots(self) -> Dict[str, Any]:
        """Get all filled slots."""
        return self.state.get_all_slots()

    def get_filled_required_slots(self) -> Dict[str, Any]:
        """Get all filled required slots."""
        return self.state.get_filled_required_slots()

    def register_slot_filled_callback(self, slot_name: str, callback) -> None:
        """Register a callback to be called when a specific slot is filled."""
        self._on_slot_filled_callbacks[slot_name] = callback

    def _trigger_slot_filled_callback(self, slot_name: str, value: Any) -> None:
        """Trigger the callback for a slot if one is registered."""
        if slot_name in self._on_slot_filled_callbacks:
            try:
                self._on_slot_filled_callbacks[slot_name](value)
            except Exception as e:
                logger.error(f"Error in slot filled callback for {slot_name}: {e}", exc_info=True)

    async def update_from_message(self, role: str, message: str, attachments: Optional[List[Dict]] = None) -> None:
        """Update conversation history with a new message."""
        self.state.add_to_history(role, message, attachments)
        await self.state.save()

    async def extract_slots_from_message(self, message: str, extractors: Dict[str, callable] = None) -> Dict[str, Any]:
        """Extract slot values from a message using provided extractors.
        
        Args:
            message: The message text to extract values from
            extractors: Dictionary mapping slot names to extractor functions
            
        Returns:
            Dictionary of slot name to extracted value
        """
        extracted_slots = {}
        
        if extractors:
            for slot_name, extractor in extractors.items():
                try:
                    value = extractor(message)
                    if value is not None:
                        self.set_slot(slot_name, value)
                        extracted_slots[slot_name] = value
                except Exception as e:
                    logger.error(f"Error extracting slot {slot_name}: {e}", exc_info=True)
        
        await self.state.save()
        return extracted_slots

    async def process_vision_inputs(self, image_data: Dict[str, Any], vision_extractors: Dict[str, callable] = None) -> Dict[str, Any]:
        """Extract slot values from image data using provided vision extractors.
        
        Args:
            image_data: Dictionary with image data including URL or content
            vision_extractors: Dictionary mapping slot names to vision extractor functions
            
        Returns:
            Dictionary of slot name to extracted value
        """
        extracted_slots = {}
        
        # Add the image to multi-modal context
        image_id = image_data.get("id", str(len(self.state._multi_modal_context) + 1))
        self.state.add_multi_modal_context(
            image_id, 
            "image", 
            image_data.get("url", ""),
            image_data.get("metadata", {})
        )
        
        # Extract slots from image if extractors provided
        if vision_extractors:
            for slot_name, extractor in vision_extractors.items():
                try:
                    value = extractor(image_data)
                    if value is not None:
                        self.set_slot(slot_name, value)
                        extracted_slots[slot_name] = value
                except Exception as e:
                    logger.error(f"Error extracting slot {slot_name} from image: {e}", exc_info=True)
        
        await self.state.save()
        return extracted_slots

    async def save(self) -> bool:
        """Save the current state to persistent memory."""
        return await self.state.save()

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation and slot state."""
        return self.state.get_state_summary()

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.state.get_history(limit)

    def get_history_as_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM context."""
        return self.state.get_history_as_messages(limit)