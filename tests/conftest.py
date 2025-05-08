"""
Global test configuration and fixtures for pytest.
"""
import sys
from pathlib import Path
import pytest

# Add mock directories to sys.path
MOCK_DIR = Path(__file__).parent / "mocks"
sys.path.insert(0, str(MOCK_DIR))

# Set up mock for google.adk module
sys.modules["google.adk"] = __import__("google_adk_mock")
sys.modules["google.adk.messages"] = __import__("google_adk_mock")

# Add any pytest fixtures here
@pytest.fixture
def mock_supabase():
    """Return a mock supabase client."""
    from supabase_mock import SupabaseMock
    return SupabaseMock()
