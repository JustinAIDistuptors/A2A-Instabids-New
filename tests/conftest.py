"""
Pytest configuration file for tests.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the parent directory to sys.path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add mock modules
mock_path = str(Path(__file__).parent / "mocks")
sys.path.insert(0, mock_path)

# Import the mock
from tests.mocks.google_adk_mock import LlmAgent, enable_tracing, AgentMessage, UserMessage, Memory

# Create a module for google.adk if it doesn't exist
if "google" not in sys.modules:
    sys.modules["google"] = MagicMock()
if "google.adk" not in sys.modules:
    sys.modules["google.adk"] = MagicMock()

# Set up the mock
sys.modules["google.adk"].LlmAgent = LlmAgent
sys.modules["google.adk"].enable_tracing = enable_tracing
sys.modules["google.adk"].AgentMessage = AgentMessage
sys.modules["google.adk"].UserMessage = UserMessage

# Create memory module
memory_module = MagicMock()
memory_module.Memory = Memory
sys.modules["google.adk.memory"] = memory_module

# Set up environmental variables for testing
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "example-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "example-service-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-example-key")


# Mock the supabase client
@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("supabase.create_client") as mock_create_client:
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        yield mock_client


# Mock persistent memory
@pytest.fixture
def mock_memory():
    """Mock persistent memory."""
    with patch("memory.persistent_memory.PersistentMemory") as mock_memory_cls:
        mock_memory = MagicMock()
        mock_memory_cls.return_value = mock_memory
        yield mock_memory


# Mock the OpenAI API
@pytest.fixture
def mock_openai():
    """Mock OpenAI API."""
    with patch("openai.Audio.atranscribe") as mock_transcribe:
        mock_transcribe.return_value = {
            "text": "This is a mock transcription",
            "avg_logprob": -0.5,  # High confidence
        }
        yield mock_transcribe
