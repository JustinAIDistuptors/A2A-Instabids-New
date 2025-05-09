"""Conversation state management for InstaBids agents."""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class ConversationState:
    """Store conversation state including history, slots, and metadata."""
    user_id: str
    project_id: Optional[str] = None
    
    # Message history as a list of dicts with {role, content}
    history: List[Dict[str, str]] = field(default_factory=list)
    
    # Slot values collected through the conversation
    slots: Dict[str, Any] = field(default_factory=dict)
    
    # Vision context from image analysis (labels, embeddings, etc.)
    vision_context: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: Message role (user or assistant)
            content: Message content
        """
        self.history.append({"role": role, "content": content})
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history.
        
        Args:
            content: User message content
        """
        self.add_message("user", content)
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation history.
        
        Args:
            content: Assistant message content
        """
        self.add_message("assistant", content)
    
    def set_slot(self, slot_name: str, value: Any) -> None:
        """Set a slot value.
        
        Args:
            slot_name: Slot name
            value: Slot value
        """
        self.slots[slot_name] = value
    
    def get_slot(self, slot_name: str, default: Any = None) -> Any:
        """Get a slot value.
        
        Args:
            slot_name: Slot name
            default: Default value if slot not found
            
        Returns:
            Slot value or default if not found
        """
        return self.slots.get(slot_name, default)
    
    def set_vision_data(self, image_id: str, metadata: Dict[str, Any]) -> None:
        """Set vision data for an image.
        
        Args:
            image_id: Image identifier
            metadata: Vision metadata (labels, embeddings, etc.)
        """
        if not self.vision_context:
            self.vision_context = {}
        self.vision_context[image_id] = metadata
    
    def get_vision_labels(self) -> List[str]:
        """Get all vision labels from analyzed images.
        
        Returns:
            List of unique labels from all analyzed images
        """
        all_labels = []
        for metadata in self.vision_context.values():
            if "labels" in metadata and isinstance(metadata["labels"], list):
                all_labels.extend(metadata["labels"])
        return list(set(all_labels))
