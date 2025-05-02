"""HomeownerAgent with classification + Supabase persistence."""
from __future__ import annotations
from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools
from memory.persistent_memory import PersistentMemory
from instabids.data import project_repo
from instabids.agents.job_classifier import classify, JobCategory
from typing import List

enable_tracing("stdout")

class HomeownerAgent(LlmAgent):
    def __init__(self, memory: PersistentMemory | None = None):
        super().__init__(
            name="HomeownerAgent",
            tools=[*supabase_tools],
            system_prompt=(
                "You guide homeowners, classify the job type, and save structured data."
            ),
            memory=memory,
        )

    def start_project(self, description: str, images: List[dict] | None = None) -> str:
        cat: JobCategory = classify(description)
        row = {
            "homeowner_id": "TODO_user_id",
            "title": description[:80],
            "description": description,
            "category": cat.lower(),
        }
        pid = project_repo.save_project(row)
        if images:
            project_repo.save_project_photos(pid, images)
        # TODO: emit A2A event
        return pid