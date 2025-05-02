"""
Message types for agent communication.
This module defines the message types used for communication between agents and users.
"""
from typing import Dict, Any, Optional, List, Union
import json
from datetime import datetime


class BaseMessage:
    """Base class for all message types."""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a base message.
        
        Args:
            content: The message content
            metadata: Optional metadata associated with the message
        """
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        return {
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "type": self.__class__.__name__
        }
    
    def __str__(self) -> str:
        """String representation of the message."""
        return f"{self.__class__.__name__}(content={self.content[:50]}...)"


class UserMessage(BaseMessage):
    """Message from a user to an agent."""
    
    def __init__(self, content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a user message.
        
        Args:
            content: The message content
            user_id: ID of the user sending the message
            metadata: Optional metadata associated with the message
        """
        super().__init__(content, metadata)
        self.user_id = user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        result = super().to_dict()
        result["user_id"] = self.user_id
        return result


class AgentMessage(BaseMessage):
    """Message from an agent to a user or another agent."""
    
    def __init__(self, content: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize an agent message.
        
        Args:
            content: The message content
            agent_id: ID of the agent sending the message
            metadata: Optional metadata associated with the message
        """
        super().__init__(content, metadata)
        self.agent_id = agent_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        result = super().to_dict()
        result["agent_id"] = self.agent_id
        return result


class SystemMessage(BaseMessage):
    """System message for providing instructions or context."""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a system message.
        
        Args:
            content: The message content
            metadata: Optional metadata associated with the message
        """
        super().__init__(content, metadata)


class FunctionCallMessage(BaseMessage):
    """Message representing a function call."""
    
    def __init__(self, function_name: str, arguments: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a function call message.
        
        Args:
            function_name: Name of the function to call
            arguments: Arguments to pass to the function
            metadata: Optional metadata associated with the message
        """
        content = json.dumps({"function": function_name, "arguments": arguments})
        super().__init__(content, metadata)
        self.function_name = function_name
        self.arguments = arguments
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        result = super().to_dict()
        result["function_name"] = self.function_name
        result["arguments"] = self.arguments
        return result


class FunctionResultMessage(BaseMessage):
    """Message representing the result of a function call."""
    
    def __init__(self, function_name: str, result: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a function result message.
        
        Args:
            function_name: Name of the function that was called
            result: Result of the function call
            metadata: Optional metadata associated with the message
        """
        content = json.dumps({"function": function_name, "result": result})
        super().__init__(content, metadata)
        self.function_name = function_name
        self.result = result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        result = super().to_dict()
        result["function_name"] = self.function_name
        result["result"] = self.result
        return result


def create_message_from_dict(data: Dict[str, Any]) -> BaseMessage:
    """
    Create a message object from a dictionary.
    
    Args:
        data: Dictionary representation of a message
        
    Returns:
        Message object
        
    Raises:
        ValueError: If the message type is not recognized
    """
    message_type = data.get("type", "BaseMessage")
    content = data.get("content", "")
    metadata = data.get("metadata", {})
    
    if message_type == "UserMessage":
        return UserMessage(content, data.get("user_id", "unknown"), metadata)
    elif message_type == "AgentMessage":
        return AgentMessage(content, data.get("agent_id", "unknown"), metadata)
    elif message_type == "SystemMessage":
        return SystemMessage(content, metadata)
    elif message_type == "FunctionCallMessage":
        return FunctionCallMessage(
            data.get("function_name", "unknown"),
            data.get("arguments", {}),
            metadata
        )
    elif message_type == "FunctionResultMessage":
        return FunctionResultMessage(
            data.get("function_name", "unknown"),
            data.get("result", None),
            metadata
        )
    else:
        return BaseMessage(content, metadata)