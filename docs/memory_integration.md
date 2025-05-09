# Memory Integration Guide

## Overview

The Memory Integration module provides persistent memory capabilities for InstaBids agents. This system enables agents to:

1. Maintain context across multiple conversations
2. Learn user preferences automatically
3. Store and retrieve slot values for structured data collection
4. Remember conversation history with support for multi-modal inputs

## Architecture

The memory system consists of several components:

### PersistentMemory

The core class that manages memory persistence using Supabase as the backend storage:

- Implements the ADK Memory interface
- Provides async methods for loading/saving memory state
- Tracks user preferences and interaction history
- Handles memory caching for performance
- Automatically converts between string and UUID formats for user IDs

### ConversationState

Manages the state of individual conversations, including:

- Slot tracking (required and optional slots)
- Conversation history with multi-modal support
- Integration with PersistentMemory for persistence

### SlotFillerFactory

Factory class for creating slot fillers with memory integration:

- Creates new slot fillers with persistent memory
- Configures slot requirements and validation
- Manages slot filler instances across conversations

### SlotFiller

Manages the slot filling process with memory integration:

- Extracts slot values from text and images
- Tracks filled slots and validates requirements
- Provides callbacks when specific slots are filled
- Integrates with ConversationState for persistence

### MemoryEnabledAgent

Base agent class with memory and slot filling capabilities:

- Manages memory instances for each user
- Provides methods for processing messages with memory
- Handles slot filling with text and vision inputs
- Exposes an extensible architecture for derived agents

## Database Schema

The memory system uses the existing Supabase tables:

### user_memories

Stores the complete memory state for each user:

- `user_id` (primary key, UUID): Unique identifier for the user
- `memory_data` (JSONB): Complete memory state including context, preferences, and interaction history
- `created_at` (timestamp): When the memory was first created
- `updated_at` (timestamp): When the memory was last updated

### user_memory_interactions

Detailed log of user interactions for analytics:

- `id` (UUID): Unique identifier for the interaction
- `user_id` (UUID): Reference to the user
- `interaction_type`: Type of interaction (e.g., "project_creation", "conversation")
- `interaction_data` (JSONB): Data associated with the interaction
- `created_at` (timestamp): When the interaction occurred

### user_preferences

Extracted user preferences with confidence scores:

- `id` (UUID): Unique identifier for the preference
- `user_id` (UUID): Reference to the user
- `preference_key`: Key identifying the preference (e.g., "preferred_project_types")
- `preference_value` (JSONB): Value of the preference
- `confidence` (float): Confidence score (0-1) for the preference
- `source`: Source of the preference (e.g., "project_creation")
- `created_at` / `updated_at` (timestamp): Creation/update timestamps

## Usage Examples

### Basic Memory Usage

```python
from supabase import create_client
from src.memory.persistent_memory import PersistentMemory

# Create Supabase client
supabase = create_client("SUPABASE_URL", "SUPABASE_KEY")

# Create memory instance for a user
# Note: user_id must be a valid UUID format
memory = PersistentMemory(supabase, "550e8400-e29b-41d4-a716-446655440000")

# Load memory
await memory.load()

# Access stored values
user_name = memory.get("user_name")

# Store new values
memory.set("last_project", "bathroom")

# Save changes
await memory.save()

# Record an interaction
await memory.add_interaction(
    "project_creation",
    {
        "project_type": "bathroom",
        "timeline": "1-3 months",
        "budget": "$5,000-$15,000"
    }
)

# Get learned preferences
preferred_project_types = memory.get_preference("preferred_project_types")
```

### Slot Filling with Memory

```python
from supabase import create_client
from src.memory.persistent_memory import PersistentMemory
from src.slot_filler.slot_filler_factory import SlotFillerFactory

# Create Supabase client
supabase = create_client("SUPABASE_URL", "SUPABASE_KEY")

# Create memory instance
# Note: user_id must be a valid UUID format
memory = PersistentMemory(supabase, "550e8400-e29b-41d4-a716-446655440000")
await memory.load()

# Create slot filler factory
factory = SlotFillerFactory(memory)

# Create a slot filler with required and optional slots
slot_filler = await factory.create_slot_filler(
    "conversation123",
    ["location", "project_type"],  # Required slots
    ["timeline", "budget"]  # Optional slots
)

# Update from user message
await slot_filler.update_from_message(
    "user", "I need a bathroom renovation in Denver"
)

# Extract slots with custom extractors
extracted = await slot_filler.extract_slots_from_message(
    "I need a bathroom renovation in Denver",
    {
        "location": location_extractor,
        "project_type": project_type_extractor
    }
)

# Check if all required slots are filled
if slot_filler.all_required_slots_filled():
    print("All required slots filled!")
    print(f"Slots: {slot_filler.get_filled_slots()}")
else:
    print(f"Missing slots: {slot_filler.get_missing_required_slots()}")

# Save state to database
await slot_filler.save()
```

### Creating a Memory-Enabled Agent

```python
from supabase import create_client
from src.agents.memory_enabled_agent import MemoryEnabledAgent
from google.adk.conversation import Message, Response

class MyCustomAgent(MemoryEnabledAgent):
    def __init__(self, db):
        super().__init__(db)
        
    async def _process_message_with_memory(self, message, user_id, conversation_id):
        # Process with slot filling
        slot_result = await self._process_with_slot_filling(
            message,
            user_id,
            conversation_id,
            ["location", "project_type"],  # Required slots
            ["timeline", "budget"],        # Optional slots
            {
                "location": self._extract_location,
                "project_type": self._extract_project_type
            },  # Text extractors
            {
                "project_type": self._extract_project_type_from_image
            }   # Vision extractors
        )
        
        # Generate response based on slot state
        if slot_result["all_required_slots_filled"]:
            return f"Thanks! I'll help with your {slot_result['filled_slots']['project_type']} project in {slot_result['filled_slots']['location']}"
        else:
            return f"I need more information: {slot_result['missing_slots']}"
            
    def _extract_location(self, text):
        # Custom location extraction logic
        return "Denver" if "Denver" in text else None
```

## Integration with Vision Features

The memory system integrates seamlessly with vision features:

```python
# Process vision inputs
image_data = {
    "id": "img123",
    "url": "https://example.com/bathroom.jpg",
    "metadata": {"width": 800, "height": 600}
}

# Extract slots from image
extracted = await slot_filler.process_vision_inputs(
    image_data,
    {
        "project_type": extract_project_type_from_image,
        "style_preference": extract_style_from_image
    }
)

# Image is automatically added to multi-modal context
multi_modal_context = slot_filler.state.get_multi_modal_context()
```

## Best Practices

### Memory Usage

- Always use `await memory.load()` before accessing memory
- Use `memory.add_interaction()` to record significant user interactions
- Call `await memory.save()` after making changes to ensure persistence
- Use the preference learning system to track user preferences over time
- Always use valid UUID format for user IDs, as the database uses UUID type

### Slot Filling

- Define required and optional slots clearly
- Implement robust extractors for each slot type
- Register callbacks for handling when specific slots are filled
- Save slot state after each meaningful interaction
- Use vision extractors to enhance slot filling with image analysis

### Agent Implementation

- Extend the `MemoryEnabledAgent` class for consistent memory handling
- Override `_process_message_with_memory()` to implement custom logic
- Use the `_process_with_slot_filling()` method for structured data collection
- Handle missing slots gracefully with informative prompts
- Generate responses based on filled slots and conversation context

## Performance Considerations

- The memory system uses in-memory caching to minimize database access
- Only changed data is saved to the database (dirty tracking)
- Conversation history is stored efficiently with optional limits
- Consider pruning old interactions periodically for long-running systems
- Use batch operations when processing multiple users or conversations

## Security

- Supabase Row Level Security (RLS) is configured to restrict access by user_id
- Use service roles for agent access to the database
- Never expose API keys or service tokens in client-side code
- Sanitize any user inputs before storing in the database
- Implement rate limiting to prevent abuse of memory features