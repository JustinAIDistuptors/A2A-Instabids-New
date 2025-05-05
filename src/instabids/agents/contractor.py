"""Contractor agent implementation."""
from typing import Optional, Dict, Any

# Try to import from google.adk first, if not available use mock implementation
try:
    from google.adk import LlmAgent
except ImportError:
    from instabids.mock_adk import LlmAgent

from memory.persistent_memory import PersistentMemory

class ContractorAgent(LlmAgent):
    """Agent representing a contractor who can bid on projects."""
    
    def __init__(self, memory: Optional[PersistentMemory] = None) -> None:
        """Initialize ContractorAgent."""
        super().__init__(
            name="ContractorAgent",
            system_prompt="You help contractors find and bid on home improvement projects."
        )
        self.memory = memory or PersistentMemory()
        self.tools = []
    
    async def process_bid(self, bid_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a bid from a contractor."""
        return {
            "bid_id": bid_data.get("id", "unknown"),
            "status": "submitted",
            "message": "Bid submitted successfully"
        }

def create_contractor_agent(memory: Optional[PersistentMemory] = None) -> ContractorAgent:
    """Create and return a ContractorAgent instance."""
    return ContractorAgent(memory=memory)

# Create a singleton instance for import
contractor_agent = ContractorAgent()
