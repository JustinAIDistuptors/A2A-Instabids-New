# Vision 2.0 Integration Guide

## Overview

The Vision 2.0 feature enhances the InstaBids platform by integrating OpenAI's GPT-4o Vision API to analyze images uploaded by homeowners. This integration extracts structured information from photos, such as damage assessments, construction elements, and project types. The enhanced slot filler then uses this extracted information to automatically populate relevant project details.

## Key Components

### 1. Vision Tool Plus

The core vision analysis functionality is implemented in `src/instabids/tools/vision_tool_plus.py`. This module provides:

- **analyse(image_path)**: Analyzes a single image and extracts structured data including labels, descriptions, and damage assessments.
- **batch_analyse(image_paths)**: Processes multiple images in a batch.
- **validate_image_for_bid_card(image_path)**: Validates if an image is suitable for a bid card and returns extracted information.

### 2. Enhanced Slot Filler

The standard slot filler has been enhanced in `src/instabids/agents/slot_filler.py` to support vision integration:

- **process_image_for_slots(image_path)**: Processes an image to extract slot values where possible.
- **update_card_from_images(card, image_paths)**: Updates a card with information extracted from multiple images.

The slot definition now includes mapping to vision fields:

```python
SLOTS = {
    "category": {
        "q": "What category best fits this project?",
        "options": ["repair", "renovation", "installation", "maintenance", "construction", "other"],
        "vision_field": "labels"  # Field from vision analysis to use for this slot
    },
    # ...
}
```

### 3. Base64 Helpers

Utility functions for working with base64-encoded images are provided in `src/instabids/tools/base64_helpers.py`:

- **encode_image_file(image_path)**: Encodes an image file to a base64 string.
- **decode_base64(base64_string)**: Decodes a base64 string to binary data.
- **save_base64_to_file(base64_string, output_path)**: Saves a base64 encoded string to a file.
- **get_data_uri(base64_string, mime_type)**: Creates a data URI from a base64 string.

### 4. Homeowner Agent Integration

The `src/instabids/agents/homeowner_agent.py` has been updated to use the vision-enhanced slot filler:

- Vision analysis is performed on uploaded images.
- Extracted information is used to populate card fields automatically.
- Damage assessments are stored in project notes.

## Usage Examples

### Processing Images in Homeowner Agent

```python
async def process_input(self, user_id: str, image_paths: List[Path] | None = None, ...):
    # Build bid_card from existing data
    bid_card = {...}
    
    # Process images if provided
    if image_paths:
        bid_card = await update_card_from_images(bid_card, [str(path) for path in image_paths])
```

### Manually Analyzing an Image

```python
from instabids.tools.vision_tool_plus import analyse

async def analyze_project_image(image_path: str):
    analysis = await analyse(image_path)
    print(f"Labels: {analysis['labels']}")
    print(f"Description: {analysis['description']}")
    print(f"Damage assessment: {analysis['damage_assessment']}")
```

### Extracting Slot Values from Images

```python
from instabids.agents.slot_filler import process_image_for_slots

async def extract_slot_values(image_path: str):
    extracted = await process_image_for_slots(image_path)
    if "category" in extracted:
        print(f"Detected category: {extracted['category']}")
    if "job_type" in extracted:
        print(f"Detected job type: {extracted['job_type']}")
    if "damage_assessment" in extracted:
        print(f"Damage assessment: {extracted['damage_assessment']}")
```

## Environment Setup

To use the vision integration, the following environment variable must be set:

```
OPENAI_API_KEY=your_api_key_here
```

The API key should have access to the `gpt-4o-vision-preview` model.

## Demo Application

A demonstration application is provided in `examples/vision_slot_filler_demo.py`. This script shows how to use the vision-enhanced slot filler in an interactive session.

To run the demo:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here

# Run the demo with one or more images
python examples/vision_slot_filler_demo.py path/to/image1.jpg path/to/image2.jpg
```

## Testing

Comprehensive tests are included for each component:

- Unit tests for `vision_tool_plus.py` and `base64_helpers.py`
- Integration tests for the slot filler with vision integration
- End-to-end tests for the homeowner agent with image processing

To run the tests:

```bash
python -m pytest tests/unit/test_vision_tool_plus.py
python -m pytest tests/unit/test_base64_helpers.py
python -m pytest tests/unit/test_vision_slot_filler.py
python -m pytest tests/integration/test_vision_integration.py
```

## Security Considerations

- The OpenAI API key is loaded from environment variables to avoid hardcoding in source code.
- Images are processed locally and only the base64-encoded version is sent to the OpenAI API.
- User uploads should be validated for file type and size before processing.

## Performance Optimization

- For batch processing of multiple images, use `batch_analyse()` which processes images in parallel.
- Cache vision analysis results when possible to avoid redundant API calls.
- Consider implementing background processing for large images or many uploads.

## Future Enhancements

- Support for additional vision models (Google Vision API, Azure Computer Vision)
- Enhanced damage classification with severity ratings
- Material identification and cost estimation
- Automatic project scope generation based on image analysis