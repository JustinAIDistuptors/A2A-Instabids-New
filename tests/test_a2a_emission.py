from unittest.mock import AsyncMock, patch, MagicMock, call
from instabids.agents.homeowner_agent import HomeownerAgent
from memory.persistent_memory import PersistentMemory
import builtins
import logging

# Set up minimal logging config for tests
logging.basicConfig(level=logging.INFO)

@patch("instabids.a2a_comm.send_envelope")
@patch("instabids.data.project_repo.save_project", return_value="pid1")
@patch("instabids.data.project_repo.save_project_photos")
def test_event_emitted(m_photos, m_save, m_send):
    """Test that project.created event is emitted when project is started."""
    # Create agent with test memory
    memory = PersistentMemory()
    agent = HomeownerAgent(memory=memory)
    
    # Mock important function to help with debugging
    real_print = print
    def mock_print(*args, **kwargs):
        real_print(*args, **kwargs)
    builtins.print = mock_print
    
    # Test the target function directly
    pid = agent.start_project("paint fence urgently")
    
    # Print for debugging
    real_print(f"PID: {pid}")
    real_print(f"m_save.call_count: {m_save.call_count}")
    real_print(f"m_save.call_args: {m_save.call_args}")
    real_print(f"m_send.call_count: {m_send.call_count}")
    if m_send.call_args:
        real_print(f"m_send.call_args: {m_send.call_args}")
    
    # Verify results
    assert pid == "pid1", f"Expected project ID 'pid1' but got {pid}"
    
    # Verify the repo.save_project was called
    m_save.assert_called_once()
    
    # Monkey-patch the send_envelope function directly for a clean test
    from instabids.a2a_comm import send_envelope as real_send_envelope
    import instabids.a2a_comm
    
    # Store original
    orig_send = instabids.a2a_comm.send_envelope
    
    try:
        # Replace with mock that tracks calls
        mock_sender = MagicMock(return_value="event1")
        instabids.a2a_comm.send_envelope = mock_sender
        
        # Call the function again
        pid = agent.start_project("paint fence urgently")
        
        # Now check the mock directly
        assert mock_sender.call_count >= 1, "Directly patched mock not called"
        event_name, payload = mock_sender.call_args[0]
        assert event_name == "project.created"
        assert payload["project_id"] == "pid1"
    finally:
        # Restore original
        instabids.a2a_comm.send_envelope = orig_send
    
    # Also verify the original test approach, which should work
    assert m_send.call_count >= 1, "Expected send_envelope to be called at least once"
