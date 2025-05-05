from unittest.mock import AsyncMock, patch, MagicMock
from instabids.agents.homeowner_agent import HomeownerAgent
from memory.persistent_memory import PersistentMemory

@patch("instabids.a2a_comm.send_envelope")
@patch("instabids.data.project_repo.save_project", return_value="pid1")
@patch("instabids.data.project_repo.save_project_photos")
def test_event_emitted(m_photos, m_save, m_send):
    # Create agent with mock memory
    memory = PersistentMemory()
    agent = HomeownerAgent(memory=memory)
    
    # Test project creation
    pid = agent.start_project("paint fence urgently")
    assert pid == "pid1"
    
    # Verify the event was emitted with expected parameters
    m_send.assert_called_once()
    event_name, payload = m_send.call_args[0]
    assert event_name == "project.created"
    assert payload["project_id"] == "pid1"
