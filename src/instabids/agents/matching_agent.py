"""MatchingAgent: connects projects with qualified contractors using vector similarity and bid scores."""
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime

from instabids_google.adk import LlmAgent as LLMAgent, enable_tracing
from instabids_google.adk.messages import UserMessage
from instabids.tools import supabase_tools, vector_search_tool
from instabids.a2a_comm import send_envelope
from memory.persistent_memory import PersistentMemory
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
            memory=memory,
        )
        
    async def find_matches(
        self,
        project_id: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Find qualified contractors for a project.
        
        Args:
            project_id: The ID of the project to match
            max_results: Maximum number of matches to return
            
        Returns:
            Dict containing agent response, matches, and match status
        """
        # Retrieve project from database
        from instabids.data_access import get_project  # local import to avoid circulars
        
        project = await get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Execute matching logic
        matches = await self._execute_matching(project, max_results)
        
        # Create user message for agent
        user_message = UserMessage(
            content=f"Find matches for project {project_id} in category {project['category']}"
        )
        
        # Process message with agent
        response = await self.process(user_message)
        
        # Emit A2A envelope for matches found
        if matches:
            send_envelope("match.found", {
                "project_id": project_id,
                "matches": matches,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "agent_response": response.content,
            "matches": matches,
            "match_count": len(matches)
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