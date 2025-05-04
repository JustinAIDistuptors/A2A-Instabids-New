"""
Bid Cards API Routes

This module provides FastAPI routes for managing bid cards.
"""
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel, Field

from instabids.data import bidcard_repo
from instabids.agents.bidcard_agent import BidCardAgent
from instabids.api.auth import get_current_user

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/bid-cards", tags=["bid-cards"])

# Pydantic models for request/response
class BidCardCreate(BaseModel):
    """Model for creating a bid card."""
    
    project_id: str = Field(..., description="ID of the associated project")
    category: str = Field(..., description="Category of the job")
    job_type: str = Field(..., description="Specific type of job")
    budget_min: Optional[float] = Field(None, description="Minimum budget amount")
    budget_max: Optional[float] = Field(None, description="Maximum budget amount")
    timeline: Optional[str] = Field(None, description="Expected timeline for the job")
    location: Optional[str] = Field(None, description="Location of the job")
    group_bidding: bool = Field(False, description="Whether group bidding is enabled")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

class BidCardUpdate(BaseModel):
    """Model for updating a bid card."""
    
    category: Optional[str] = Field(None, description="Category of the job")
    job_type: Optional[str] = Field(None, description="Specific type of job")
    budget_min: Optional[float] = Field(None, description="Minimum budget amount")
    budget_max: Optional[float] = Field(None, description="Maximum budget amount")
    timeline: Optional[str] = Field(None, description="Expected timeline for the job")
    location: Optional[str] = Field(None, description="Location of the job")
    group_bidding: Optional[bool] = Field(None, description="Whether group bidding is enabled")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

class BidCardResponse(BaseModel):
    """Model for bid card response."""
    
    id: str = Field(..., description="ID of the bid card")
    homeowner_id: str = Field(..., description="ID of the homeowner")
    project_id: str = Field(..., description="ID of the associated project")
    category: str = Field(..., description="Category of the job")
    job_type: str = Field(..., description="Specific type of job")
    budget_min: Optional[float] = Field(None, description="Minimum budget amount")
    budget_max: Optional[float] = Field(None, description="Maximum budget amount")
    timeline: Optional[str] = Field(None, description="Expected timeline for the job")
    location: Optional[str] = Field(None, description="Location of the job")
    group_bidding: bool = Field(False, description="Whether group bidding is enabled")
    details: Dict[str, Any] = Field({}, description="Additional details")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

# Routes
@router.post("", response_model=BidCardResponse)
async def create_bid_card(
    bid_card: BidCardCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new bid card.
    
    Args:
        bid_card: Bid card data
        current_user: Current authenticated user
        
    Returns:
        The created bid card
    """
    try:
        # Create bid card
        result = bidcard_repo.create_bid_card(
            homeowner_id=current_user["id"],
            project_id=bid_card.project_id,
            category=bid_card.category,
            job_type=bid_card.job_type,
            budget_min=bid_card.budget_min,
            budget_max=bid_card.budget_max,
            timeline=bid_card.timeline,
            location=bid_card.location,
            group_bidding=bid_card.group_bidding,
            details=bid_card.details or {}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating bid card: {e}")
        raise HTTPException(status_code=500, detail="Failed to create bid card")

@router.get("", response_model=List[BidCardResponse])
async def get_bid_cards(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get bid cards.
    
    Args:
        project_id: Optional project ID filter
        category: Optional category filter
        current_user: Current authenticated user
        
    Returns:
        List of bid cards
    """
    try:
        if project_id:
            # Get bid cards for a specific project
            return bidcard_repo.get_bid_cards_by_project(project_id)
        elif category:
            # Get bid cards by category
            return bidcard_repo.get_bid_cards_by_category(category)
        else:
            # Get all bid cards for the current user
            return bidcard_repo.get_bid_cards_by_homeowner(current_user["id"])
    except Exception as e:
        logger.error(f"Error getting bid cards: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bid cards")

@router.get("/{bid_card_id}", response_model=BidCardResponse)
async def get_bid_card(
    bid_card_id: str = Path(..., description="ID of the bid card to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a bid card by ID.
    
    Args:
        bid_card_id: ID of the bid card to retrieve
        current_user: Current authenticated user
        
    Returns:
        The bid card
    """
    try:
        # Get bid card
        bid_card = bidcard_repo.get_bid_card(bid_card_id)
        
        if not bid_card:
            raise HTTPException(status_code=404, detail="Bid card not found")
        
        return bid_card
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bid card: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bid card")

@router.put("/{bid_card_id}", response_model=BidCardResponse)
async def update_bid_card(
    bid_card_id: str = Path(..., description="ID of the bid card to update"),
    updates: BidCardUpdate = Body(..., description="Updates to apply"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a bid card.
    
    Args:
        bid_card_id: ID of the bid card to update
        updates: Updates to apply
        current_user: Current authenticated user
        
    Returns:
        The updated bid card
    """
    try:
        # Get the existing bid card
        existing_bid_card = bidcard_repo.get_bid_card(bid_card_id)
        
        if not existing_bid_card:
            raise HTTPException(status_code=404, detail="Bid card not found")
        
        # Check ownership
        if existing_bid_card["homeowner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this bid card")
        
        # Update bid card
        bid_card_agent = BidCardAgent(existing_bid_card["project_id"])
        result = bid_card_agent.update_bid_card(
            bid_card_id=bid_card_id,
            updates=updates.dict(exclude_unset=True)
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bid card: {e}")
        raise HTTPException(status_code=500, detail="Failed to update bid card")

@router.delete("/{bid_card_id}")
async def delete_bid_card(
    bid_card_id: str = Path(..., description="ID of the bid card to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a bid card.
    
    Args:
        bid_card_id: ID of the bid card to delete
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        # Get the existing bid card
        existing_bid_card = bidcard_repo.get_bid_card(bid_card_id)
        
        if not existing_bid_card:
            raise HTTPException(status_code=404, detail="Bid card not found")
        
        # Check ownership
        if existing_bid_card["homeowner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this bid card")
        
        # Delete bid card
        bidcard_repo.delete_bid_card(bid_card_id)
        
        return {"message": "Bid card deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bid card: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete bid card")