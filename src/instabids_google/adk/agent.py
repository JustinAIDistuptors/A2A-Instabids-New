"""
Agent implementation for LLM-based agents.
This module provides the base implementation for LLM-based agents.
"""
from typing import Dict, Any, Optional, List, Callable, Union
import logging
import asyncio

from .messages import BaseMessage, UserMessage, AgentMessage, SystemMessage

# Set up logging
logger = logging.getLogger(__name__)


class LlmAgent:
    """
    Base class for LLM-based agents.
    
    This class provides the core functionality for agents that use LLMs for reasoning
    and decision making.
    """
    
    def __init__(
        self,
        name: str,
        tools: Optional[List[Any]] = None,
        memory: Optional[Any] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize an LLM agent.
        
        Args:
            name: Name of the agent
            tools: Optional list of tools the agent can use
            memory: Optional memory system for the agent
            system_prompt: Optional system prompt to guide the agent's behavior
        """
        self.name = name
        self.tools = tools or []
        self.memory = memory
        self.system_prompt = system_prompt or f"You are {name}, an AI assistant."
        self.conversation_history: List[BaseMessage] = []
        
        # Add system message to conversation history
        self.conversation_history.append(SystemMessage(self.system_prompt))
        
        logger.info(f"Initialized agent: {name}")
    
    async def process_message(self, message: Union[str, BaseMessage], **kwargs) -> Dict[str, Any]:
        """
        Process a message and generate a response.
        
        Args:
            message: The message to process
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary containing the agent's response
        """
        # Convert string to UserMessage if necessary
        if isinstance(message, str):
            user_id = kwargs.get("user_id", "user")
            message = UserMessage(message, user_id)
        
        # Add message to conversation history
        self.conversation_history.append(message)
        
        # Save to memory if available
        if self.memory:
            await self._save_to_memory(message)
        
        # Generate response (to be implemented by subclasses)
        response = await self._generate_response(message, **kwargs)
        
        # Add agent's response to conversation history
        agent_message = AgentMessage(response["content"], self.name)
        self.conversation_history.append(agent_message)
        
        return response
    
    async def _generate_response(self, message: BaseMessage, **kwargs) -> Dict[str, Any]:
        """
        Generate a response to a message.
        
        Args:
            message: The message to respond to
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary containing the agent's response
            
        Note:
            This method should be overridden by subclasses.
        """
        # Default implementation returns a simple response
        return {
            "content": f"Hello, I am {self.name}. I received your message but I'm not fully implemented yet.",
            "metadata": {}
        }
    
    async def _save_to_memory(self, message: BaseMessage) -> None:
        """
        Save a message to the agent's memory.
        
        Args:
            message: The message to save
        """
        if not self.memory:
            return
        
        try:
            # Different memory implementations might have different methods
            if hasattr(self.memory, "add_interaction"):
                self.memory.add_interaction(
                    "message",
                    {
                        "content": message.content,
                        "type": message.__class__.__name__,
                        "metadata": message.metadata
                    }
                )
            elif hasattr(self.memory, "add"):
                self.memory.add(message.to_dict())
        except Exception as e:
            logger.error(f"Error saving to memory: {e}")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history as a list of dictionaries.
        
        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in self.conversation_history]
    
    def clear_conversation_history(self, keep_system_prompt: bool = True) -> None:
        """
        Clear the conversation history.
        
        Args:
            keep_system_prompt: Whether to keep the system prompt in the history
        """
        if keep_system_prompt:
            # Keep only the system prompt
            self.conversation_history = [msg for msg in self.conversation_history 
                                       if isinstance(msg, SystemMessage)]
        else:
            self.conversation_history = []