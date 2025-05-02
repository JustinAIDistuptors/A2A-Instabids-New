"""ContractorAgent: specialized agent for contractors to submit bids and visualize projects."""
from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path

from instabids_google.adk import LlmAgent as LLMAgent, enable_tracing
from instabids_google.adk.messages import UserMessage
from instabids.tools import supabase_tools, bid_visualization_tool
from instabids.a2a_comm import send_envelope
from memory.persistent_memory import PersistentMemory
from .bid_scoring import score_bid

# enable stdout tracing for dev envs
enable_tracing("stdout")

SYSTEM_PROMPT = (
    "You are ContractorAgent, a specialized assistant for contractors. "
    "Review project details, ask clarifying questions, generate bid visualizations, "
    "score bid competitiveness, persist bid data to Supabase, and emit 'bid.submitted' "
    "A2A envelopes. Maintain memory of contractor preferences and past bids."
)

class ContractorAgent(LLMAgent):
    """Concrete ADK agent with bid creation and visualization capabilities."""
    
    def __init__(self, memory: PersistentMemory | None = None) -> None:
        super().__init__(
            name="ContractorAgent",
            tools=[*supabase_tools, bid_visualization_tool],
            system_prompt=SYSTEM_PROMPT,
            memory=memory,
        )
        
    async def submit_bid(
        self,
        project_id: str,
        contractor_id: str,
        bid_details: Dict[str, Any],
        image_paths: List[Path] = []
    ) -> Dict[str, Any]:
        """
        Submit a bid for a project.
        
        Args:
            project_id: The ID of the project to bid on
            contractor_id: The ID of the contractor submitting the bid
            bid_details: Dictionary containing bid details
            image_paths: Optional list of paths to bid visualization images
            
        Returns:
            Dict containing agent response, bid ID, and bid score
        """
        # Process any images
        image_context = {}
        if image_paths:
            image_context = await self._process_images(image_paths)
        
        # Create user message for agent
        user_message = UserMessage(
            content=f"Submit bid for project {project_id} from contractor {contractor_id}"
        )
        
        # Process message with agent
        response = await self.process(user_message)
        
        # Score the bid
        bid_score = await score_bid(project_id, bid_details)
        
        # 4) Persist bid to Supabase
        from instabids.data_access import save_bid  # local import to avoid circulars
        
        bid_id = await save_bid(
            contractor_id=contractor_id,
            project_id=project_id,
            bid_details=bid_details,
            score=bid_score["score"],
            image_context=image_context
        )
        
        # 5) Emit A2A envelope
        await send_envelope("bid.submitted", {
            "bid_id": bid_id,
            "project_id": project_id,
            "score": bid_score
        })
        
        # Fix: Access response as dictionary if it's a dict, otherwise use .content attribute
        agent_response = response["content"] if isinstance(response, dict) else response.content
        
        return {
            "agent_response": agent_response,
            "bid_id": bid_id,
            "bid_score": bid_score
        }
    
    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    async def _process_images(self, image_paths: List[Path]) -> dict[str, Any]:
        """Call the visualization tool and return parsed context."""
        context = {}
        for path in image_paths:
            result = await bid_visualization_tool.call(image_path=str(path))
            context[path.name] = result
        return context