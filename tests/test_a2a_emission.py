from unittest.mock import AsyncMock, patch, MagicMock, call
from instabids.agents.homeowner_agent import HomeownerAgent
from memory.persistent_memory import PersistentMemory

@patch("instabids.a2a_comm.send_envelope", return_value="event1")
@patch("instabids.data.project_repo.save_project", return_value="pid1")
@patch("instabids.data.project_repo.save_project_photos")
def test_event_emitted(m_photos, m_save, m_send):
    """Test that project.created event is emitted when project is started."""
    # Create agent with test memory
    memory = PersistentMemory()
    agent = HomeownerAgent(memory=memory)
    
    # Start a project
    pid = agent.start_project("paint fence urgently")
    
    # Verify results
    assert pid == "pid1", f"Expected project ID 'pid1' but got {pid}"
    
    # Verify the repo.save_project was called
    m_save.assert_called_once()
    
    # Check that send_envelope was called correctly
    assert m_send.call_count >= 1, "Expected send_envelope to be called at least once"
    
    # Check if any call has the right pattern
    found_correct_call = False
    for args, _ in m_send.call_args_list:
        if len(args) >= 2 and args[0] == "project.created" and isinstance(args[1], dict) and args[1].get("project_id") == "pid1":
            found_correct_call = True
            break
    
    # Alternative direct check for first call
    if m_send.call_count > 0:
        # Access first positional arguments
        first_args = m_send.call_args_list[0][0]
        if len(first_args) >= 2:
            event_name, payload = first_args[0], first_args[1]
            # Print for debugging
            print(f"Event: {event_name}, Payload: {payload}")
            assert event_name == "project.created"
            assert payload["project_id"] == "pid1"
            found_correct_call = True

    assert found_correct_call, "No call to send_envelope with correct arguments found"
