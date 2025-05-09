#!/usr/bin/env python
"""
Conversation state management with persistent memory support.

This module handles conversation state tracking, including multi-modal inputs and slot filling.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Set

# Set up logging
logger = logging.getLogger(__name__)


class ConversationState:
    """Manages the state of a conversation with memory persistence.
    
    Tracks conversation history, filled slots, and multi-modal contexts.
    """
    
    def __init__(self, conversation_id: str):
        """Initialize conversation state.
        
        Args:
            conversation_id: Unique identifier for the conversation
        """
        self.conversation_id = conversation_id
        self.history = []
        self.slots = {}
        self.required_slots = set()
        self.optional_slots = set()
        self.multi_modal_context = {}
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: Role of the sender (e.g., "user", "assistant")
            content: Message content
        """
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": None  # Will be filled when persisted
        })
    
    def add_multi_modal_input(self, input_id: str, input_type: str, data: Dict[str, Any]) -> None:
        """Add a multi-modal input to the conversation context.
        
        Args:
            input_id: Unique identifier for the input
            input_type: Type of input (e.g., "image", "audio")
            data: Input data including URL, metadata, etc.
        """
        self.multi_modal_context[input_id] = {
            "type": input_type,
            "data": data
        }
    
    def set_required_slots(self, slots: List[str]) -> None:
        """Set the required slots for this conversation.
        
        Args:
            slots: List of required slot names
        """
        self.required_slots = set(slots)
    
    def set_optional_slots(self, slots: List[str]) -> None:
        """Set the optional slots for this conversation.
        
        Args:
            slots: List of optional slot names
        """
        self.optional_slots = set(slots)
    
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for persistence.
        
        Returns:
            Dictionary representation of the state
        """
        return {
            "conversation_id": self.conversation_id,
            "history": self.history,
            "slots": self.slots,
            "required_slots": list(self.required_slots),
            "optional_slots": list(self.optional_slots),
            "multi_modal_context": self.multi_modal_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create state from dictionary.
        
        Args:
            data: Dictionary representation of state
            
        Returns:
            ConversationState instance
        """
        state = cls(data.get("conversation_id", str(uuid.uuid4())))
        state.history = data.get("history", [])
        state.slots = data.get("slots", {})
        state.required_slots = set(data.get("required_slots", []))
        state.optional_slots = set(data.get("optional_slots", []))
        state.multi_modal_context = data.get("multi_modal_context", {})
        return state