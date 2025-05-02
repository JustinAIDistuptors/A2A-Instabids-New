"""
Tracing utilities for agent development.
This module provides tracing capabilities for debugging and monitoring agents.
"""
from typing import Dict, Any, Optional, Union, Literal
import logging
import sys
import json
import os
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Global tracing configuration
_tracing_enabled = False
_tracing_destination: Union[Literal["stdout"], Literal["file"], None] = None
_tracing_file_path: Optional[str] = None


def enable_tracing(destination: Union[Literal["stdout"], Literal["file"], None] = "stdout", 
                  file_path: Optional[str] = None) -> None:
    """
    Enable tracing for agents.
    
    Args:
        destination: Where to send trace output ('stdout', 'file', or None)
        file_path: Path to the trace file (required if destination is 'file')
    """
    global _tracing_enabled, _tracing_destination, _tracing_file_path
    
    _tracing_enabled = True
    _tracing_destination = destination
    
    if destination == "file":
        if not file_path:
            file_path = f"agent_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        _tracing_file_path = file_path
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        logger.info(f"Tracing enabled, writing to file: {file_path}")
    elif destination == "stdout":
        logger.info("Tracing enabled, writing to stdout")
    else:
        _tracing_enabled = False
        logger.info("Tracing disabled")


def disable_tracing() -> None:
    """Disable tracing."""
    global _tracing_enabled
    _tracing_enabled = False
    logger.info("Tracing disabled")


def trace(event_type: str, data: Dict[str, Any]) -> None:
    """
    Record a trace event.
    
    Args:
        event_type: Type of event to trace
        data: Event data to record
    """
    if not _tracing_enabled:
        return
    
    trace_event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "data": data
    }
    
    if _tracing_destination == "stdout":
        print(json.dumps(trace_event), file=sys.stdout)
    elif _tracing_destination == "file" and _tracing_file_path:
        try:
            with open(_tracing_file_path, "a") as f:
                f.write(json.dumps(trace_event) + "\n")
        except Exception as e:
            logger.error(f"Error writing trace to file: {e}")


def trace_message(message_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Record a message trace event.
    
    Args:
        message_type: Type of message (e.g., 'user', 'agent', 'system')
        content: Message content
        metadata: Optional message metadata
    """
    trace("message", {
        "message_type": message_type,
        "content": content,
        "metadata": metadata or {}
    })


def trace_tool_call(tool_name: str, arguments: Dict[str, Any], result: Any = None) -> None:
    """
    Record a tool call trace event.
    
    Args:
        tool_name: Name of the tool being called
        arguments: Arguments passed to the tool
        result: Optional result of the tool call
    """
    trace("tool_call", {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result
    })


def trace_error(error_type: str, message: str, exception: Optional[Exception] = None) -> None:
    """
    Record an error trace event.
    
    Args:
        error_type: Type of error
        message: Error message
        exception: Optional exception object
    """
    trace("error", {
        "error_type": error_type,
        "message": message,
        "exception": str(exception) if exception else None
    })