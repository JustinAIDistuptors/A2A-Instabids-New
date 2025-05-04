"""
Bid Card Repository

This module provides functions for managing bid cards in the database.
"""
import os
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

from instabids.data.supabase_client import create_client

# Initialize Supabase client
_sb = create_client()

def create_bid_card(
    homeowner_id: str,
    project_id: str,
    category: str,
    job_type: str,
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    timeline: Optional[str] = None,
    location: Optional[str] = None,
    group_bidding: bool = False,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new bid card in the database.
    
    Args:
        homeowner_id: ID of the homeowner
        project_id: ID of the associated project
        category: Category of the job (repair, renovation, etc.)
        job_type: Specific type of job
        budget_min: Minimum budget amount
        budget_max: Maximum budget amount
        timeline: Expected timeline for the job
        location: Location of the job
        group_bidding: Whether group bidding is enabled
        details: Additional details as JSON
        
    Returns:
        The created bid card record
    """
    if details is None:
        details = {}
    
    # Validate category
    valid_categories = ['repair', 'renovation', 'installation', 'maintenance', 'construction', 'other']
    if category not in valid_categories:
        raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
    
    # Create the bid card
    response = _sb.table("bid_cards").insert({
        "homeowner_id": homeowner_id,
        "project_id": project_id,
        "category": category,
        "job_type": job_type,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "timeline": timeline,
        "location": location,
        "group_bidding": group_bidding,
        "details": details
    }).execute()
    
    if "error" in response:
        raise Exception(f"Error creating bid card: {response['error']}")
    
    return response.data[0]

def get_bid_card(bid_card_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a bid card by ID.
    
    Args:
        bid_card_id: ID of the bid card to retrieve
        
    Returns:
        The bid card record or None if not found
    """
    response = _sb.table("bid_cards").select("*").eq("id", bid_card_id).execute()
    
    if not response.data:
        return None
    
    return response.data[0]

def get_bid_cards_by_homeowner(homeowner_id: str) -> List[Dict[str, Any]]:
    """
    Get all bid cards for a homeowner.
    
    Args:
        homeowner_id: ID of the homeowner
        
    Returns:
        List of bid card records
    """
    response = _sb.table("bid_cards") \
        .select("*") \
        .eq("homeowner_id", homeowner_id) \
        .order("created_at", desc=True) \
        .execute()
    
    return response.data

def get_bid_cards_by_project(project_id: str) -> List[Dict[str, Any]]:
    """
    Get all bid cards for a project.
    
    Args:
        project_id: ID of the project
        
    Returns:
        List of bid card records
    """
    response = _sb.table("bid_cards") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("created_at", desc=True) \
        .execute()
    
    return response.data

def get_bid_cards_by_category(category: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get bid cards by category.
    
    Args:
        category: Category to filter by
        limit: Maximum number of records to return
        
    Returns:
        List of bid card records
    """
    response = _sb.table("bid_cards") \
        .select("*") \
        .eq("category", category) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    
    return response.data

def update_bid_card(
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
    # Ensure we're not trying to update protected fields
    protected_fields = ["id", "homeowner_id", "project_id", "created_at"]
    for field in protected_fields:
        if field in updates:
            del updates[field]
    
    # Add updated_at timestamp
    updates["updated_at"] = datetime.now().isoformat()
    
    response = _sb.table("bid_cards") \
        .update(updates) \
        .eq("id", bid_card_id) \
        .execute()
    
    if not response.data:
        raise Exception(f"Bid card with ID {bid_card_id} not found or you don't have permission to update it")
    
    return response.data[0]

def delete_bid_card(bid_card_id: str) -> bool:
    """
    Delete a bid card.
    
    Args:
        bid_card_id: ID of the bid card to delete
        
    Returns:
        True if successful, raises exception otherwise
    """
    response = _sb.table("bid_cards") \
        .delete() \
        .eq("id", bid_card_id) \
        .execute()
    
    if not response.data:
        raise Exception(f"Bid card with ID {bid_card_id} not found or you don't have permission to delete it")
    
    return True

def search_bid_cards(
    query: str,
    categories: Optional[List[str]] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search for bid cards based on various criteria.
    
    Args:
        query: Text search query
        categories: List of categories to filter by
        min_budget: Minimum budget filter
        max_budget: Maximum budget filter
        limit: Maximum number of records to return
        
    Returns:
        List of matching bid card records
    """
    # Start with a base query
    db_query = _sb.table("bid_cards").select("*")
    
    # Apply filters
    if categories:
        db_query = db_query.in_("category", categories)
    
    if min_budget is not None:
        db_query = db_query.gte("budget_min", min_budget)
    
    if max_budget is not None:
        db_query = db_query.lte("budget_max", max_budget)
    
    # Apply text search (basic implementation - would be better with full-text search)
    if query:
        db_query = db_query.or_(f"job_type.ilike.%{query}%,location.ilike.%{query}%")
    
    # Execute the query
    response = db_query.order("created_at", desc=True).limit(limit).execute()
    
    return response.data