# A2A Routing

## Overview

This module provides an asynchronous event routing mechanism between agents using the A2AEnvelope schema.

## Components

- **A2AEnvelope**: Defines the structure of an event.
- **A2ADispatcher**: Manages registration and dispatching of events to appropriate handlers.

## Usage

1. Create an envelope:
   ```python
   from instabids.a2a.envelope import A2AEnvelope

   envelope = A2AEnvelope.create(topic="example.topic", sender="agent1", payload={"key": "value"})
   ```

2. Register a handler:
   ```python
   from instabids.a2a.dispatcher import A2ADispatcher

   dispatcher = A2ADispatcher()

   async def handler_function(envelope: A2AEnvelope):
       print(f"Received event: {envelope.id} with payload: {envelope.payload}")
       # Process the event

   dispatcher.register("example.topic", handler_function)
   ```

3. Dispatch the event:
   ```python
   import asyncio
   # Assuming the dispatcher and handler are defined as above
   # asyncio.run(dispatcher.dispatch(envelope)) # In a main execution context
   # Or if already in an async context:
   await dispatcher.dispatch(envelope)
   ```

## Tracing

Basic event tracing is implemented using print statements in the `A2ADispatcher.dispatch` method. This shows when an event is dispatched, which handlers are queued, and when handling is complete. For production environments, integrating with a formal logging library (like the standard `logging` module) is recommended.