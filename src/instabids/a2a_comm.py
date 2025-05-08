"""
Agent-to-Agent Communication Module.

This module provides functions for sending and receiving messages between agents
in the InstaBids system.
"""

from typing import Dict, Any, Callable, Optional, List
import json
import logging
import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)

# Registry of event handlers
_event_handlers: Dict[str, List[Callable]] = {}

def send_envelope(event_type: str, payload: Dict[str, Any], source: str = "unknown") -> str:
    """
    Send an event envelope to other agents.
    
    Args:
        event_type: Type of event being sent
        payload: Event payload data
        source: Source agent identifier
        
    Returns:
        Envelope ID
    """
    envelope_id = str(uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    envelope = {
        "id": envelope_id,
        "type": event_type,
        "source": source,
        "timestamp": timestamp,
        "payload": payload
    }
    
    logger.info(f"Sending envelope: {envelope_id} of type {event_type} from {source}")
    
    # Dispatch to registered handlers
    _dispatch_envelope(envelope)
    
    return envelope_id

def on_envelope(event_type: str) -> Callable:
    """
    Decorator to register a handler for a specific event type.
    
    Args:
        event_type: Type of event to handle
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        if event_type not in _event_handlers:
            _event_handlers[event_type] = []
        _event_handlers[event_type].append(func)
        logger.info(f"Registered handler for event type: {event_type}")
        return func
    return decorator

def _dispatch_envelope(envelope: Dict[str, Any]) -> None:
    """
    Dispatch an envelope to registered handlers.
    
    Args:
        envelope: Event envelope to dispatch
    """
    event_type = envelope.get("type")
    if not event_type:
        logger.error("Envelope missing event type")
        return
    
    handlers = _event_handlers.get(event_type, [])
    if not handlers:
        logger.warning(f"No handlers registered for event type: {event_type}")
        return
    
    for handler in handlers:
        try:
            handler(envelope)
        except Exception as e:
            logger.error(f"Error in handler for event type {event_type}: {e}")