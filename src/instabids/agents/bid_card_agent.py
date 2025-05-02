"""BidCardAgent: standardizes project requests into structured bid templates."""
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime

from instabids_google.adk import LlmAgent as LLMAgent, enable_tracing
from instabids_google.adk.messages import UserMessage
from instabids.tools import supabase_tools, template_engine
from instabids.a2a_comm import send_envelope
from memory.persistent_memory import PersistentMemory
from .bid_template import create_bid_template

# enable stdout tracing for dev envs
enable_tracing("stdout")

SYSTEM_PROMPT = (
    "You are BidCardAgent, responsible for standardizing project requests into structured bid templates. "
    "Create consistent bid cards from homeowner project details, validate required fields, "
    "support multiple bid formats, and emit 'bidcard.created' A2A envelopes when templates are generated. "
    "Maintain template versions and ensure compliance with platform requirements."
)

class BidCardAgent(LLMAgent):
    """Concrete ADK agent for creating standardized bid templates."""
    
    def __init__(self, memory: PersistentMemory | None = None) -> None:
        super().__init__(
            name="BidCardAgent",
            tools=[*supabase_tools, template_engine],
            system_prompt=SYSTEM_PROMPT,
            memory=memory,
        )
        
    async def create_template(
        self,
        project_id: str,
        template_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        Create a standardized bid template for a project.
        
        Args:
            project_id: The ID of the project to create a template for
            template_type: The type of template to create (standard, commercial, etc.)
            
        Returns:
            Dict containing agent response, template ID, and template data
        """
        # Retrieve project from database
        from instabids.data_access import get_project  # local import to avoid circulars
        
        project = await get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get template schema
        schema = self._get_template_schema(template_type)
        
        # Get required fields
        required_fields = self._get_required_fields(template_type)
        
        # Validate project data
        missing_fields = [field for field in required_fields if field not in project]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Create user message for agent
        user_message = UserMessage(
            content=f"Create {template_type} bid template for project {project_id}"
        )
        
        # Process message with agent
        response = await self.process(user_message)
        
        # Generate template
        template = await create_bid_template(
            project=project,
            template_type=template_type,
            schema=schema
        )
        
        # Generate template ID
        template_id = f"tpl_{project_id}_{template_type}_{int(datetime.now().timestamp())}"
        
        # Persist template to database
        from instabids.data_access import save_template  # local import to avoid circulars
        
        await save_template(
            template_id=template_id,
            project_id=project_id,
            template_type=template_type,
            template_data=template
        )
        
        # Emit A2A envelope for template created
        send_envelope("bidcard.created", {
            "template_id": template_id,
            "project_id": project_id,
            "template_type": template_type,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "agent_response": response.content,
            "template_id": template_id,
            "template": template
        }
    
    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    def _get_template_schema(self, template_type: str) -> Dict[str, Any]:
        """Get schema definition for a specific template type."""
        # In a real implementation, this would likely come from a database
        version = "1.0"  # Schema version
        
        # For now, return a hardcoded schema
        # In production, this would come from database or schema registry
        return {
            "schema_version": version,
            "required_sections": ["project_details", "scope_of_work", "pricing"],
            "field_rules": {
                "project_details": {
                    "required_fields": ["project_id", "category", "description"]
                },
                "scope_of_work": {
                    "min_length": 100,
                    "max_length": 5000
                },
                "pricing": {
                    "min_value": 100,
                    "max_value": 1000000
                }
            }
        }
    
    def _get_required_fields(self, template_type: str) -> List[str]:
        """Get list of required fields based on template type."""
        # Base required fields for all templates
        required_fields = [
            "project_id",
            "category",
            "description",
            "created_at"
        ]
        
        # Add template-type specific fields
        if template_type == "standard":
            required_fields.extend([
                "scope_of_work",
                "materials",
                "labor_costs",
                "total_estimate"
            ])
        elif template_type == "commercial":
            required_fields.extend([
                "contractor_license",
                "insurance_proof",
                "project_timeline",
                "payment_schedule"
            ])
        
        return required_fields