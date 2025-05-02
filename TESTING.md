# Testing the Package Structure

This document provides instructions for testing the package structure to ensure imports work correctly.

## Testing Import Functionality

After restructuring the package, it's important to verify that imports work as expected. You can use the provided `test_imports.py` script to check if the package structure is correctly set up.

### Running the Test Script

To run the test script:

```bash
# From the repository root directory
python test_imports.py
```

If the package structure is correctly set up, you should see output similar to:

```
Testing imports...
✅ Successfully imported LlmAgent
✅ Successfully imported enable_tracing
✅ Successfully created an LlmAgent instance: TestAgent
✅ Successfully called enable_tracing

All imports and basic functionality tests passed!
```

### Manual Testing

You can also test the imports manually in a Python interpreter:

```python
# Start Python interpreter
python

# Try importing from the package
from google.adk import LlmAgent
from google.adk import enable_tracing

# If no errors occur, the package structure is correct
```

## Installing the Package in Development Mode

For development, you can install the package in editable mode:

```bash
pip install -e .
```

This will install the package while allowing you to make changes to the code without needing to reinstall.

## Troubleshooting

If you encounter import errors:

1. Make sure you're running the script from the repository root directory
2. Verify that all `__init__.py` files are present in the package directories
3. Check that `setup.py` includes the correct package configuration
4. Try installing the package in development mode as described above