"""Central A2A event‑schema registry."""
from __future__ import annotations
from typing import TypedDict

class ProjectCreated(TypedDict):
    project_id: str
    homeowner_id: str

EVENT_SCHEMAS = {
    "project.created": ProjectCreated,
}