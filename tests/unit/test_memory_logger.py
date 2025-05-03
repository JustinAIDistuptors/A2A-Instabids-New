"""
Tests for the memory_logger middleware.
"""
import pytest
from unittest.mock import patch, AsyncMock
from instabids.middleware.memory_logger import memory_logger

class MockMessage:
    def __init__(self, content, metadata=None):
        self.content = content
        self.metadata = metadata or {}

class MockResponse:
    def __init__(self, content):
        self.content = content

class MockAgent:
    @memory_logger("TestAgent")
    async def chat(self, msg, *args, **kwargs):
        # Simulate agent processing
        return MockResponse(f"Response to: {msg.content}")

@pytest.mark.asyncio
@patch("instabids.middleware.memory_logger.insert_message")
async def test_memory_logger_records_messages(mock_insert):
    # Setup
    agent = MockAgent()
    message = MockMessage("Hello agent", {"project_id": "test-project-123"})
    
    # Execute
    response = await agent.chat(message)
    
    # Verify
    assert response.content == "Response to: Hello agent"
    assert mock_insert.call_count == 2
    
    # Check homeowner message was logged
    mock_insert.assert_any_call(
        project_id="test-project-123",
        role="homeowner",
        content="Hello agent"
    )
    
    # Check agent response was logged
    mock_insert.assert_any_call(
        project_id="test-project-123",
        role="agent",
        content="Response to: Hello agent"
    )

@pytest.mark.asyncio
@patch("instabids.middleware.memory_logger.insert_message")
async def test_memory_logger_with_kwarg_project_id(mock_insert):
    # Setup
    agent = MockAgent()
    message = MockMessage("Hello agent")  # No metadata
    
    # Execute with project_id as kwarg
    response = await agent.chat(message, project_id="kwarg-project-456")
    
    # Verify
    assert mock_insert.call_count == 2
    
    # Check both messages use the kwarg project_id
    mock_insert.assert_any_call(
        project_id="kwarg-project-456",
        role="homeowner",
        content="Hello agent"
    )
    mock_insert.assert_any_call(
        project_id="kwarg-project-456",
        role="agent",
        content="Response to: Hello agent"
    )

@pytest.mark.asyncio
@patch("instabids.middleware.memory_logger.insert_message")
async def test_memory_logger_no_project_id(mock_insert):
    # Setup
    agent = MockAgent()
    message = MockMessage("Hello agent")  # No metadata or project_id
    
    # Execute without project_id
    response = await agent.chat(message)  # No project_id in kwargs either
    
    # Verify no logging occurred
    assert mock_insert.call_count == 0
    assert response.content == "Response to: Hello agent"