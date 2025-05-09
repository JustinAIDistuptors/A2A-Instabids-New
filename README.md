# InstaBids Google ADK

This repository contains InstaBids' implementation of the Google Agent Development Kit (ADK).

## Features

### Memory Persistence and Slot Filling Integration

The latest version includes memory persistence with Supabase, which enables maintaining user context across conversations:

- User preferences are automatically learned and stored in the database
- Conversation history is preserved for better context understanding
- Multi-modal inputs (text, images) are integrated in the memory model
- Slot filling framework for structured data collection with persistence

For more details, see the [Memory Integration Guide](docs/memory_integration.md).

### Vision 2.0 Integration

Includes Vision 2.0 integration, which enhances the platform with image analysis capabilities:

- Image analysis using OpenAI's GPT-4o Vision API
- Automatic extraction of project details from images
- Enhanced slot filling with vision-derived information
- Damage assessment detection and categorization

For more details, see the [Vision Integration Guide](docs/vision_integration.md).

## Vendor Namespace Approach

This package uses a vendor namespace approach (`instabids_google.adk`) instead of `google.adk` to avoid namespace collisions with existing Google packages in the Python environment.

### Why a Vendor Namespace?

Using a vendor namespace has several advantages:
- Avoids conflicts with existing Google packages
- Clearly indicates that this is InstaBids' implementation of the ADK
- Works reliably in all environments, regardless of what other packages are installed

## Installation

```bash
# Install from the repository
pip install -e .
```

## Environment Setup

To use the vision integration features, you need to set up your OpenAI API key:

```bash
export OPENAI_API_KEY=your_api_key_here
```

To use the memory persistence features, set up your Supabase credentials:

```bash
export SUPABASE_URL=your_supabase_url
export SUPABASE_SERVICE_ROLE=your_supabase_service_role_key
```

## Usage

### Basic Agent

```python
# Import the LlmAgent class
from instabids_google.adk import LlmAgent

# Create an agent
agent = LlmAgent("MyAgent", system_prompt="You are a helpful assistant.")

# Import tracing utilities
from instabids_google.adk import enable_tracing

# Enable tracing
enable_tracing(output="stdout")
```

### Memory-Enabled Homeowner Agent

```python
from supabase import create_client
from src.agents.homeowner_agent import HomeownerAgent

# Create a Supabase client
supabase = create_client("SUPABASE_URL", "SUPABASE_SERVICE_ROLE")

# Create the homeowner agent with memory persistence
agent = HomeownerAgent(supabase)

# The agent will automatically use persistent memory for slot filling
response = await agent.handle(message, handler)
print(response.text)
```

## Demo Applications

To test the memory and vision integration features:

```bash
python examples/memory_slot_filler_demo.py
```

## Testing

To verify that the package works correctly, run:

```bash
python -m pytest tests/unit
python -m pytest tests/integration
```

To test specific modules:

```bash
python -m pytest tests/test_memory/test_persistent_memory.py
python -m pytest tests/test_memory/test_conversation_state.py
python -m pytest tests/test_slot_filler/test_slot_filler_factory.py
python -m pytest tests/test_agents/test_memory_enabled_agent.py
```