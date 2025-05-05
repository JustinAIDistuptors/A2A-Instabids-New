from unittest.mock import AsyncMock, patch, MagicMock, call
from instabids.agents.homeowner_agent import HomeownerAgent
from memory.persistent_memory import PersistentMemory
import builtins
import logging

# Set up minimal logging config for tests
logging.basicConfig(level=logging.INFO)

# Patch the module-level function, not the imported reference
@patch("instabids.a2a_comm.send_envelope")
@patch("instabids.data.project_repo.save_project", return_value="pid1")
@patch("instabids.data.project_repo.save_project_photos")
def test_event_emitted(m_photos, m_save, m_send):
    """Test that project.created event is emitted when project is started."""
    # Create agent with test memory
    memory = PersistentMemory()
    agent = HomeownerAgent(memory=memory)
    
    # Test the target function directly
    pid = agent.start_project("paint fence urgently")
    
    # Print mocked values for debugging
    print(f"PID: {pid}")
    print(f"m_save.call_count: {m_save.call_count}")
    print(f"m_save.call_args: {m_save.call_args}")
    print(f"m_send.call_count: {m_send.call_count}")
    
    if m_send.call_args:
        print(f"m_send.call_args: {m_send.call_args}")
    
    # Verify results
    assert pid == "pid1", f"Expected project ID 'pid1' but got {pid}"
    
    # Verify the repo.save_project was called
    m_save.assert_called_once()
    
    # Verify the call to send_envelope
    assert m_send.call_count >= 1, "Expected send_envelope to be called at least once"
    
    # Now check the first call arguments
    event_type, payload = m_send.call_args[0]
    assert event_type == "project.created", f"Expected event type 'project.created' but got {event_type}"
    assert payload["project_id"] == "pid1", f"Expected project_id 'pid1' but got {payload.get('project_id')}"
