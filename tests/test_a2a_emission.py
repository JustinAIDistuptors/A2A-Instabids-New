from unittest.mock import AsyncMock, patch
from instabids.agents.homeowner_agent import HomeownerAgent
from memory.persistent_memory import PersistentMemory

@patch("instabids.a2a_comm.send_envelope")
@patch("instabids.data.project_repo.save_project", return_value="pid1")
@patch("instabids.data.project_repo.save_project_photos")
def test_event_emitted(m_photos, m_save, m_send):
    agent = HomeownerAgent(memory=PersistentMemory())
    pid = agent.start_project("paint fence urgently")
    assert pid == "pid1"
    m_send.assert_called_once()
    evt_name, payload = m_send.call_args[0]
    assert evt_name == "project.created"
    assert payload["project_id"] == "pid1"