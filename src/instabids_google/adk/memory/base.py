"""
Base memory implementation for agent persistence.
This module provides the base Memory class that all memory implementations should extend.
"""
from typing import Dict, Any, Optional, List
import logging
from abc import ABC, abstractmethod

# Set up logging
logger = logging.getLogger(__name__)


class Memory(ABC):
    """
    Abstract base class for agent memory implementations.
    
    This class defines the interface that all memory implementations must implement.
    """
    
    def __init__(self):
        """Initialize the memory system."""
        pass
    
    @abstractmethod
    async def load(self) -> bool:
        """
        Load memory from storage.
        
        Returns:
            bool: True if memory was successfully loaded, False otherwise
        """
        pass
    
    @abstractmethod
    async def save(self) -> bool:
        """
        Save memory to storage.
        
        Returns:
            bool: True if memory was successfully saved, False otherwise
        """
        pass
    
    @abstractmethod
    def add_interaction(self, interaction_type: str, data: Dict[str, Any]) -> None:
        """
        Add a user interaction to memory.
        
        Args:
            interaction_type: Type of interaction (e.g., 'message', 'tool_call')
            data: Interaction data
        """
        pass
    
    @abstractmethod
    def set_preference(self, preference_key: str, value: Any, confidence: float = 1.0) -> None:
        """
        Set a learned user preference with confidence level.
        
        Args:
            preference_key: Key for the preference
            value: Value of the preference
            confidence: Confidence level (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def set_context(self, key: str, value: Any) -> None:
        """
        Set a context value in memory.
        
        Args:
            key: Context key
            value: Context value
        """
        pass
    
    @abstractmethod
    def get_recent_interactions(self, interaction_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get recent user interactions, optionally filtered by type.
        
        Args:
            interaction_type: Optional type to filter by
            limit: Maximum number of interactions to return
            
        Returns:
            List of interaction dictionaries
        """
        pass
    
    @abstractmethod
    def get_preference(self, preference_key: str) -> Any:
        """
        Get a learned user preference.
        
        Args:
            preference_key: Key for the preference
            
        Returns:
            The preference value, or None if not found
        """
        pass
    
    @abstractmethod
    def get_all_preferences(self) -> Dict[str, Any]:
        """
        Get all learned preferences with their values.
        
        Returns:
            Dictionary of preference keys to values
        """
        pass