"""A2A communication module.

This module provides functions for sending and receiving events between agents.
"""

import uuid
import json
import logging
from typing import List, Dict, Any, Callable

logger = logging.getLogger(__name__)

# Registry of event handlers
_event_handlers: Dict[str, List[Callable]] = {}

def send_envelope(event_type: str, payload: Dict[str, Any], source: str = "unknown") -> str:
    """
    Send an event envelope to other agents.
    
    Args:
        event_type: Type of event (e.g., 'project.created')
        payload: Event data
        source: Name of the sending agent
        
    Returns:
        ID of the envelope sent
    """
    # Generate an envelope
    envelope_id = str(uuid.uuid4())
    envelope = {
        "id": envelope_id,
        "type": event_type,
        "source": source,
        "timestamp": 12345678,  # placeholder for actual
        "payload": payload
    }
    
    # Log the envelope for debugging
    logger.info(f"Sending envelope: {envelope}")
    
    # Deliver to handlers
    _dispatch_envelope(envelope)
    
    return envelope_id

def register_handler(event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
    """
    Register a handler for an event type.
    
    Args:
        event_type: Type of event to handle
        handler: Function to call when events of this type are received
    """
    if event_type not in _event_handlers:
        _event_handlers[event_type] = []
        
    _event_handlers[event_type].append(handler)
    logger.debug(f"Registered handler for {event_type}")

def _dispatch_envelope(envelope: Dict[str, Any]) -> None:
    """
    Dispatch an envelope to registered handlers.
    
    Args:
        envelope: Event envelope to dispatch
    """
    event_type = envelope["type"]
    if event_type in _event_handlers:
        for handler in _event_handlers[event_type]:
            try:
                handler(envelope)
            except Exception as e:
                logger.error(f"Error in handler for {event_type}: {e}")
    else:
        logger.debug(f"No handlers registered for {event_type}")