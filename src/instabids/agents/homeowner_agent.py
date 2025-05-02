"""HomeownerAgent: collects info then delegates to BidCardAgent."""
from __future__ import annotations
from pathlib import Path
from typing import Any, List, Optional, Dict
import logging

# Use instabids_google.adk instead of google.adk to fix import conflicts
from instabids_google.adk import LlmAgent, enable_tracing
from instabids_google.adk.messages import UserMessage
from instabids.tools import supabase_tools, openai_vision_tool
from instabids.a2a_comm import send_envelope
from memory.persistent_memory import PersistentMemory
from instabids.data import project_repo
from instabids.agents.bidcard_agent import create_bid_card

# Set up logging
logger = logging.getLogger(__name__)
enable_tracing("stdout")

SYSTEM_PROMPT = (
    "You are HomeownerAgent. Gather project info, store a project row, then "
    "call BidCardAgent to create a standardized bid card for contractors."
)

class HomeownerAgent(LlmAgent):
    def __init__(self, memory: Optional[PersistentMemory] = None) -> None:
        """
        Initialize the HomeownerAgent.
        
        Args:
            memory: Optional persistent memory system
        """
        super().__init__(
            name="HomeownerAgent",
            tools=[*supabase_tools, openai_vision_tool],
            system_prompt=SYSTEM_PROMPT,
            memory=memory or PersistentMemory(),
        )

    async def process_input(        # unchanged public API
        self,
        user_id: str,
        description: str | None = None,
        image_paths: List[Path] | None = None,
    ) -> Dict[str, Any]:
        """
        Process input from a homeowner.
        
        Args:
            user_id: ID of the user
            description: Optional project description
            image_paths: Optional list of image paths
            
        Returns:
            Dict containing agent response, project ID, bid card, and confidence
        """
        vision_ctx: Dict[str, Any] = {}
        if image_paths:
            vision_ctx = await self._process_images(image_paths)

        parts = [p for p in (description, f"Vision: {vision_ctx}" if vision_ctx else None) if p]
        response = await self.chat(UserMessage("\n".join(parts), user_id))

        project_id = await self._save_project(
            user_id=user_id,
            description=description or "(image‑only)",
            category="tbd",
            urgency="tbd",
            vision_context=vision_ctx,
        )

        project_stub = {
            "id": project_id,
            "title": (description or "Project")[:80],
            "description": description or "",
        }
        bid_card, confidence = create_bid_card(project_stub, vision_ctx)

        await send_envelope("bid_card.created", {"bid_card_id": bid_card["id"]})

        return {
            "agent_response": response.content,
            "project_id": project_id,
            "bid_card": bid_card,
            "confidence": confidence,
        }

    async def _process_images(self, paths: List[Path]) -> Dict[str, Any]:
        """
        Process images and extract vision context.
        
        Args:
            paths: List of image paths
            
        Returns:
            Dictionary of image analysis results
        """
        ctx = {}
        for p in paths:
            ctx[p.name] = await openai_vision_tool.analyze_image(image_path=str(p))
        return ctx
        
    async def _save_project(
        self,
        user_id: str,
        description: str,
        category: str,
        urgency: str,
        vision_context: Optional[Dict[str, Any]] = None,  # Changed to Optional
    ) -> str:
        """
        Save a project to the database.
        
        Args:
            user_id: ID of the user
            description: Project description
            category: Project category
            urgency: Project urgency
            vision_context: Optional vision context
            
        Returns:
            Project ID
        """
        row = {
            "homeowner_id": user_id,
            "title": description[:80],
            "description": description,
            "category": category.lower(),
            "urgency": urgency.lower(),
            "vision_context": vision_context or {},  # Use empty dict if None
        }
        
        try:
            project_id = project_repo.save_project(row)
            await send_envelope("project.created", {"project_id": project_id, "homeowner_id": user_id})
            return project_id
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise