"""
Event schemas for agent-to-agent communication.

This module defines the schemas for events that can be sent between agents
in the InstaBids system.
"""

from typing import Dict, Any

# Event types
EVENT_TYPE_PROJECT_CREATED = "project.created"
EVENT_TYPE_PROJECT_UPDATED = "project.updated"
EVENT_TYPE_BID_CREATED = "bid.created"
EVENT_TYPE_BID_UPDATED = "bid.updated"
EVENT_TYPE_MATCH_FOUND = "match.found"
EVENT_TYPE_MESSAGE_SENT = "message.sent"

# Event schemas
EVENT_SCHEMAS = {
    EVENT_TYPE_PROJECT_CREATED: {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "user_id": {"type": "string"},
            "description": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"}
        },
        "required": ["project_id", "user_id", "description"]
    },
    
    EVENT_TYPE_PROJECT_UPDATED: {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "user_id": {"type": "string"},
            "description": {"type": "string"},
            "updated_at": {"type": "string", "format": "date-time"}
        },
        "required": ["project_id", "user_id"]
    },
    
    EVENT_TYPE_BID_CREATED: {
        "type": "object",
        "properties": {
            "bid_id": {"type": "string"},
            "project_id": {"type": "string"},
            "contractor_id": {"type": "string"},
            "amount": {"type": "number"},
            "created_at": {"type": "string", "format": "date-time"}
        },
        "required": ["bid_id", "project_id", "contractor_id", "amount"]
    },
    
    EVENT_TYPE_BID_UPDATED: {
        "type": "object",
        "properties": {
            "bid_id": {"type": "string"},
            "project_id": {"type": "string"},
            "contractor_id": {"type": "string"},
            "amount": {"type": "number"},
            "updated_at": {"type": "string", "format": "date-time"}
        },
        "required": ["bid_id", "project_id"]
    },
    
    EVENT_TYPE_MATCH_FOUND: {
        "type": "object",
        "properties": {
            "match_id": {"type": "string"},
            "project_id": {"type": "string"},
            "bid_id": {"type": "string"},
            "homeowner_id": {"type": "string"},
            "contractor_id": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"}
        },
        "required": ["match_id", "project_id", "bid_id", "homeowner_id", "contractor_id"]
    },
    
    EVENT_TYPE_MESSAGE_SENT: {
        "type": "object",
        "properties": {
            "message_id": {"type": "string"},
            "sender_id": {"type": "string"},
            "recipient_id": {"type": "string"},
            "content": {"type": "string"},
            "sent_at": {"type": "string", "format": "date-time"}
        },
        "required": ["message_id", "sender_id", "recipient_id", "content"]
    }
}

def validate_event(event_type: str, payload: Dict[str, Any]) -> bool:
    """
    Validate an event payload against its schema.
    
    Args:
        event_type: Type of event
        payload: Event payload to validate
        
    Returns:
        True if valid, False otherwise
    """
    # This is a simplified validation - in a real system you would use
    # a proper JSON Schema validator like jsonschema
    
    schema = EVENT_SCHEMAS.get(event_type)
    if not schema:
        return False
    
    # Check required fields
    for field in schema.get("required", []):
        if field not in payload:
            return False
    
    return True