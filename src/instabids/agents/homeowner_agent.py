"""HomeownerAgent with slot-filling for project details."""
from __future__ import annotations
from pathlib import Path
from typing import List, Any, Dict, Set, Optional
import logging

from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools, openai_vision_tool
from memory.persistent_memory import PersistentMemory
from instabids.data import project_repo as repo
from instabids.agents.job_classifier import classify
from instabids.a2a_comm import send_envelope, on_envelope
from instabids.a2a.events import EVENT_SCHEMAS

# Set up logging
logger = logging.getLogger(__name__)
enable_tracing("stdout")

REQUIRED_SLOTS: Set[str] = {
    "title", "category", "job_type", "location",
    "budget_range", "timeline", "group_bidding",
}

def _next_question(missing: Set[str]) -> str:
    order = [
        ("category", "Is this a repair, renovation, installation, maintenance, or construction project?"),
        ("job_type", "What specific work is needed (e.g., roof repair, lawn mowing)?"),
        ("location", "Where will the work take place?"),
        ("budget_range", "Rough budget range?"),
        ("timeline", "Preferred start and end dates?"),
        ("group_bidding", "Are you open to bundling with nearby jobs to lower cost?"),
    ]
    for slot, q in order:
        if slot in missing:
            return q
    return ""

class HomeownerAgent(LlmAgent):
    def __init__(self, memory: Optional[PersistentMemory] = None):
        """
        Initialize the HomeownerAgent.
        
        Args:
            memory: Optional persistent memory system
        """
        super().__init__(
            name="HomeownerAgent",
            tools=[*supabase_tools, openai_vision_tool],
            system_prompt=(
                "Classify homeowner projects, collect required information, "
                "store them, and emit events."
            ),
            memory=memory,
        )

    async def process_input(
        self,
        user_id: str,
        description: str | None = None,
        image_paths: List[Path] | None = None,
    ) -> Dict[str, Any]:
        """
        Process input from a homeowner with slot-filling.
        
        Args:
            user_id: ID of the user
            description: Optional project description
            image_paths: Optional list of image paths
            
        Returns:
            Dict containing either next question or completed project info
        """
        mem = self.memory.get(user_id, default={})
        collected: Dict[str, Any] = mem.get("slots", {})

        if description:
            collected["description"] = description
            # naive extraction demo: title is first 50 chars
            collected.setdefault("title", description[:50])

        # Vision labels
        vision_ctx = {}
        if image_paths:
            vision_ctx = await self._process_images(image_paths)

        missing = REQUIRED_SLOTS - collected.keys()
        if missing:
            q = _next_question(missing)
            self.memory.put(user_id, {"slots": collected})
            return {"need_more": True, "question": q}

        # All slots are filled, save the project
        project_id = self.start_project(
            description=collected.get("description", ""),
            images=vision_ctx.get("images", [])
        )
        
        # Return the completed project info
        return {
            "need_more": False,
            "project_id": project_id,
            "slots": collected
        }

    async def _process_images(self, paths: List[Path]) -> Dict[str, Any]:
        """
        Process images and extract vision context.
        
        Args:
            paths: List of image paths
            
        Returns:
            Dictionary of image analysis results
        """
        images = []
        for p in paths:
            try:
                analysis = await openai_vision_tool.analyze_image(image_path=str(p))
                images.append({
                    "path": str(p),
                    "tag": analysis.get("primary_tag", ""),
                    "analysis": analysis
                })
            except Exception as err:
                logger.error(f"Error processing image {p}: {err}")
        
        return {"images": images}

    def start_project(self, description: str, images: List[dict] | None = None) -> str:
        """
        Start a new project with the collected information.
        
        Args:
            description: Project description
            images: Optional list of image data
            
        Returns:
            Project ID
        """
        vision_tags: list[str] = [img.get("tag", "") for img in images] if images else []
        cls = classify(description, vision_tags)
        row = {
            "homeowner_id": "TODO_user_id",
            "title": description[:80],
            "description": description,
            "category": cls["category"].lower(),
            "confidence": cls["confidence"],
        }
        try:
            with repo._Tx():
                pid = repo.save_project(row)
                if images:
                    repo.save_project_photos(pid, images)
        except Exception as err:
            logger.error(f"Failed to save project: {err}")
            raise
            
        # --- emit A2A envelope -----------------------------------------
        payload = {"project_id": pid, "homeowner_id": row["homeowner_id"]}
        send_envelope("project.created", payload)
        return pid


# ------------------------------------------------------------------
# listen for incoming events (example)
@on_envelope("bid.accepted")
async def _handle_bid_accepted(evt: Dict[str, Any]) -> None:  # noqa: D401
    """Handle bid accepted events."""
    # placeholder: update memory, notify homeowner, etc.
    logger.info(f"Received bid.accepted event: {evt}")