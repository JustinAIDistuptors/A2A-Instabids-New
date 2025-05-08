"""
Simple in-memory conversation state for slot-filling dialogs.
"""
from typing import Dict, Any, Optional, Set


class ConversationState:
    """In-memory conversation state for slot-filling dialogs."""
    
    def __init__(self, memory: Optional[Dict[str, Any]] = None):
        """
        Initialize conversation state.
        
        Args:
            memory: Optional initial state
        """
        self.slots: Dict[str, Any] = memory or {}
        
    def set_slot(self, key: str, value: Any) -> None:
        """
        Set a slot value.
        
        Args:
            key: Slot name
            value: Slot value
        """
        self.slots[key] = value
        
    def get_slot(self, key: str, default: Any = None) -> Any:
        """
        Get a slot value.
        
        Args:
            key: Slot name
            default: Default value if slot is not set
            
        Returns:
            Slot value or default
        """
        return self.slots.get(key, default)
        
    def get_slots(self) -> Dict[str, Any]:
        """
        Get all slots.
        
        Returns:
            Dictionary of all slots
        """
        return self.slots.copy()
        
    def clear_slots(self) -> None:
        """Clear all slots."""
        self.slots.clear()
        
    def clear_slot(self, key: str) -> None:
        """
        Clear a specific slot.
        
        Args:
            key: Slot name
        """
        if key in self.slots:
            del self.slots[key]
            
    def has_slot(self, key: str) -> bool:
        """
        Check if a slot is set.
        
        Args:
            key: Slot name
            
        Returns:
            True if slot is set, False otherwise
        """
        return key in self.slots
        
    def missing_slots(self, required: Set[str]) -> Set[str]:
        """
        Get missing required slots.
        
        Args:
            required: Set of required slot names
            
        Returns:
            Set of missing slot names
        """
        return required - set(self.slots.keys())
