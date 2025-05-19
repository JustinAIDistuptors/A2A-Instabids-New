"""ContractorAgent: specialized agent for contractors to submit bids and visualize projects."""
from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path

from google.adk import LLMAgent, enable_tracing
from google.adk.messages import UserMessage
from instabids.tools import supabase_tools, bid_visualization_tool
from instabids.a2a_comm import send_envelope
from instabids.memory.persistent_memory import PersistentMemory
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
            memory=memory or PersistentMemory(),
        )
    
    # ────────────────────────────────────────────────────────────────────────
    # Public API used by FastAPI / CLI
    # ────────────────────────────────────────────────────────────────────────

    async def submit_bid(
        self,
        contractor_id: str,
        project_id: str,
        bid_details: Dict[str, Any],
        project_images: List[Path] | None = None
    ) -> dict[str, Any]:
        """Main entry. Accepts bid details and optional project images."""
        
        # 1) Process project images if provided
        image_context = {}
        if project_images:
            image_context = await self._process_images(project_images)
        
        # 2) Build full prompt for ADK
        prompt_parts = [f"Bid details: {bid_details}"]
        if image_context:
            prompt_parts.append(f"Project images context: {image_context}")
        
        user_msg = UserMessage("\n".join(prompt_parts))
        response = await self.chat(user_msg)
        
        # 3) Score bid competitiveness
        bid_score = score_bid(bid_details, image_context)
        
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
        
        return {
            "agent_response": response.content,
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
