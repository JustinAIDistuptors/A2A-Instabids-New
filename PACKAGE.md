# InstaBids Google ADK Package

This document explains the package structure and how to use the InstaBids Google ADK package.

## Package Structure

The package is structured as follows:

```
instabids_google/
├── __init__.py
└── adk/
    ├── __init__.py
    ├── llm_agent.py
    └── tracing.py
```

## Installation

To install the package in development mode:

```bash
pip install -e .
```

## Usage

Import the package components as follows:

```python
from instabids_google.adk import LlmAgent, enable_tracing

# Create an agent
agent = LlmAgent(
    name="MyAgent",
    system_prompt="You are a helpful assistant.",
    tools=[],
    memory=None
)

# Enable tracing
enable_tracing("stdout")
```

## Why This Approach?

We're using a vendor namespace (`instabids_google.adk`) instead of `google.adk` to avoid namespace collisions with other Google packages that might be installed in the Python environment. This ensures that our package will work correctly in all environments, regardless of what other packages are installed.

## Testing

To verify that the package is correctly installed and imports work, run:

```bash
python test_imports.py
```

If everything is set up correctly, you should see:

```
Testing imports...
✅ Successfully imported LlmAgent
✅ Successfully imported enable_tracing
✅ Successfully created an LlmAgent instance: TestAgent

All imports and basic functionality tests passed!
```