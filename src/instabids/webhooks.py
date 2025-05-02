"""Webhook handling utilities for InstaBids."""
import hmac
import hashlib
import os
import time
import asyncio
from typing import Dict, Any, AsyncGenerator, Set

# Add type annotations to constants
SECRET: str = os.environ.get("WEBHOOK_SECRET", "changeme")
MAX_AGE: int = 300  # seconds


def verify_signature(token: str) -> str:
    """
    Verify webhook signature token.
    
    Args:
        token: The signature token to verify
        
    Returns:
        The verified token
    """
    # dummy Depends stub for FastAPI
    return token


class _PushBus:
    """
    Internal push notification bus for real-time updates.
    
    This class manages subscriptions to task events and handles
    publishing events to subscribers.
    """
    
    def __init__(self) -> None:
        """Initialize the push bus with empty subscriptions."""
        self._subs: Dict[str, Set[asyncio.Queue]] = {}

    async def subscribe(self, task_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribe to events for a specific task.
        
        Args:
            task_id: The ID of the task to subscribe to
            
        Yields:
            Events related to the task
        """
        q: asyncio.Queue = asyncio.Queue()
        self._subs.setdefault(task_id, set()).add(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            if task_id in self._subs:
                self._subs[task_id].discard(q)
                # Clean up empty sets
                if not self._subs[task_id]:
                    del self._subs[task_id]

    async def publish(self, task_id: str, event: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers of a task.
        
        Args:
            task_id: The ID of the task the event is for
            event: The event data to publish
        """
        for q in self._subs.get(task_id, []):
            await q.put(event)


# Create a singleton instance
push_to_ui = _PushBus()