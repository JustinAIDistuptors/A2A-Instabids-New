"""
Configuration for pytest

This module sets up the test environment for pytest, including:
- Loading environment variables from .env.test if available
- Setting up mock services for CI
- Providing fixtures for common test needs
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import patch
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load test environment variables if available
if os.path.exists(".env.test"):
    load_dotenv(".env.test")
else:
    load_dotenv()

# Check if we should use mock services
MOCK_SERVICES = os.environ.get("MOCK_SERVICES", "false").lower() in ["true", "1", "yes"]

# Set up CI compatibility for pytest-asyncio
if os.environ.get("CI") or MOCK_SERVICES:
    # Use pytest-asyncio fixtures
    @pytest.fixture(scope="session")
    def event_loop():
        """Create an event loop for the session."""
        try:
            loop = asyncio.get_event_loop_policy().new_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        yield loop
        loop.close()


@pytest.fixture(autouse=True)
def mock_services():
    """
    Mock external services in tests.
    
    This fixture is applied to all tests automatically and mocks external services
    if MOCK_SERVICES is True.
    """
    if MOCK_SERVICES:
        # Mock Supabase API calls if needed
        from unittest.mock import patch, MagicMock, AsyncMock
        
        # Create a dummy Supabase client
        mock_client = MagicMock()
        
        # Mock the table method
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock the execute method
        mock_execute = MagicMock()
        mock_execute.data = [{"id": "mock-id"}]
        
        # Mock the chain of methods
        mock_table.insert.return_value.execute.return_value = mock_execute
        mock_table.select.return_value.execute.return_value = mock_execute
        mock_table.update.return_value.execute.return_value = mock_execute
        mock_table.delete.return_value.execute.return_value = mock_execute
        
        # Allow chaining of methods
        for method in ["select", "insert", "update", "delete", "eq", "in_", "gt", "lt", "is_", "neq"]:
            mock_method = MagicMock()
            mock_method.execute.return_value = mock_execute
            
            # Allow further chaining
            for submethod in ["eq", "in_", "gt", "lt", "is_", "neq"]:
                sub_mock = MagicMock()
                sub_mock.execute.return_value = mock_execute
                
                # Create a closure to capture sub_mock for each submethod
                def create_submock_wrapper(submock):
                    def wrapper(*args, **kwargs):
                        return submock
                    return wrapper
                
                setattr(mock_method, submethod, create_submock_wrapper(sub_mock))
            
            # Create a closure to capture mock_method for each method
            def create_method_wrapper(method_mock):
                def wrapper(*args, **kwargs):
                    return method_mock
                return wrapper
            
            setattr(mock_table, method, create_method_wrapper(mock_method))
        
        # Mock the Google ADK module
        mock_module = MagicMock()
        mock_module.enable_tracing = MagicMock()
        mock_module.UserMessage = MagicMock()
        mock_module.AgentMessage = MagicMock()
        
        # Set up multiple patches
        with patch("supabase.create_client", return_value=mock_client), \
             patch.dict("sys.modules", {"google.adk": mock_module}), \
             patch.dict("sys.modules", {"google.adk.messages": mock_module}):
            yield
    else:
        yield


@pytest.fixture
def mock_environment():
    """
    Set up a mock environment for tests.
    
    This fixture sets environment variables for testing.
    """
    original_env = os.environ.copy()
    
    # Set up environment variables for testing
    os.environ["SUPABASE_URL"] = os.environ.get("SUPABASE_URL", "https://example.com")
    os.environ["SUPABASE_KEY"] = os.environ.get("SUPABASE_KEY", "mock-key")
    os.environ["SUPABASE_ANON_KEY"] = os.environ.get("SUPABASE_ANON_KEY", "mock-anon-key")
    os.environ["SUPABASE_SERVICE_ROLE"] = os.environ.get("SUPABASE_SERVICE_ROLE", "mock-service-role")
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "mock-google-api-key")
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "mock-openai-api-key")
    os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "mock-anthropic-api-key")
    
    yield
    
    # Restore the original environment
    os.environ.clear()
    os.environ.update(original_env)
