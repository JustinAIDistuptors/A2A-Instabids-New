# InstaBids Google ADK

This repository contains InstaBids' implementation of the Google Agent Development Kit (ADK).

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

## Usage

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

## Testing

To verify that the package works correctly, run:

```bash
python test_imports.py
```

This will test importing the key components and creating an agent instance.