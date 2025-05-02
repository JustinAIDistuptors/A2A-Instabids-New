"""LlmAgent: Base class for building AI agents with LLM capabilities."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

class LlmAgent:
    """Base class for building AI agents with LLM capabilities.
    
    This class provides the core functionality for creating agents that can
    use large language models to process and respond to user inputs.
    """
    
    def __init__(
        self,
        name: str,
        tools: List[Any] = None,
        system_prompt: str = "",
        memory: Any = None,
    ) -> None:
        """Initialize a new LlmAgent.
        
        Args:
            name: The name of the agent.
            tools: A list of tools the agent can use.
            system_prompt: The system prompt that defines the agent's behavior.
            memory: Optional memory system for the agent.
        """
        self.name = name
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.memory = memory
        
    async def process(self, message: Any, **kwargs) -> Dict[str, Any]:
        """Process a user message and return a response.
        
        Args:
            message: The user message to process.
            **kwargs: Additional keyword arguments.
            
        Returns:
            A dictionary containing the agent's response and any additional information.
        """
        raise NotImplementedError("Subclasses must implement process method")
    
    async def run_tool(self, tool_name: str, **tool_args) -> Any:
        """Run a tool with the given arguments.
        
        Args:
            tool_name: The name of the tool to run.
            **tool_args: Arguments to pass to the tool.
            
        Returns:
            The result of running the tool.
        """
        for tool in self.tools:
            if tool.__name__ == tool_name:
                return await tool.call(**tool_args)
        
        raise ValueError(f"Tool {tool_name} not found")