from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class LLMAgent(ABC):
    """Abstract base class for all LLM agents in the A2A protocol."""
    
    def __init__(self, agent_id: str, system_prompt: str):
        self.agent_id = agent_id
        self.system_prompt = system_prompt
        self.memory = []
        
    @abstractmethod
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages according to A2A protocol."""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities supported by this agent."""
        pass
        
    def add_to_memory(self, entry: Dict[str, Any]):
        """Add interaction to agent's memory."""
        self.memory.append(entry)
        
    def get_memory(self) -> List[Dict[str, Any]]:
        """Retrieve agent's memory."""
        return self.memory
