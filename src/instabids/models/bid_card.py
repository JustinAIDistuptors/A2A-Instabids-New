"""
Pydantic models for bid card data.

This module defines the data models for bid cards using Pydantic,
which provides validation, serialization, and documentation.
"""
from typing import List, Dict, Tuple, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import re

class BidCard(BaseModel):
    """
    Bid card model representing a project request with all required information.
    
    This model is used for validating bid card data and ensuring it meets
    the required format before processing.
    """
    id: str = Field(..., description="Unique identifier for the bid card")
    user_id: str = Field(..., description="ID of the user who created the bid card")
    category: str = Field(
        ..., 
        description="Project category (repair, renovation, installation, maintenance, construction, other)"
    )
    job_type: str = Field(..., description="Specific type of job (e.g., roof repair, lawn mowing)")
    budget_range: Tuple[int, int] = Field(
        ..., 
        description="Budget range in dollars [min, max]",
        example=[0, 10000]
    )
    timeline: str = Field(..., description="When the work should be done")
    location: str = Field(..., description="Location where the work will take place")
    group_bidding: bool = Field(
        ..., 
        description="Whether group bidding is allowed to potentially lower costs"
    )
    images: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of images related to the project"
    )
    description: Optional[str] = Field(
        None, 
        description="Detailed description of the project"
    )
    
    @validator('category')
    def validate_category(cls, v):
        """Validate that category is one of the allowed values."""
        allowed_categories = [
            'repair', 'renovation', 'installation', 
            'maintenance', 'construction', 'other'
        ]
        if v.lower() not in allowed_categories:
            raise ValueError(f"Category must be one of: {', '.join(allowed_categories)}")
        return v.lower()
    
    @validator('budget_range')
    def validate_budget_range(cls, v):
        """Validate that budget range is valid."""
        if len(v) != 2:
            raise ValueError("Budget range must be a tuple of [min, max]")
        if v[0] < 0 or v[1] < 0:
            raise ValueError("Budget values cannot be negative")
        if v[0] > v[1]:
            raise ValueError("Minimum budget cannot be greater than maximum budget")
        return v
    
    @validator('location')
    def validate_location(cls, v):
        """Validate that location is not empty."""
        if not v.strip():
            raise ValueError("Location cannot be empty")
        return v
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "bid-123456",
                "user_id": "user-789012",
                "category": "repair",
                "job_type": "roof repair",
                "budget_range": [1000, 5000],
                "timeline": "Next month",
                "location": "123 Main St, Anytown, USA",
                "group_bidding": True,
                "images": [
                    {
                        "url": "https://example.com/image1.jpg",
                        "description": "Damaged roof area"
                    }
                ],
                "description": "Need to repair leak in roof before rainy season."
            }
        }