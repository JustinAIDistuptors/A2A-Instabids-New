"""
BidCard Agent

This module provides the BidCardAgent class, which is responsible for creating
and managing bid cards based on project information.
"""
import os
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple, Union

from instabids.data import bidcard_repo
from instabids.models.bid_card import BidCard

# Set up logging
logger = logging.getLogger(__name__)

# Category mapping for standardization
CATEGORY_MAPPING = {
    # Repair categories
    "roof repair": "repair",
    "plumbing repair": "repair",
    "electrical repair": "repair",
    "hvac repair": "repair",
    "appliance repair": "repair",
    "structural repair": "repair",
    "foundation repair": "repair",
    "water damage repair": "repair",
    "siding repair": "repair",
    "window repair": "repair",
    "door repair": "repair",
    
    # Renovation categories
    "kitchen renovation": "renovation",
    "bathroom renovation": "renovation",
    "basement renovation": "renovation",
    "attic renovation": "renovation",
    "home renovation": "renovation",
    "room addition": "renovation",
    "interior renovation": "renovation",
    
    # Installation categories
    "window installation": "installation",
    "door installation": "installation",
    "flooring installation": "installation",
    "appliance installation": "installation",
    "hvac installation": "installation",
    "solar panel installation": "installation",
    "security system installation": "installation",
    "smart home installation": "installation",
    
    # Maintenance categories
    "lawn maintenance": "maintenance",
    "pool maintenance": "maintenance",
    "hvac maintenance": "maintenance",
    "gutter cleaning": "maintenance",
    "chimney cleaning": "maintenance",
    "pest control": "maintenance",
    "seasonal maintenance": "maintenance",
    
    # Construction categories
    "new construction": "construction",
    "home building": "construction",
    "deck construction": "construction",
    "fence construction": "construction",
    "garage construction": "construction",
    "shed construction": "construction",
    "pool construction": "construction",
    
    # Default fallback
    "other": "other"
}

class BidCardAgent:
    """
    Agent for creating and managing bid cards based on project information.
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize the BidCardAgent.
        
        Args:
            project_id: Optional ID of the associated project
        """
        self.project_id = project_id
        self.memory = {}
    
    def map_category(self, job_type: str) -> str:
        """
        Map a job type to a standardized category.
        
        Args:
            job_type: The job type to map
            
        Returns:
            The standardized category
        """
        # Convert to lowercase for case-insensitive matching
        job_type_lower = job_type.lower()
        
        # Try direct match first
        if job_type_lower in CATEGORY_MAPPING:
            return CATEGORY_MAPPING[job_type_lower]
        
        # Try partial matching
        for key, category in CATEGORY_MAPPING.items():
            if key in job_type_lower:
                return category
        
        # Default to "other" if no match found
        return "other"
    
    def create_bid_card_from_project(
        self,
        homeowner_id: str,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a bid card from project data.
        
        Args:
            homeowner_id: ID of the homeowner
            project_data: Project data dictionary
            
        Returns:
            The created bid card record
        """
        # Extract job type
        job_type = project_data.get("job_type", "")
        if not job_type:
            raise ValueError("Job type is required to create a bid card")
        
        # Map to category
        category = self.map_category(job_type)
        
        # Extract budget range
        budget_str = project_data.get("budget", "")
        budget_min = None
        budget_max = None
        
        if budget_str:
            try:
                # Handle different budget formats
                if "-" in budget_str:
                    # Range format: "1000-5000"
                    parts = budget_str.replace("$", "").replace(",", "").split("-")
                    budget_min = float(parts[0].strip())
                    budget_max = float(parts[1].strip())
                elif "to" in budget_str.lower():
                    # Range format: "1000 to 5000"
                    parts = budget_str.lower().replace("$", "").replace(",", "").split("to")
                    budget_min = float(parts[0].strip())
                    budget_max = float(parts[1].strip())
                else:
                    # Single value format: "5000"
                    value = float(budget_str.replace("$", "").replace(",", ""))
                    # Set a range around the single value
                    budget_min = value * 0.8
                    budget_max = value * 1.2
            except (ValueError, IndexError):
                logger.warning(f"Could not parse budget string: {budget_str}")
        
        # Create the bid card
        bid_card = bidcard_repo.create_bid_card(
            homeowner_id=homeowner_id,
            project_id=self.project_id or str(uuid.uuid4()),
            category=category,
            job_type=job_type,
            budget_min=budget_min,
            budget_max=budget_max,
            timeline=project_data.get("timeline", ""),
            location=project_data.get("location", ""),
            group_bidding=project_data.get("group_bidding", False),
            details=self._extract_details(project_data)
        )
        
        return bid_card
    
    def _extract_details(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract additional details from project data.
        
        Args:
            project_data: Project data dictionary
            
        Returns:
            Dictionary of additional details
        """
        # Fields to exclude from details
        exclude_fields = [
            "job_type", "budget", "timeline", "location", "group_bidding",
            "id", "project_id", "homeowner_id", "created_at", "updated_at"
        ]
        
        # Extract all other fields as details
        details = {}
        for key, value in project_data.items():
            if key not in exclude_fields and value is not None:
                details[key] = value
        
        return details
    
    def update_bid_card(
        self,
        bid_card_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a bid card.
        
        Args:
            bid_card_id: ID of the bid card to update
            updates: Dictionary of fields to update
            
        Returns:
            The updated bid card record
        """
        # Process special fields
        if "job_type" in updates and "category" not in updates:
            updates["category"] = self.map_category(updates["job_type"])
        
        # Process budget updates
        if "budget" in updates and isinstance(updates["budget"], str):
            budget_str = updates["budget"]
            try:
                if "-" in budget_str:
                    parts = budget_str.replace("$", "").replace(",", "").split("-")
                    updates["budget_min"] = float(parts[0].strip())
                    updates["budget_max"] = float(parts[1].strip())
                elif "to" in budget_str.lower():
                    parts = budget_str.lower().replace("$", "").replace(",", "").split("to")
                    updates["budget_min"] = float(parts[0].strip())
                    updates["budget_max"] = float(parts[1].strip())
                else:
                    value = float(budget_str.replace("$", "").replace(",", ""))
                    updates["budget_min"] = value * 0.8
                    updates["budget_max"] = value * 1.2
            except (ValueError, IndexError):
                logger.warning(f"Could not parse budget string: {budget_str}")
            
            # Remove the original budget field
            del updates["budget"]
        
        # Update the bid card
        return bidcard_repo.update_bid_card(bid_card_id, updates)
    
    def get_bid_card(self, bid_card_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a bid card by ID.
        
        Args:
            bid_card_id: ID of the bid card to retrieve
            
        Returns:
            The bid card record or None if not found
        """
        return bidcard_repo.get_bid_card(bid_card_id)
    
    def get_bid_cards_for_project(self) -> List[Dict[str, Any]]:
        """
        Get all bid cards for the current project.
        
        Returns:
            List of bid card records
        """
        if not self.project_id:
            return []
        
        return bidcard_repo.get_bid_cards_by_project(self.project_id)
    
    def delete_bid_card(self, bid_card_id: str) -> bool:
        """
        Delete a bid card.
        
        Args:
            bid_card_id: ID of the bid card to delete
            
        Returns:
            True if successful, raises exception otherwise
        """
        return bidcard_repo.delete_bid_card(bid_card_id)