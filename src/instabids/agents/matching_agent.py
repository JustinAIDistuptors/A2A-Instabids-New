"""MatchingAgent: connects projects with qualified contractors using vector similarity and bid scores."""
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime

from google.adk import LLMAgent, enable_tracing
from google.adk.messages import UserMessage
from instabids.tools import supabase_tools, vector_search_tool
from instabids.a2a_comm import send_envelope
from instabids.memory.persistent_memory import PersistentMemory
from .matching_engine import match_projects_to_contractors

# enable stdout tracing for dev envs
enable_tracing("stdout")

SYSTEM_PROMPT = (
    "You are MatchingAgent, responsible for connecting projects with qualified contractors. "
    "Use vector similarity to match project requirements with contractor expertise, "
    "consider bid scores when available, and emit 'match.found' A2A envelopes when "
    "qualified connections are identified. Prioritize matches that maximize contractor efficiency "
    "through geographic/project type bundling."
)

class MatchingAgent(LLMAgent):
    """Concrete ADK agent with project-contractor matching capabilities."""
    
    def __init__(self, memory: PersistentMemory | None = None) -> None:
        super().__init__(
            name="MatchingAgent",
            tools=[*supabase_tools, vector_search_tool],
            system_prompt=SYSTEM_PROMPT,
            memory=memory or PersistentMemory(),
        )
    
    # ────────────────────────────────────────────────────────────────────────
    # Public API used by FastAPI / CLI
    # ────────────────────────────────────────────────────────────────────────

    async def find_matches(
        self,
        project_id: str,
        max_results: int = 5
    ) -> dict[str, Any]:
        """Main entry. Find contractors for a specific project."""
        
        # 1) Get project details from Supabase
        from instabids.data_access import get_project_details
        
        project = await get_project_details(project_id)
        
        # 2) Build prompt for ADK
        prompt = f"Find matches for project: {project['description']}\nCategory: {project['category']}"
        user_msg = UserMessage(prompt)
        response = await self.chat(user_msg)
        
        # 3) Execute matching logic
        matches = await self._execute_matching(project, max_results)
        
        # 4) Persist matches to Supabase
        from instabids.data_access import save_matches
        
        match_ids = await save_matches(project_id, matches)
        
        # 5) Emit A2A envelope
        await send_envelope("match.found", {
            "project_id": project_id,
            "matches": matches,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "agent_response": response.content,
            "match_ids": match_ids,
            "matches": matches
        }
    
    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    async def _execute_matching(
        self,
        project: Dict[str, Any],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Execute matching logic using vector search and bid scoring."""
        # 1) Vector search for similar projects
        vector_results = await vector_search_tool.call(
            query=project["description"],
            category=project["category"],
            top_k=max_results
        )
        
        # 2) Apply business logic to filter results
        filtered_matches = []
        for contractor in vector_results["matches"]:
            # Skip if contractor hasn't completed profile
            if not contractor.get("verified"):
                continue
                
            # Calculate composite score
            score = await match_projects_to_contractors(
                project, 
                contractor,
                vector_results["scores"][contractor["id"]]
            )
            
            if score > 0.7:  # Threshold for quality matches
                filtered_matches.append({
                    "contractor_id": contractor["id"],
                    "score": score,
                    "reasoning": vector_results["reasoning"][contractor["id"]]
                })
        
        return filtered_matches
