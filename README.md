# InstaBids - BidCard Memory Integration

This branch integrates the BidCard v2 feature with the Persistent Memory functionality to provide enhanced user experiences through preference-based personalization.

## Features

- Personalized BidCard generation using user preferences
- Tracking of user interactions with BidCards
- Preference learning from BidCard creation and updates
- Enhanced API endpoints with memory integration
- Comprehensive test suite

## Key Components

- `memory/bidcard_memory_integration.py` - Core integration module
- `instabids/agents/bidcard_agent.py` - Enhanced BidCard agent with memory
- `instabids/api/routes/bidcard.py` - Memory-integrated API routes

## Database Requirements

This integration uses the memory schema which includes:

- `user_memories` - Primary memory storage
- `user_preferences` - User preferences with confidence scores
- `user_memory_interactions` - Detailed interaction history

Make sure these tables exist in your Supabase database before deploying.

## Getting Started

1. Clone the repository
2. Create a `.env` file with Supabase credentials
3. Install dependencies: `pip install -e .`
4. Run tests: `pytest tests/unit/test_bidcard_memory_integration.py`

## Architecture

The memory integration follows a layered approach:

1. **Core Memory Layer**: `PersistentMemory` class for CRUD operations on memory
2. **Integration Layer**: `bidcard_memory_integration.py` bridging BidCard and memory
3. **Application Layer**: Enhanced BidCard agent and API routes

## Usage Examples

### Creating a BidCard with Memory

```python
from memory.bidcard_memory_integration import create_bid_card_with_memory
from memory.persistent_memory import PersistentMemory

# Initialize memory
memory = PersistentMemory(supabase_client, user_id)
await memory.load()

# Create bid card with memory integration
card, confidence = await create_bid_card_with_memory(
    project_data, 
    vision_data, 
    memory, 
    user_id
)
```

### Using Preferences

```python
# Get user preferences
preferences = memory.get_all_preferences()

# Check for specific preference
preferred_category = memory.get_preference("preferred_project_categories")
if preferred_category:
    print(f"User prefers {preferred_category} projects")
```

## Testing

- Unit tests: `pytest tests/unit/test_bidcard_memory_integration.py`
- Integration tests: `pytest tests/integration/test_bidcard_memory_integration_e2e.py`

## Documentation

For detailed information about the integration architecture and implementation, see the [BidCard Memory Integration](docs/bidcard_memory_integration.md) documentation.

## Future Enhancements

- Multi-modal memory integration for vision, text, and voice
- Advanced preference learning algorithms
- Time-decay for preference confidence
- Cross-project preference analysis