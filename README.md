# InstaBids Google ADK

This repository contains InstaBids' implementation of the Google Agent Development Kit (ADK).

## Features

### Vision 2.0 Integration

The latest version includes Vision 2.0 integration, which enhances the platform with image analysis capabilities:

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

### Vision-Enhanced Homeowner Agent

```python
from instabids.agents.homeowner_agent import HomeownerAgent
from pathlib import Path

# Create the homeowner agent
agent = HomeownerAgent()

# Process input with images
result = await agent.process_input(
    user_id="user123",
    description="I need to fix my leaking roof",
    image_paths=[Path("path/to/roof_image.jpg")]
)

# Check if more information is needed
if result["need_more"]:
    print(f"Need more info: {result['follow_up']}")
else:
    print(f"Project created with ID: {result['project_id']}")
```

## Demo Applications

To test the vision integration features, try the demo application:

```bash
python examples/vision_slot_filler_demo.py path/to/image.jpg
```

## Testing

To verify that the package works correctly, run:

```bash
python -m pytest tests/unit
python -m pytest tests/integration
```

To test specific modules:

```bash
python -m pytest tests/unit/test_vision_tool_plus.py
python -m pytest tests/unit/test_vision_slot_filler.py
```