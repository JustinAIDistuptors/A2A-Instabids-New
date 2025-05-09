# InstaBids Memory Module

## Overview

The Memory module provides persistent storage capabilities for InstaBids agents, storing user preferences, conversation contexts, multi-modal inputs, and agent-to-agent communication history. It is designed to work with Supabase as a backend storage provider.

## Key Components

### IntegratedMemory

The `IntegratedMemory` class is the core of the memory system. It combines:

1. **Conversation State Tracking**: Tracks the state of a conversation, including filled slots, required slots, and multi-modal inputs.
2. **Persistent Memory Storage**: Stores memory data in a Supabase database.
3. **User Preference Learning**: Extracts and updates user preferences based on interactions.
4. **A2A Communication History**: Records and retrieves messages exchanged between agents.

This class implements the Google ADK `Memory` interface, making it compatible with ADK-based agents.

### MemoryManager

The `MemoryManager` class provides a simplified interface to the memory system, handling:

1. **Database Connection**: Connects to the Supabase database using environment variables.
2. **Memory Instance Management**: Creates, caches, and retrieves memory instances for different users.
3. **Direct Database Access**: Provides methods to access the database directly for common operations.

A singleton instance `memory_manager` is exported for easy access throughout the application.

## Database Schema

The memory system relies on the following database tables:

1. `user_memories`: Stores the complete memory state for each user.
2. `user_memory_interactions`: Records specific interactions for tracking user behavior.
3. `user_preferences`: Stores extracted user preferences with confidence scores.
4. `agent_messages`: Records messages exchanged between agents.
5. `message_routing_logs`: Tracks message routing events.
6. `agent_routing`: Stores information about available agents and their capabilities.

## Usage Examples

### Initializing Memory

```python
from src.memory import memory_manager

# Get memory for a specific user
user_id = "user-123"
memory = await memory_manager.get_user_memory(user_id)
```

### Conversation State Tracking

```python
# Add message to history
memory.add_message("user", "I want to remodel my bathroom")

# Add multi-modal input
image_data = {"url": "https://example.com/bathroom.jpg", "width": 800, "height": 600}
memory.add_multi_modal_input("image-1", "image", image_data)

# Set required slots
memory.set_required_slots(["project_type", "budget", "timeline"])

# Fill slots
memory.set_slot("project_type", "bathroom_remodel")
memory.set_slot("budget", "15000")

# Check if all required slots are filled
if not memory.all_required_slots_filled():
    missing_slots = memory.get_missing_required_slots()
    print(f"Missing information: {missing_slots}")
```

### User Preferences and Interactions

```python
# Record an interaction
interaction_data = {
    "project_type": "bathroom_remodel",
    "budget": "15000",
    "timeline": "3_months"
}
await memory.add_interaction("project_creation", interaction_data)

# Get learned preferences
preferences = memory.get_all_preferences()
preferred_project_type = memory.get_preference("preferred_project_types")
```

### A2A Communication

```python
from src.a2a_types.core import Agent

# Record a message exchange between agents
await memory.record_agent_message(
    message_id="msg-123",
    task_id="task-456",
    sender_agent_id="agent-1",
    recipient_agent_id="agent-2",
    content="How should we handle this bathroom remodel project?",
    role="assistant"
)

# Record the routing event
await memory.record_message_routing(
    message_id="msg-123",
    task_id="task-456",
    sender_agent_id="agent-1",
    recipient_agent_id="agent-2",
    route_status="delivered"
)

# Get messages for a specific task
messages = await memory_manager.get_agent_messages(task_id="task-456")
```

### Persisting Memory Changes

```python
# Save changes to database
await memory.save()

# Alternatively, save all active memory instances
await memory_manager.save_all()
```

## Environment Variables

The memory system requires the following environment variables:

- `SUPABASE_URL`: URL of the Supabase instance
- `SUPABASE_KEY`: API key for the Supabase instance (service role key recommended)

## Testing

Unit tests are available in `tests/unit/test_integrated_memory.py`. Integration tests require a live Supabase instance and are available in `tests/integration/test_memory_integration.py`.

To run the tests:

```bash
# Unit tests
python -m pytest tests/unit/test_integrated_memory.py -v

# Integration tests (requires Supabase credentials)
python -m pytest tests/integration/test_memory_integration.py -v
```
