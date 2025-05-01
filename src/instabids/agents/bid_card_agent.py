"""BidCardAgent: standardizes project requests into structured bid templates."""
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime

from google.adk import LLMAgent, enable_tracing
from google.adk.messages import UserMessage
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
            memory=memory or PersistentMemory(),
        )
    
    # ────────────────────────────────────────────────────────────────────────
    # Public API used by FastAPI / CLI
    # ────────────────────────────────────────────────────────────────────────

    async def create_bidcard(
        self,
        project_id: str,
        template_type: str = "standard",
        version: str = "1.0"
    ) -> dict[str, Any]:
        """Main entry. Create a standardized bid card for a project."""
        
        # 1) Get project details from Supabase
        from instabids.data_access import get_project_details
        
        project = await get_project_details(project_id)
        
        # 2) Build prompt for ADK
        prompt = f"Create bid card for project {project_id} ({project['category']}): {project['description']}"
        user_msg = UserMessage(prompt)
        response = await self.chat(user_msg)
        
        # 3) Generate bid template
        bid_template = await self._generate_template(
            project, 
            template_type,
            version
        )
        
        # 4) Persist template to Supabase
        from instabids.data_access import save_bid_template
        
        template_id = await save_bid_template(
            project_id=project_id,
            template_type=template_type,
            version=version,
            content=bid_template,
            timestamp=datetime.now().isoformat()
        )
        
        # 5) Emit A2A envelope
        await send_envelope("bidcard.created", {
            "template_id": template_id,
            "project_id": project_id,
            "template_type": template_type,
            "version": version,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "agent_response": response.content,
            "template_id": template_id,
            "bid_template": bid_template
        }
    
    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    async def _generate_template(
        self,
        project: Dict[str, Any],
        template_type: str,
        version: str
    ) -> Dict[str, Any]:
        """Generate standardized bid template from project details."""
        # 1) Create base template
        template = create_bid_template(
            project_id=project["id"],
            category=project["category"],
            description=project["description"],
            urgency=project["urgency"],
            template_type=template_type,
            version=version
        )
        
        # 2) Add validation rules
        validation_rules = await self._get_validation_rules(template_type, version)
        template["validation_rules"] = validation_rules
        
        # 3) Add required fields
        template["required_fields"] = self._get_required_fields(template_type)
        
        return template
    
    async def _get_validation_rules(self, template_type: str, version: str) -> Dict[str, Any]:
        """Get validation rules for template type and version."""
        # This would typically come from a rules engine or database
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
