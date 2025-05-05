import asyncio
import pytest
from instabids.a2a.envelope import A2AEnvelope
from instabids.a2a.dispatcher import A2ADispatcher

@pytest.mark.asyncio
async def test_dispatcher_calls_registered_handler():
    dispatcher = A2ADispatcher()
    called = False
    received_envelope = None

    async def handler(envelope: A2AEnvelope):
        nonlocal called, received_envelope
        called = True
        received_envelope = envelope
        await asyncio.sleep(0.01) # Simulate async work

    topic = "test.topic"
    payload = {"data": "test_payload"}
    sender = "tester"
    dispatcher.register(topic, handler)
    
    envelope_to_dispatch = A2AEnvelope.create(topic=topic, sender=sender, payload=payload)
    await dispatcher.dispatch(envelope_to_dispatch)

    assert called, "Handler was not called"
    assert received_envelope is not None, "Envelope was not received by handler"
    assert received_envelope.topic == topic
    assert received_envelope.sender == sender
    assert received_envelope.payload == payload
    assert received_envelope.id == envelope_to_dispatch.id

@pytest.mark.asyncio
async def test_dispatcher_handles_multiple_handlers():
    dispatcher = A2ADispatcher()
    call_count = 0

    async def handler1(envelope: A2AEnvelope):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)

    async def handler2(envelope: A2AEnvelope):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)

    topic = "multi.handler.topic"
    dispatcher.register(topic, handler1)
    dispatcher.register(topic, handler2)
    
    envelope = A2AEnvelope.create(topic=topic, sender="tester", payload={})
    await dispatcher.dispatch(envelope)

    assert call_count == 2, "Expected two handlers to be called"

@pytest.mark.asyncio
async def test_dispatcher_no_handler_for_topic():
    dispatcher = A2ADispatcher()
    called = False

    async def handler(envelope: A2AEnvelope):
        nonlocal called
        called = True # This should not be called

    dispatcher.register("registered.topic", handler)
    
    # Dispatch to a different topic
    envelope = A2AEnvelope.create(topic="unregistered.topic", sender="tester", payload={})
    await dispatcher.dispatch(envelope)

    assert not called, "Handler for the wrong topic was called"