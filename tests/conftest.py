"""Test fixtures for InstaBids tests."""
import pytest
from unittest.mock import MagicMock
from google.adk.memory import Memory

# Mock PersistentMemory for testing
class MockPersistentMemory(Memory):
    """In-memory implementation for testing."""
    
    def __init__(self):
        self._data = {}
        
    def get(self, key):
        return self._data.get(key)
        
    def set(self, key, value):
        self._data[key] = value
        
@pytest.fixture
def mock_memory():
    """Fixture to provide a mock memory instance."""
    return MockPersistentMemory()

@pytest.fixture
def mock_supabase():
    """Fixture to provide a mock Supabase client."""
    mock = MagicMock()
    # Add common mock behaviors needed across tests
    return mock
