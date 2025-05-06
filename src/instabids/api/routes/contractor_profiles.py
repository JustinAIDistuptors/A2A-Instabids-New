"""FastAPI router exposing CRUD endpoints for contractor profiles.

Authentication is assumed to be handled by a dependency injecting the user_id.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
import logging

# Assume agent is importable
try:
    from instabids.agents.contractor_profile_agent import ContractorProfileAgent
except ImportError:
    logging.error("Failed to import ContractorProfileAgent")
    # Define a dummy agent if import fails, for basic structure
    class DummyAgent:
        def create(self, user_id, payload): return {'id': 'new_dummy', 'user_id': user_id, **payload}
        def get(self, user_id): return {'id': 'dummy', 'user_id': user_id, 'display_name': 'Dummy Profile'}
        def update(self, user_id, updates): return {'id': 'dummy', 'user_id': user_id, **updates}
        def delete(self, user_id): pass
    ContractorProfileAgent = DummyAgent

# Pydantic Models for validation
class ContractorProfileBase(BaseModel):
    display_name: str = Field(..., min_length=1, description="Public display name of the contractor.")
    bio: Optional[str] = Field(None, description="Short biography or description.")
    trade: str = Field(..., min_length=1, description="Primary trade or specialization.")
    location: Optional[str] = Field(None, description="Service area or primary location.")
    license_number: Optional[str] = Field(None, description="Contractor license number, if applicable.")
    insurance_cert: Optional[str] = Field(None, description="Reference to insurance certificate (e.g., URL or ID).")
    google_reviews: Optional[list[Any]] = Field(default_factory=list, description="Cached Google reviews data.")
    internal_rating: Optional[float] = Field(0.0, ge=0, le=5, description="Internal rating score.")

class ContractorProfileCreate(ContractorProfileBase):
    pass # Inherits all fields, no extras needed for creation via payload

class ContractorProfileUpdate(BaseModel):
    # All fields are optional for updates
    display_name: Optional[str] = Field(None, min_length=1)
    bio: Optional[str] = None
    trade: Optional[str] = Field(None, min_length=1)
    location: Optional[str] = None
    license_number: Optional[str] = None
    insurance_cert: Optional[str] = None
    google_reviews: Optional[list[Any]] = None
    internal_rating: Optional[float] = Field(None, ge=0, le=5)

class ContractorProfileResponse(ContractorProfileBase):
    id: str # UUID stored as string
    user_id: str # UUID stored as string
    created_at: str # ISO 8601 format string
    updated_at: str # ISO 8601 format string

    class Config:
        orm_mode = True # Enable ORM mode for compatibility if using ORM later
        # Pydantic V2 uses from_attributes=True instead of orm_mode
        # from_attributes = True 

router = APIRouter(
    prefix="/contractor_profiles",
    tags=["Contractor Profiles"],
    # dependencies=[Depends(get_token_header)], # Example global dependency
    responses={404: {"description": "Not found"}},
)

_agent = ContractorProfileAgent()

# --- Dependency --- #
# Replace this with your actual authentication dependency later.
# This stub simulates getting a user ID, perhaps from a decoded JWT.
async def get_current_user_id() -> str:
    """Dependency to get the current user's ID. Replace with real auth."""
    # In a real app, this would decode a token, validate it, and return the user ID.
    # For testing/dev, you might return a hardcoded ID or use an API key map.
    # IMPORTANT: Replace this with actual authentication logic!
    user_id_stub = "f47ac10b-58cc-4372-a567-0e02b2c3d479" # Example UUID
    logging.warning(f"Using STUB authentication. Returning user_id: {user_id_stub}")
    return user_id_stub

# --- Routes --- #

@router.post(
    "/",
    response_model=ContractorProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new contractor profile for the current user",
    description="Creates a profile linked to the authenticated user's ID."
)
async def create_profile(
    payload: ContractorProfileCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Creates a contractor profile. The `user_id` is injected via auth dependency."""
    try:
        # The agent expects the user_id separately from the payload dict
        created_profile_data = _agent.create(user_id=user_id, payload=payload.dict())
        # Ensure the response matches the Pydantic model structure
        # The repo/agent should return data compatible with ContractorProfileResponse
        return ContractorProfileResponse.parse_obj(created_profile_data) 
    except Exception as e:
        logging.error(f"Error creating profile for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/me",
    response_model=ContractorProfileResponse,
    summary="Get the current user's profile",
    description="Retrieves the profile associated with the authenticated user."
)
async def read_own_profile(user_id: str = Depends(get_current_user_id)):
    """Gets the profile for the currently authenticated user."""
    profile_data = _agent.get(user_id)
    if not profile_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found for current user")
    return ContractorProfileResponse.parse_obj(profile_data)

@router.get(
    "/{profile_user_id}",
    response_model=ContractorProfileResponse,
    summary="Get a specific contractor profile by user ID",
    description="Retrieves a specific profile. Access control via RLS or service layer needed.",
    # dependencies=[Depends(require_admin_or_owner)], # Example finer-grained access
)
async def read_profile(
    profile_user_id: str, 
    # _current_user: str = Depends(get_current_user_id) # Optional: Inject current user for logging/checks
):
    """Gets a profile by its associated user ID. 
       Note: RLS policies in the DB should handle most access control.
       Additional checks can be added here if needed.
    """
    profile_data = _agent.get(profile_user_id)
    if not profile_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Profile not found for user_id {profile_user_id}")
    return ContractorProfileResponse.parse_obj(profile_data)

@router.put(
    "/me",
    response_model=ContractorProfileResponse,
    summary="Update the current user's profile",
    description="Allows the authenticated user to update their own profile."
)
async def update_own_profile(
    updates: ContractorProfileUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Updates the profile for the currently authenticated user."""
    try:
        # Pass only non-None values to the agent/repo for update
        update_data = updates.dict(exclude_unset=True)
        if not update_data:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")
        updated_profile_data = _agent.update(user_id, update_data)
        return ContractorProfileResponse.parse_obj(updated_profile_data)
    except ValueError as ve: # Catch specific error from repo if user not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logging.error(f"Error updating profile for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete the current user's profile",
    description="Allows the authenticated user to delete their own profile."
)
async def delete_own_profile(user_id: str = Depends(get_current_user_id)):
    """Deletes the profile for the currently authenticated user."""
    try:
        _agent.delete(user_id)
        # No content response on successful deletion
        return
    except Exception as e:
        logging.error(f"Error deleting profile for user {user_id}: {e}")
        # Deciding whether to expose details or return a generic error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting profile")

# Note: Routes for updating/deleting *other* users' profiles (e.g., by an admin)
# would typically require different dependencies (e.g., checking admin role)
# and would likely use '/{profile_user_id}' path parameters instead of '/me'.
