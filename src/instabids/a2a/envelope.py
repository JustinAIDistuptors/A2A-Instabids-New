"""Defines the A2A event envelope schema."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any
from datetime import datetime
import uuid

@dataclass
class A2AEnvelope:
    id: str
    type: Literal["event"]
    topic: str
    sender: str
    recipient: Optional[str]
    timestamp: datetime
    payload: Dict[str, Any]

    @staticmethod
    def create(topic: str, sender: str, payload: Dict[str, Any], recipient: Optional[str] = None) -> A2AEnvelope:
        return A2AEnvelope(
            id=str(uuid.uuid4()),
            type="event",
            topic=topic,
            sender=sender,
            recipient=recipient,
            timestamp=datetime.utcnow(),
            payload=payload
        )