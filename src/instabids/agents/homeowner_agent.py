"""HomeownerAgent: multimodal concierge for homeowners."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from google.adk import LlmAgent, enable_tracing
from google.adk.messages import UserMessage
from instabids.tools import supabase_tools, openai_vision_tool
from instabids.a2a_comm import send_envelope
from memory.persistent_memory import PersistentMemory
from .job_classifier import classify_job

# enable stdout tracing for dev envs
enable_tracing("stdout")

SYSTEM_PROMPT = (
    "You are HomeownerAgent, a long‑term concierge for homeowners. "
    "Given images, voice/text, or forms, classify the project, ask clarifying "
    "questions, persist structured data to Supabase, and emit a 'project.created' "
    "A2A envelope once you have enough details. Keep memory of preferences and "
    "prior jobs for each user."
)


class HomeownerAgent(LlmAgent):
    """Concrete ADK agent with multimodal intake and memory."""

    def __init__(self, memory: PersistentMemory | None = None) -> None:
        super().__init__(
            name="HomeownerAgent",
            tools=[*supabase_tools, openai_vision_tool],
            system_prompt=SYSTEM_PROMPT,
            memory=memory or PersistentMemory(),
        )

    # ────────────────────────────────────────────────────────────────────────
    # Public API used by FastAPI / CLI
    # ────────────────────────────────────────────────────────────────────────

    async def process_input(
        self,
        user_id: str,
        description: str | None = None,
        image_paths: List[Path] | None = None,
    ) -> dict[str, Any]:
        """Main entry. Accepts description text and/or image file Paths."""

        # 1) Vision pass if images provided
        vision_context: dict[str, Any] = {}
        if image_paths:
            vision_context = await self._process_images(image_paths)

        # 2) Build full prompt for ADK
        content_parts = []
        if description:
            content_parts.append(description)
        if vision_context:
            content_parts.append(f"Vision context: {vision_context}")

        user_msg = UserMessage("\n".join(content_parts))
        response = await self.chat(user_msg)

        # 3) Classify job type & urgency (simple rule‑based for v1)
        classification = classify_job(description or "", vision_context)

        # 4) Persist project
        from instabids.data_access import save_project  # local import to avoid circulars

        project_id = await save_project(
            user_id=user_id,
            description=description or "(image‑only)",
            category=classification["category"],
            urgency=classification["urgency"],
            vision_context=vision_context,
        )

        # 5) Emit A2A envelope
        await send_envelope("project.created", {"project_id": project_id})

        return {
            "agent_response": response.content,
            "project_id": project_id,
            **classification,
        }

    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    async def _process_images(self, image_paths: List[Path]) -> dict[str, Any]:
        """Call the vision tool and return parsed context."""
        context: dict[str, Any] = {}
        for p in image_paths:
            result = await openai_vision_tool.call(image_path=str(p))
            context[p.name] = result
        return context