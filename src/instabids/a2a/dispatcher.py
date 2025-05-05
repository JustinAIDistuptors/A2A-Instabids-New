"""Asynchronous dispatcher for A2A events."""
from __future__ import annotations
import asyncio
from typing import Callable, Dict, List, Any
from instabids.a2a.envelope import A2AEnvelope

class A2ADispatcher:
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[A2AEnvelope], Any]]] = {}

    def register(self, topic: str, handler: Callable[[A2AEnvelope], Any]) -> None:
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    async def dispatch(self, envelope: A2AEnvelope) -> None:
        handlers = self._handlers.get(envelope.topic, [])
        # Basic logging for tracing
        print(f"Dispatching event {envelope.id} on topic {envelope.topic} to {len(handlers)} handlers.") 
        tasks = []
        for handler in handlers:
            # Schedule handler execution
            tasks.append(asyncio.create_task(handler(envelope)))
            print(f"  - Queued handler: {handler.__name__}")
        
        if tasks:
            await asyncio.gather(*tasks) # Wait for all handlers to complete
            print(f"Finished handling event {envelope.id} on topic {envelope.topic}.")
        else:
             print(f"No handlers found for topic {envelope.topic}.")
