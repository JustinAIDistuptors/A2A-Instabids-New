"""
API routes for user feedback.

This module provides endpoints for submitting and retrieving user feedback.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from instabids.data import pref_repo

# Create router
router = APIRouter(prefix="/feedback")

class FeedbackRequest(BaseModel):
    """Request model for submitting feedback."""
    user_id: str = Field(..., description="User ID")
    rating: int = Field(..., description="Rating (1-5)", ge=1, le=5)
    comments: Optional[str] = Field("", description="Optional feedback comments")

@router.post("/")
def give_feedback(feedback: FeedbackRequest) -> Dict[str, Any]:
    """
    Submit user feedback.
    
    Args:
        feedback: Feedback request containing user_id, rating, and optional comments
        
    Returns:
        Status response
        
    Raises:
        HTTPException: If the rating is invalid or there's a database error
    """
    try:
        # Validate rating
        if not 1 <= feedback.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Insert feedback into database
        pref_repo._sb.table("user_feedback").insert({
            "user_id": feedback.user_id,
            "rating": feedback.rating,
            "comments": feedback.comments
        }).execute()
        
        return {"ok": True, "message": "Feedback submitted successfully"}
    
    except Exception as e:
        # Log the error
        import logging
        logging.error(f"Error submitting feedback: {e}")
        
        # Return error response
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.get("/{user_id}")
def get_user_feedback(user_id: str) -> Dict[str, Any]:
    """
    Get feedback history for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary containing user feedback history
        
    Raises:
        HTTPException: If there's a database error
    """
    try:
        # Query feedback from database
        result = pref_repo._sb.table("user_feedback").select("*") \
                 .eq("user_id", user_id).order("created_at", desc=True).execute()
        
        return {"feedback": result.data}
    
    except Exception as e:
        # Log the error
        import logging
        logging.error(f"Error retrieving feedback: {e}")
        
        # Return error response
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback")