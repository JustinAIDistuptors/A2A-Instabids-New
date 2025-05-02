"""A2A communication utilities for envelope-based event handling."""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast, Awaitable
import asyncio
import functools
import json
import logging
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

# Type definitions
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Awaitable[Any]])

# Registry of event handlers
_event_handlers: Dict[str, List[Callable[..., Awaitable[Any]]]] = {}

def on_envelope(event_type: str) -> Callable[[F], F]:
    """
    Decorator to register a handler for a specific event type.
    
    Args:
        event_type: The type of event to handle
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        if event_type not in _event_handlers:
            _event_handlers[event_type] = []
            
        # Ensure the handler is async
        if not asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)
            _event_handlers[event_type].append(async_wrapper)
        else:
            _event_handlers[event_type].append(cast(Callable[..., Awaitable[Any]], func))
            
        return func
    return decorator

def send_envelope(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Send an event envelope to registered handlers.
    
    Args:
        event_type: The type of event
        payload: The event data
    """
    envelope = {
        "type": event_type,
        "payload": payload,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    logger.info(f"Sending envelope: {event_type}")
    
    # Dispatch to any registered handlers
    if event_type in _event_handlers:
        for handler in _event_handlers[event_type]:
            asyncio.create_task(handler(payload))
    
    # TODO: Add external event bus integration