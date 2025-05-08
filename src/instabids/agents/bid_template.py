"""
Bid template module for generating standardized bid cards
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime

def create_bid_template(
    project_id: str,
    category: str,
    description: str,
    urgency: Optional[str] = None,
    template_type: str = "standard",
    version: str = "1.0"
) -> Dict[str, Any]:
    """
    Create a standardized bid template from project details.
    
    Args:
        project_id: UUID of the project
        category: Project category (e.g., repair, renovation)
        description: Project description
        urgency: Optional urgency level
        template_type: Template type (standard or commercial)
        version: Template version
        
    Returns:
        Dictionary with structured bid template
    """
    # Create base template
    template = {
        "template_id": str(uuid.uuid4()),
        "project_id": project_id,
        "template_type": template_type,
        "version": version,
        "created_at": datetime.now().isoformat(),
        "category": category,
        "description": description,
        "sections": _create_sections(category, description, urgency, template_type)
    }
    
    # Add template-specific fields
    if template_type == "standard":
        template["estimated_duration"] = _estimate_duration(category, description)
    elif template_type == "commercial":
        template["required_licenses"] = _get_required_licenses(category)
        template["insurance_requirements"] = _get_insurance_requirements(category)
        
    return template

def _create_sections(
    category: str,
    description: str,
    urgency: Optional[str],
    template_type: str
) -> List[Dict[str, Any]]:
    """Create template sections based on project details."""
    sections = [
        {
            "id": "project_details",
            "title": "Project Details",
            "required": True,
            "fields": [
                {"name": "title", "type": "text", "required": True},
                {"name": "category", "type": "select", "required": True},
                {"name": "job_type", "type": "text", "required": True},
                {"name": "location", "type": "text", "required": True},
                {"name": "timeline", "type": "text", "required": True},
            ]
        },
        {
            "id": "scope_of_work",
            "title": "Scope of Work",
            "required": True,
            "fields": [
                {"name": "description", "type": "textarea", "required": True},
                {"name": "materials", "type": "textarea", "required": False},
                {"name": "exclusions", "type": "textarea", "required": False},
            ]
        },
        {
            "id": "pricing",
            "title": "Pricing Information",
            "required": True,
            "fields": [
                {"name": "budget_range", "type": "text", "required": True},
                {"name": "payment_schedule", "type": "select", "required": False},
                {"name": "group_bidding", "type": "checkbox", "required": False},
            ]
        }
    ]
    
    # Add template-specific sections
    if template_type == "commercial":
        sections.append({
            "id": "compliance",
            "title": "Compliance Requirements",
            "required": True,
            "fields": [
                {"name": "licenses", "type": "multiselect", "required": True},
                {"name": "insurance", "type": "multiselect", "required": True},
                {"name": "certifications", "type": "multiselect", "required": False},
            ]
        })
    
    # Add urgency section if specified
    if urgency:
        sections.append({
            "id": "urgency",
            "title": "Urgency and Timeline",
            "required": True,
            "fields": [
                {"name": "urgency_level", "type": "select", "required": True},
                {"name": "completion_deadline", "type": "date", "required": True},
            ]
        })
        
    return sections

def _estimate_duration(category: str, description: str) -> str:
    """Estimate project duration based on category and description."""
    # Simple duration estimator - would be replaced with ML model in production
    duration_map = {
        "repair": "1-3 days",
        "maintenance": "1-2 days",
        "installation": "2-5 days",
        "renovation": "1-4 weeks",
        "construction": "4-12 weeks",
        "other": "2-4 weeks"
    }
    
    # Default to category estimate
    estimate = duration_map.get(category.lower(), "2-4 weeks")
    
    # Adjust based on description keywords
    if "minor" in description.lower() or "small" in description.lower():
        return "1-3 days"
    elif "major" in description.lower() or "extensive" in description.lower():
        return "4-8 weeks"
    elif "quick" in description.lower() or "urgent" in description.lower():
        return "1-2 days"
        
    return estimate

def _get_required_licenses(category: str) -> List[str]:
    """Get required licenses based on project category."""
    # Basic license requirements by category
    license_map = {
        "repair": ["General Contractor"],
        "maintenance": ["General Contractor"],
        "installation": ["General Contractor", "Specialty License"],
        "renovation": ["General Contractor", "Building Permit"],
        "construction": ["General Contractor", "Building Permit", "Engineering Approval"],
        "other": ["General Contractor"]
    }
    
    return license_map.get(category.lower(), ["General Contractor"])

def _get_insurance_requirements(category: str) -> Dict[str, float]:
    """Get insurance requirements based on project category."""
    # Basic insurance requirements by category (coverage amounts in USD)
    base_requirements = {
        "general_liability": 1000000.0,
        "workers_comp": 500000.0
    }
    
    # Adjust based on category
    if category.lower() in ["renovation", "construction"]:
        base_requirements["general_liability"] = 2000000.0
        base_requirements["property_damage"] = 500000.0
        
    return base_requirements
