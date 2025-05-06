"""
Global pytest configuration for the InstaBids test suite.

This file contains common fixtures and configuration for all tests.
"""

import os
import pytest
import sys
from datetime import datetime

# Ensure the base directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Register custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test to run using asyncio")
    config.addinivalue_line("markers", "skip_llm: mark test to skip in CI non-LLM mode")

# Define a custom argument to skip LLM tests
def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        "--skip-llm",
        action="store_true",
        help="Skip tests that require LLM interaction",
    )

def pytest_collection_modifyitems(config, items):
    """Modify collected test items based on command-line options."""
    if config.getoption("--skip-llm"):
        skip_llm = pytest.mark.skip(reason="LLM tests skipped with --skip-llm option")
        for item in items:
            # Skip any test with "llm" in the name
            if "llm" in item.name.lower():
                item.add_marker(skip_llm)
