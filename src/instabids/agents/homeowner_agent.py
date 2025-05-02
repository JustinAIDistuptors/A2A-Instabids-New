"""HomeownerAgent now uses advanced classifier with confidence."""
from __future__ import annotations
from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools, openai_vision_tool
from memory.persistent_memory import PersistentMemory
from instabids.data import project_repo as repo
from instabids.agents.job_classifier import classify
from typing import List, Any
from contextlib import suppress

enable_tracing("stdout")

class HomeownerAgent(LlmAgent):
    def __init__(self, memory: PersistentMemory|None=None):
        super().__init__(
            name="HomeownerAgent",
            tools=[*supabase_tools, openai_vision_tool],
            system_prompt=(
                "Classify homeowner projects, store them, emit events."
            ),
            memory=memory,
        )

    # ----------------------------------------------------------
    def start_project(self, description: str, images: List[dict]|None=None) -> str:
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
            # TODO: logging
            raise
        return pid