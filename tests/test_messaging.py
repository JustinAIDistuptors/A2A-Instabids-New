aW1wb3J0IHB5dGVzdApmcm9tIGluc3RhYmlkcy5hZ2VudHMubWVzc2FnaW5nX2FnZW50IGltcG9ydCBNZXNzYWdpbmdBZ2VudAoKQHB5dGVzdC5tYXJrLmFzeW5jaW8KYXN5bmMgZGVmIHRlc3RfdGhyZWFkX2FuZF9tZXNzYWdlcyhtb25rZXlwYXRjaCwgbW9ja19hc3luY19zZW5kX2VudmVsb3BlKToKIyBFeHBlY3QgYSBtb2NrIGZvciBzZW5kX2VudmVsb3BlCiAgICBhZ2VudCA9IE1lc3NhZ2luZ0FnZW50KCkKCiAgICAjIE1vbmtleS1wYXRjaCByZXBvIHRvIGF2b2lkIHJlYWwgREIgY2FsbHMKICAgIG1vbmtleXBhdGNoLnNldGF0dHIoImluc3RhYmlkcy5kYXRhLm1lc3NhZ2VfcmVwby5jcmVhdGVfdGhyZWFkIiwKICAgICAgICAgICAgICAgICAgICAgICAgbGFtYmRhIHAsdTogeyJpZCI6ICJ0aC0xMjMifSkKICAgIG1vbmtleXBhdGNoLnNldGF0dHIoImluc3RhYmlkcy5kYXRhLm1lc3NhZ2VfcmVwby5jcmVhdGVfbWVzc2FnZSIsCiAgICAgICAgICAgICAgICAgICAgICAgbGFtYmRhIHQsdSxjLG0sYXM6IHsiaWQiOiAibXNnLTQ1NiIsICJjb250ZW50IjogY30pCiAgICBtb25rZXlwYXRjaC5zZXRhdHRyKCJpbnN0YWJpZHMuZGF0YS5tZXNzYWdlX3JlcG8uZ2V0X21lc3NhZ2VzIiwKICAgICAgICAgICAgICAgICAgICAgICAgbGFtYmRhIHQ6IFt7ImlkIjogIm1zZy00NTYiLCAiY29udGVudCI6ICJIZWxsbyJ9XSkKICAgIC# Monkeypatch a2a_comm.send_envelope to track calls
    monkeypatch.setattr("instabids.agents.messaging_agent.send_envelope", mock_async_send_envelope)


    # Create thread
    out = await agent.handle_create_thread("user1", "proj1")
    assert out["thread_id"] == "th-123"

    # Send message
    msg = await agent.handle_send_message("user1", "th-123", "Hi")
    assert msg["content"] == "Hi"
    # Verify send_envelope was called
    mock_async_send_envelope.assert_awaited_once_with("message.sent", {
        "thread_id": "th-123",
        "message_id": "msg-456",
        "sender_id": "user1"
    })

    # Get messages
    hist = await agent.handle_get_messages("user1", "th-123")
    assert isinstance(hist["messages"], list)
    assert len(hist["messages"]) == 1
    assert hist["messages"][0]["content"] == "Hello"

# Fixture to mock async send_envelope
@pytest.fixture
def mock_async_send_envelope(mocker):
    return mocker.AsyncMock()
