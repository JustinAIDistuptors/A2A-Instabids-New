"""
Agent-to-Agent (A2A) communication package.

This package provides modules for agent-to-agent communication in the InstaBids system.
"""

from .events import EVENT_SCHEMAS, validate_event

__all__ = ["EVENT_SCHEMAS", "validate_event"]