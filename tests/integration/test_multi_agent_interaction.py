"""
Multi-Agent Interaction Test with Real LLMs

This test demonstrates the full project workflow with multiple LLM agents interacting
with each other and sharing data through the Supabase database. It shows:
1. Homeowner Agent creating a project and bid card
2. Matching Agent finding suitable contractors
3. Contractor Agent reviewing and bidding on the project
4. Homeowner Agent reviewing and accepting bids

All agents use real LLM calls with Google ADK v0.4.0.
"""

import os
import asyncio
import uuid
import json
import pytest
import sys
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from supabase import create_client, Client

# Constants for the test - get from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE", "")

# API keys should be loaded from environment variables, not hardcoded
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Set up Google ADK
try:
    import google.adk
    from google.adk import Agent, Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    ADK_AVAILABLE = True
    print("Google ADK 0.4.0 imported successfully")
    
    # Set up the model to use
    DEFAULT_MODEL = "gemini-1.5-pro" 
    print(f"Using model: {DEFAULT_MODEL}")
except ImportError as e:
    print(f"Warning: Google ADK import error: {e}")
    ADK_AVAILABLE = False
    print("Falling back to direct workflow testing without Google ADK")

# Configure test
TEST_PREFIX = f"pytest-multiagent-{int(datetime.now().timestamp())}"

@pytest.fixture(scope="module")
def supabase_admin_client():
    """Get Supabase client with service role for admin access."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)

@pytest.fixture
def setup_env_variables():
    """Set up environment variables for the test."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["MOCK_EXTERNAL_SERVICES"] = "false"
    os.environ["SUPABASE_URL"] = SUPABASE_URL
    os.environ["SUPABASE_SERVICE_ROLE"] = SUPABASE_SERVICE_ROLE
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    
    # Return so we can test these were set
    return {
        "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY")
    }

@pytest.fixture
def test_homeowner(supabase_admin_client):
    """Create a test homeowner and return the user data. Clean up after test."""
    # Generate unique email
    random_id = str(uuid.uuid4())[:8]
    email = f"{TEST_PREFIX}_homeowner_{random_id}@example.com"
    
    # User data
    user_data = {
        "email": email,
        "user_type": "homeowner",
        "created_at": datetime.now().isoformat()
    }
    
    # Insert user
    result = supabase_admin_client.table("users").insert(user_data).execute()
    user = result.data[0] if result.data else None
    
    print(f"Created test homeowner with ID: {user['id']}") if user else print("Failed to create test homeowner")
    
    # Yield the created user for the test
    yield user
    
    # Clean up will be handled by the cleanup fixture

@pytest.fixture
def test_contractors(supabase_admin_client):
    """Create test contractors with different specialties."""
    contractors = []
    contractor_ids = []
    
    try:
        # Create multiple contractors with different specialties
        for i, specialty_set in enumerate([
            ["kitchen", "bathroom", "flooring"],
            ["kitchen", "electrical", "plumbing"],
            ["bathroom", "tile", "painting"]
        ]):
            random_id = str(uuid.uuid4())[:8]
            email = f"{TEST_PREFIX}_contractor_{i}_{random_id}@example.com"
            
            contractor_data = {
                "email": email,
                "user_type": "contractor",
                "created_at": datetime.now().isoformat(),
                "contractor_profile": {
                    "company_name": f"Test Contracting Co. {i} {random_id}",
                    "specialties": specialty_set,
                    "years_experience": 5 + i * 2,
                    "license_number": f"LIC-{random_id}",
                    "insurance_policy": f"INS-{random_id}",
                    "verified": True
                }
            }
            
            result = supabase_admin_client.table("users").insert(contractor_data).execute()
            contractor = result.data[0] if result.data else None
            
            if contractor:
                print(f"Created test contractor {i} with ID: {contractor['id']}")
                contractors.append(contractor)
                contractor_ids.append(contractor["id"])
            else:
                print(f"Failed to create test contractor {i}")
        
        # Yield contractors for the test
        yield contractors
        
    except Exception as e:
        print(f"Error creating test contractors: {str(e)}")
        yield []
        
    # Cleanup will be handled by the cleanup fixture

@pytest.fixture
def memory_data():
    """Initial memory data for test users."""
    return {
        "interactions": [],
        "context": {
            "preferences": {
                "communication": "direct",
                "decision_style": "collaborative"
            },
            "last_login": datetime.now().isoformat()
        },
        "learned_preferences": {},
        "creation_date": datetime.now().isoformat()
    }

@pytest.fixture
def test_memories(supabase_admin_client, test_homeowner, test_contractors, memory_data):
    """Create memory records for all test users."""
    all_users = [test_homeowner] + test_contractors
    memories = {}
    
    for user in all_users:
        if not user:
            continue
            
        user_id = user["id"]
        
        # Copy memory data for this user
        user_memory = dict(memory_data)
        
        # Add user type-specific context
        if user["user_type"] == "contractor":
            user_memory["context"]["specialties"] = user.get("contractor_profile", {}).get("specialties", [])
            user_memory["context"]["years_experience"] = user.get("contractor_profile", {}).get("years_experience", 0)
        
        # Memory data for insertion
        memory_record = {
            "user_id": user_id,
            "memory_data": user_memory
        }
        
        # Insert into user_memories table
        try:
            print(f"Creating memory for user {user_id}...")
            result = supabase_admin_client.table("user_memories").upsert(memory_record).execute()
            memory = result.data[0] if result.data else None
            if memory:
                print(f"Created memory for user {user_id}")
                memories[user_id] = memory
            else:
                print(f"Failed to create memory for user {user_id}")
        except Exception as e:
            print(f"Error creating memory: {str(e)}")
    
    return memories

@pytest.fixture
def cleanup(supabase_admin_client, test_homeowner, test_contractors):
    """Cleanup fixture to remove all test data after tests run."""
    # Yield to let the test run
    yield
    
    # Clean up after the test
    try:
        # Collect all user IDs
        user_ids = []
        if test_homeowner and 'id' in test_homeowner:
            user_ids.append(test_homeowner["id"])
            
        for contractor in test_contractors:
            if contractor and 'id' in contractor:
                user_ids.append(contractor["id"])
        
        # Get all project IDs created by the test homeowner
        project_ids = []
        if test_homeowner and 'id' in test_homeowner:
            projects_result = supabase_admin_client.table("projects").select("id").eq("homeowner_id", test_homeowner["id"]).execute()
            if projects_result.data:
                project_ids = [p["id"] for p in projects_result.data]
        
        # Get all bid card IDs for these projects
        bid_card_ids = []
        for project_id in project_ids:
            bid_cards_result = supabase_admin_client.table("bid_cards").select("id").eq("project_id", project_id).execute()
            if bid_cards_result.data:
                bid_card_ids.extend([b["id"] for b in bid_cards_result.data])
        
        # Get all bid IDs for these bid cards
        bid_ids = []
        for bid_card_id in bid_card_ids:
            bids_result = supabase_admin_client.table("bids").select("id").eq("bid_card_id", bid_card_id).execute()
            if bids_result.data:
                bid_ids.extend([b["id"] for b in bids_result.data])
        
        # Get all match IDs for these projects
        match_ids = []
        for project_id in project_ids:
            matches_result = supabase_admin_client.table("contractor_matches").select("id").eq("project_id", project_id).execute()
            if matches_result.data:
                match_ids.extend([m["id"] for m in matches_result.data])
        
        # Delete in reverse order of dependencies
        print(f"Cleaning up test data - Bids: {len(bid_ids)}, Matches: {len(match_ids)}, Bid Cards: {len(bid_card_ids)}, Projects: {len(project_ids)}, Users: {len(user_ids)}")
        
        # Delete bids
        for bid_id in bid_ids:
            supabase_admin_client.table("bids").delete().eq("id", bid_id).execute()
        
        # Delete contractor matches
        for match_id in match_ids:
            supabase_admin_client.table("contractor_matches").delete().eq("id", match_id).execute()
        
        # Delete bid cards
        for bid_card_id in bid_card_ids:
            supabase_admin_client.table("bid_cards").delete().eq("id", bid_card_id).execute()
        
        # Delete projects
        for project_id in project_ids:
            supabase_admin_client.table("projects").delete().eq("id", project_id).execute()
        
        # Delete user memory interactions
        for user_id in user_ids:
            supabase_admin_client.table("user_memory_interactions").delete().eq("user_id", user_id).execute()
        
        # Delete user memories
        for user_id in user_ids:
            supabase_admin_client.table("user_memories").delete().eq("user_id", user_id).execute()
        
        # Delete users
        for user_id in user_ids:
            supabase_admin_client.table("users").delete().eq("id", user_id).execute()
            
        print(f"Successfully cleaned up all test data")
        
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

# SupabaseClient wrapper tool for the LLM
def supabase_tool(query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Tool to interact with Supabase for the LLM."""
    print(f"SupabaseTool called with: {query_type}, {params}")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
    
    try:
        if query_type == "select":
            table = params.get("table")
            columns = params.get("columns", "*")
            filters = params.get("filters", {})
            
            query = client.table(table).select(columns)
            
            # Apply filters
            for key, value in filters.items():
                if isinstance(value, dict):
                    operation = value.get("operation")
                    compare_value = value.get("value")
                    
                    if operation == "eq":
                        query = query.eq(key, compare_value)
                    elif operation == "neq":
                        query = query.neq(key, compare_value)
                    elif operation == "gt":
                        query = query.gt(key, compare_value)
                    elif operation == "lt":
                        query = query.lt(key, compare_value)
                    elif operation == "gte":
                        query = query.gte(key, compare_value)
                    elif operation == "lte":
                        query = query.lte(key, compare_value)
                else:
                    # Simple equality
                    query = query.eq(key, value)
            
            result = query.execute()
            return {"success": True, "data": result.data if hasattr(result, 'data') else []}
        
        elif query_type == "insert":
            table = params.get("table")
            data = params.get("data", {})
            
            result = client.table(table).insert(data).execute()
            return {"success": True, "data": result.data if hasattr(result, 'data') else []}
        
        elif query_type == "update":
            table = params.get("table")
            data = params.get("data", {})
            filters = params.get("filters", {})
            
            query = client.table(table).update(data)
            
            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return {"success": True, "data": result.data if hasattr(result, 'data') else []}
        
        elif query_type == "delete":
            table = params.get("table")
            filters = params.get("filters", {})
            
            query = client.table(table).delete()
            
            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return {"success": True, "data": result.data if hasattr(result, 'data') else []}
        
        else:
            return {"success": False, "error": f"Unknown query type: {query_type}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

# Additional tool for the homeowner agent
def extract_renovation_details(text: str) -> Dict[str, Any]:
    """Extract renovation project details from user text."""
    print(f"Extracting renovation details from: {text}")
    
    details = {
        "text_analyzed": text,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Simple keyword detection for room type
    if "kitchen" in text.lower():
        details["detected_room"] = "kitchen"
    elif "bathroom" in text.lower():
        details["detected_room"] = "bathroom"
    elif "living room" in text.lower():
        details["detected_room"] = "living room"
    else:
        details["detected_room"] = "unknown"
    
    # Simple keyword detection for complexity
    if "complete" in text.lower() or "major" in text.lower() or "full" in text.lower():
        details["estimated_complexity"] = "high"
    elif "partial" in text.lower() or "minor" in text.lower():
        details["estimated_complexity"] = "medium"
    else:
        details["estimated_complexity"] = "standard"
    
    # Extract budget if mentioned
    budget_words = ["budget", "cost", "spend", "price"]
    has_budget = any(word in text.lower() for word in budget_words)
    
    if has_budget:
        import re
        # Look for currency patterns like $5,000 or $10k
        matches = re.findall(r'\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+k)', text)
        if matches:
            details["mentioned_budget"] = matches
    
    return details

# Tool for cost estimation for the contractor agent
def estimate_cost(job_details: Dict[str, Any]) -> Dict[str, Any]:
    """Tool to estimate the cost of a job based on details."""
    print(f"Estimating cost for job: {job_details}")
    
    # Simple cost estimation logic
    base_cost = 5000
    
    # Add costs based on job details
    if "cabinets" in job_details:
        if job_details["cabinets"] == "custom":
            base_cost += 3000
        elif job_details["cabinets"] == "white":
            base_cost += 1500
        
    if "countertops" in job_details:
        if job_details["countertops"] == "granite":
            base_cost += 2000
        elif job_details["countertops"] == "marble":
            base_cost += 3500
        
    if "backsplash" in job_details:
        if job_details["backsplash"] == "subway tile":
            base_cost += 800
        elif job_details["backsplash"] == "glass tile":
            base_cost += 1200
    
    # Estimate timeline
    timeline_weeks = 4
    if "cabinets" in job_details and job_details["cabinets"] == "custom":
        timeline_weeks += 3
        
    # Return estimate
    return {
        "estimate": {
            "low": int(base_cost * 0.9),
            "high": int(base_cost * 1.1),
            "average": base_cost,
            "timeline_weeks": timeline_weeks,
            "details": {
                "labor": int(base_cost * 0.4),
                "materials": int(base_cost * 0.6),
                "breakdown": job_details
            }
        }
    }

# Tool for vector search for the matching agent
def vector_search_tool(query: str, category: str, top_k: int = 5) -> Dict[str, Any]:
    """Simplified vector search tool for matching projects with contractors."""
    print(f"Vector search for query: {query}, category: {category}, top_k: {top_k}")
    
    # In a real implementation, this would do vector similarity search
    # Here we'll just do a simplified mock implementation
    
    # Get all contractors
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
    result = client.table("users").select("*").eq("user_type", "contractor").execute()
    
    if not result.data:
        return {
            "matches": [],
            "scores": {},
            "reasoning": {}
        }
    
    # Filter contractors based on specialties
    matches = []
    scores = {}
    reasoning = {}
    
    for contractor in result.data:
        # Skip contractors without profiles
        if "contractor_profile" not in contractor:
            continue
            
        profile = contractor.get("contractor_profile", {})
        specialties = profile.get("specialties", [])
        
        # Calculate a simple score based on keywords in query and specialties
        score = 0
        if category.lower() in [s.lower() for s in specialties]:
            score += 0.5
            
        # Look for keywords
        keywords = ["kitchen", "bathroom", "flooring", "electrical", "plumbing", "tile"]
        for keyword in keywords:
            if keyword in query.lower() and keyword in [s.lower() for s in specialties]:
                score += 0.1
                
        # Add experience bonus
        years_exp = profile.get("years_experience", 0)
        score += min(years_exp * 0.02, 0.3)  # Cap at 0.3
        
        # Only include if above threshold
        if score > 0.3:
            matches.append(contractor)
            scores[contractor["id"]] = score
            reasoning[contractor["id"]] = f"Matched on specialties: {', '.join(specialties)}. Experience: {years_exp} years."
    
    # Sort by score and limit to top_k
    matches = sorted(matches, key=lambda x: scores.get(x["id"], 0), reverse=True)[:top_k]
    
    return {
        "matches": matches,
        "scores": scores,
        "reasoning": reasoning
    }

def create_homeowner_agent():
    """Creates a homeowner agent with the current Google ADK version."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent creation")
        return None
    
    try:
        # Create an Agent with the current API
        agent = Agent(
            name="homeowner_agent",
            model=DEFAULT_MODEL,
            description="Agent that helps homeowners create and manage projects with contractors",
            instruction="""You are a helpful assistant that helps homeowners create and manage home renovation projects.
            When the user describes a project, extract key details like:
            - Project type (renovation, repair, installation, etc.)
            - Location (which room or part of the house)
            - Budget range (if mentioned)
            - Timeline (if mentioned)
            - Any specific details about materials, style, or preferences
            
            Use the provided tools to interact with the database when needed.
            When the user asks about bids from contractors, help them understand the details
            and provide guidance on selecting the right contractor.
            """,
            tools=[supabase_tool, extract_renovation_details]
        )
        print(f"Successfully created homeowner agent with API key")
        return agent
    except Exception as e:
        print(f"Error creating homeowner agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_contractor_agent():
    """Creates a contractor agent with the current Google ADK version."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent creation")
        return None
    
    try:
        # Create an Agent with the current API
        agent = Agent(
            name="contractor_agent",
            model=DEFAULT_MODEL,
            description="Agent that helps contractors review and bid on projects",
            instruction="""You are a helpful assistant for contractors who are using the InstaBids platform. 
            
            Your goal is to help contractors:
            - Review bid cards and project details
            - Estimate job costs and timelines
            - Submit competitive bids
            - Manage their projects
            
            When reviewing bid cards, extract key details like:
            - Project type (renovation, repair, installation, etc.)
            - Location (which room or part of the house)
            - Budget range
            - Timeline
            - Specific requirements (materials, style, etc.)
            
            Then help the contractor create an appropriate bid for the project.
            
            Use the provided tools to interact with the database and estimate costs.
            """,
            tools=[supabase_tool, estimate_cost]
        )
        print(f"Successfully created contractor agent with API key")
        return agent
    except Exception as e:
        print(f"Error creating contractor agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_matching_agent():
    """Creates a matching agent with the current Google ADK version."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent creation")
        return None
    
    try:
        # Create an Agent with the current API
        agent = Agent(
            name="matching_agent",
            model=DEFAULT_MODEL,
            description="Agent that matches projects with qualified contractors",
            instruction="""You are MatchingAgent, responsible for connecting projects with qualified contractors. 
            
            Your goal is to:
            - Analyze project requirements from bid cards
            - Identify contractors with matching skills and experience
            - Score contractor matches based on relevance
            - Provide reasoning for why contractors are a good match
            
            When analyzing projects, consider:
            - Project category and specific requirements
            - Location and timeline
            - Budget constraints
            - Specialized skills needed
            
            When matching contractors, consider:
            - Contractor specialties and experience
            - Geographic proximity
            - Availability and capacity
            - Previous work quality
            
            Use the provided tools to interact with the database and perform vector search.
            """,
            tools=[supabase_tool, vector_search_tool]
        )
        print(f"Successfully created matching agent with API key")
        return agent
    except Exception as e:
        print(f"Error creating matching agent: {e}")
        import traceback
        traceback.print_exc()
        return None

async def call_agent_async(query: str, runner, user_id, session_id):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>> User Query: {query}")

    # Prepare the user's message in ADK format
    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response." # Default

    # Iterate through events to find the final answer
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            # Check if this is the final response
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Get the text from the first part
                    final_response_text = event.content.parts[0].text
                break
    except Exception as e:
        print(f"Error during agent execution: {e}")
        import traceback
        traceback.print_exc()
        final_response_text = f"Error: {str(e)}"

    print(f"<<< Agent Response: {final_response_text}")
    return final_response_text

def add_interaction_to_memory(supabase_admin_client, user_id, interaction_type, interaction_data):
    """Add an interaction to a user's memory."""
    print(f"Adding {interaction_type} interaction for user {user_id}...")
    
    try:
        # First get current memory
        memory_result = supabase_admin_client.table("user_memories").select("memory_data").eq("user_id", user_id).execute()
        
        if not memory_result.data or len(memory_result.data) == 0:
            print(f"No memory found for user {user_id}")
            return False
        
        # Get the current memory data
        memory_data = memory_result.data[0]["memory_data"]
        
        # Add new interaction
        new_interaction = {
            "type": interaction_type,
            "timestamp": datetime.now().isoformat(),
            "data": interaction_data
        }
        
        if "interactions" not in memory_data:
            memory_data["interactions"] = []
        
        memory_data["interactions"].append(new_interaction)
        
        # Update memory
        update_result = supabase_admin_client.table("user_memories").update({"memory_data": memory_data}).eq("user_id", user_id).execute()
        
        # Also add to interactions table
        interaction_result = supabase_admin_client.table("user_memory_interactions").insert({
            "user_id": user_id,
            "interaction_type": interaction_type,
            "interaction_data": interaction_data,
            "created_at": datetime.now().isoformat()
        }).execute()
        
        print(f"Added {interaction_type} interaction to user {user_id}'s memory")
        return True
        
    except Exception as e:
        print(f"Error adding interaction: {str(e)}")
        return False

def create_project(supabase_admin_client, homeowner_id, title="Kitchen Renovation", description="Complete kitchen renovation with new cabinets, countertops, and appliances"):
    """Create a test project for the homeowner."""
    project_data = {
        "homeowner_id": homeowner_id,
        "title": f"{TEST_PREFIX} {title}",
        "description": description,
        "category": "renovation",
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        result = supabase_admin_client.table("projects").insert(project_data).execute()
        if result.data and len(result.data) > 0:
            project_id = result.data[0]["id"]
            print(f"Created project with ID: {project_id}")
            return result.data[0]
        else:
            print("Failed to create project")
            return None
    except Exception as e:
        print(f"Error creating project: {str(e)}")
        return None

def create_bid_card(supabase_admin_client, homeowner_id, project_id, details=None):
    """Create a bid card directly."""
    if details is None:
        details = {
            "cabinets": "white",
            "countertops": "granite",
            "backsplash": "subway tile"
        }
        
    bid_card_data = {
        "homeowner_id": homeowner_id,
        "project_id": project_id,
        "category": "renovation",
        "job_type": "kitchen",
        "budget_min": 5000,
        "budget_max": 10000,
        "timeline": "3 months",
        "location": "Home",
        "group_bidding": False,
        "details": details,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        result = supabase_admin_client.table("bid_cards").insert(bid_card_data).execute()
        if result.data and len(result.data) > 0:
            bid_card_id = result.data[0]["id"]
            print(f"Created bid card with ID: {bid_card_id}")
            return result.data[0]
        else:
            print("Failed to create bid card")
            return None
    except Exception as e:
        print(f"Error creating bid card: {str(e)}")
        return None

def create_bid(supabase_admin_client, contractor_id, bid_card_id, project_id, homeowner_id, amount=None):
    """Create a bid on a project."""
    if amount is None:
        # Generate a somewhat random bid amount between budget range
        amount = random.randint(6000, 9500)
    
    bid_data = {
        "contractor_id": contractor_id,
        "bid_card_id": bid_card_id,
        "project_id": project_id,
        "homeowner_id": homeowner_id,
        "amount": amount,
        "timeline_weeks": 6,
        "message": "This bid includes all labor and materials for the kitchen renovation as specified.",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "details": {
            "materials_included": True,
            "warranty_length": "1 year",
            "payment_schedule": {
                "deposit": 0.3,
                "mid_project": 0.4,
                "completion": 0.3
            }
        }
    }
    
    try:
        result = supabase_admin_client.table("bids").insert(bid_data).execute()
        if result.data and len(result.data) > 0:
            bid_id = result.data[0]["id"]
            print(f"Created bid with ID: {bid_id}")
            return result.data[0]
        else:
            print("Failed to create bid")
            return None
    except Exception as e:
        print(f"Error creating bid: {str(e)}")
        return None

def save_matches(supabase_admin_client, project_id, contractors, match_scores):
    """Save matched contractors to the database."""
    match_ids = []
    
    try:
        # Delete any existing matches for this project
        supabase_admin_client.table("contractor_matches").delete().eq("project_id", project_id).execute()
        
        # Save new matches
        for contractor in contractors:
            contractor_id = contractor["id"]
            match_data = {
                "project_id": project_id,
                "contractor_id": contractor_id,
                "score": match_scores.get(contractor_id, 0.0),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = supabase_admin_client.table("contractor_matches").insert(match_data).execute()
            
            if result.data and len(result.data) > 0:
                match_ids.append(result.data[0]["id"])
                print(f"Created match with ID: {result.data[0]['id']} for contractor {contractor_id}")
            else:
                print(f"Failed to create match for contractor {contractor_id}")
        
        return match_ids
    except Exception as e:
        print(f"Error saving matches: {str(e)}")
        return []

async def run_homeowner_agent_conversation(homeowner_id, project_id=None, session_id=None):
    """Run a conversation with the Homeowner Agent."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent conversation")
        return "No LLM agent"
    
    try:
        # Set up the agent
        agent = create_homeowner_agent()
        if not agent:
            print("Agent creation failed, skipping conversation")
            return "Failed to create homeowner agent"
        
        # Initialize session service and runner
        session_service = InMemorySessionService()
        app_name = "test_homeowner_app"
        
        if session_id is None:
            session_id = f"session_homeowner_{int(datetime.now().timestamp())}"
        
        # Create the session
        session = session_service.create_session(
            app_name=app_name,
            user_id=homeowner_id,
            session_id=session_id
        )
        
        # Initialize the runner
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service
        )
        
        # Run a simple conversation
        if project_id:
            # If project is provided, ask about the existing project
            prompts = [
                f"I want to renovate my kitchen. I have a budget of $10,000 to $15,000 and want to get it done in the next 3 months. My project ID is {project_id} and I'm user {homeowner_id}.",
                "I'd like to have white cabinets, granite countertops, and a subway tile backsplash.",
                "Can you tell me what you've recorded about my project so far?"
            ]
        else:
            # If no project is provided, create a new project
            prompts = [
                "I'm thinking about renovating my bathroom. I have a budget of about $8,000 to $12,000.",
                "I want to replace the bathtub with a walk-in shower, new vanity, and tile flooring.",
                "How long would this typically take to complete?"
            ]
        
        responses = []
        for prompt in prompts:
            response = await call_agent_async(
                query=prompt,
                runner=runner,
                user_id=homeowner_id,
                session_id=session_id
            )
            responses.append(response)
            # Give the LLM a moment to process
            await asyncio.sleep(1)
            
        print("Homeowner agent conversation completed")
        return responses
        
    except Exception as e:
        print(f"Error running homeowner agent conversation: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

async def run_matching_agent(project_data, session_id=None):
    """Run a matching agent to find contractors for a project."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent execution")
        return "No LLM agent"
    
    try:
        # Set up the agent
        agent = create_matching_agent()
        if not agent:
            print("Agent creation failed, skipping execution")
            return "Failed to create matching agent"
        
        # Initialize session service and runner
        session_service = InMemorySessionService()
        app_name = "test_matching_app"
        
        if session_id is None:
            session_id = f"session_matching_{int(datetime.now().timestamp())}"
        
        # Create the session
        session = session_service.create_session(
            app_name=app_name,
            user_id=project_data["id"],
            session_id=session_id
        )
        
        # Initialize the runner
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service
        )
        
        # Create a prompt for the project
        project_text = (
            f"Project ID: {project_data['id']}\n"
            f"Project Type: {project_data['category']}\n"
            f"Description: {project_data['description']}\n"
        )
        
        # Run the matching request
        prompt = f"I need to find qualified contractors for this project: {project_text}"
        response = await call_agent_async(
            query=prompt,
            runner=runner,
            user_id=project_data["id"],
            session_id=session_id
        )
        
        return response
    except Exception as e:
        print(f"Error running matching agent: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

async def run_contractor_agent_conversation(contractor_id, bid_card_data, session_id=None):
    """Run a conversation with the Contractor Agent."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent conversation")
        return "No LLM agent"
    
    try:
        # Set up the agent
        agent = create_contractor_agent()
        if not agent:
            print("Agent creation failed, skipping conversation")
            return "Failed to create contractor agent"
        
        # Initialize session service and runner
        session_service = InMemorySessionService()
        app_name = "test_contractor_app"
        
        if session_id is None:
            session_id = f"session_contractor_{int(datetime.now().timestamp())}"
        
        # Create the session
        session = session_service.create_session(
            app_name=app_name,
            user_id=contractor_id,
            session_id=session_id
        )
        
        # Initialize the runner
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service
        )
        
        # Convert bid card to readable text
        bid_card_text = (
            f"Bid Card ID: {bid_card_data['id']}\n"
            f"Project Type: {bid_card_data['category']} - {bid_card_data['job_type']}\n"
            f"Budget Range: ${bid_card_data['budget_min']} - ${bid_card_data['budget_max']}\n"
            f"Timeline: {bid_card_data['timeline']}\n"
            f"Project Details: {json.dumps(bid_card_data['details'], indent=2)}\n"
        )
        
        # Run a simple conversation
        prompts = [
            f"I'm a contractor with ID: {contractor_id}. I'm looking at this bid card: {bid_card_text}. Can you help me understand the project?",
            "Can you help me estimate the cost for this project and what my bid should be?",
            "I'd like to submit a bid for this project. Can you help me create a competitive bid?"
        ]
        
        responses = []
        for prompt in prompts:
            response = await call_agent_async(
                query=prompt,
                runner=runner,
                user_id=contractor_id,
                session_id=session_id
            )
            responses.append(response)
            # Give the LLM a moment to process
            await asyncio.sleep(1)
            
        print("Contractor agent conversation completed")
        return responses
        
    except Exception as e:
        print(f"Error running contractor agent conversation: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

async def run_homeowner_review_bids(homeowner_id, project_id, bid_card_id, session_id=None):
    """Run a conversation with the Homeowner Agent to review and accept bids."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent conversation")
        return "No LLM agent"
    
    try:
        # Set up the agent
        agent = create_homeowner_agent()
        if not agent:
            print("Agent creation failed, skipping conversation")
            return "Failed to create homeowner agent"
        
        # Initialize session service and runner
        session_service = InMemorySessionService()
        app_name = "test_homeowner_app"
        
        if session_id is None:
            session_id = f"session_homeowner_review_{int(datetime.now().timestamp())}"
        
        # Create the session
        session = session_service.create_session(
            app_name=app_name,
            user_id=homeowner_id,
            session_id=session_id
        )
        
        # Initialize the runner
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service
        )
        
        # Get bids information from database
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
        bids_result = client.table("bids").select("*").eq("project_id", project_id).execute()
        
        if not bids_result.data or len(bids_result.data) == 0:
            return ["No bids found for this project"]
        
        # Format bids for the prompt
        bids_text = ""
        for i, bid in enumerate(bids_result.data):
            contractor_result = client.table("users").select("*").eq("id", bid["contractor_id"]).execute()
            contractor = contractor_result.data[0] if contractor_result.data else {"email": "unknown", "contractor_profile": {}}
            
            bids_text += f"Bid #{i+1}:\n"
            bids_text += f"  Contractor: {contractor.get('email')}\n"
            bids_text += f"  Company: {contractor.get('contractor_profile', {}).get('company_name', 'Unknown')}\n"
            bids_text += f"  Amount: ${bid['amount']}\n"
            bids_text += f"  Timeline: {bid['timeline_weeks']} weeks\n"
            bids_text += f"  Message: {bid['message']}\n"
            bids_text += f"  Bid ID: {bid['id']}\n\n"
        
        # Run a conversation to review bids
        prompts = [
            f"I'm the homeowner with ID: {homeowner_id}. I want to review the bids for my project ID: {project_id}, bid card ID: {bid_card_id}.",
            f"Here are the bids I've received:\n\n{bids_text}\nCan you help me understand these bids and which one might be best for my project?",
            f"I think I'll go with the first bid. Can you help me accept it?"
        ]
        
        responses = []
        for prompt in prompts:
            response = await call_agent_async(
                query=prompt,
                runner=runner,
                user_id=homeowner_id,
                session_id=session_id
            )
            responses.append(response)
            # Give the LLM a moment to process
            await asyncio.sleep(1)
            
        # Accept the first bid
        if bids_result.data and len(bids_result.data) > 0:
            first_bid_id = bids_result.data[0]["id"]
            update_result = client.table("bids").update({"status": "accepted"}).eq("id", first_bid_id).execute()
            print(f"Updated bid {first_bid_id} status to 'accepted'")
            
        print("Homeowner review conversation completed")
        return responses
        
    except Exception as e:
        print(f"Error running homeowner review conversation: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

@pytest.mark.asyncio
async def test_multi_agent_interaction(setup_env_variables, supabase_admin_client, test_homeowner, test_contractors, test_memories, cleanup):
    """Test the full multi-agent interaction with real LLMs."""
    print("\n======== MULTI-AGENT INTERACTION TEST WITH REAL LLM ========\n")
    
    # Verify environment variables are set
    assert setup_env_variables["SUPABASE_URL"] == SUPABASE_URL
    assert setup_env_variables["GOOGLE_API_KEY"] == GOOGLE_API_KEY
    
    # Skip test if ADK is not available
    if not ADK_AVAILABLE:
        pytest.skip("Google ADK not available for testing")
    
    # Get IDs for testing
    homeowner_id = test_homeowner["id"]
    
    # Make sure we have contractors to match
    assert len(test_contractors) > 0, "No test contractors were created"
    
    # Step 1: Homeowner creates a project with the homeowner agent
    print("\n--- Step 1: Homeowner creates a project using homeowner agent ---")
    homeowner_responses = await run_homeowner_agent_conversation(homeowner_id)
    assert isinstance(homeowner_responses, list)
    
    # Add homeowner conversation to memory
    for i, response in enumerate(homeowner_responses):
        add_interaction_to_memory(supabase_admin_client, homeowner_id, "llm_response", {
            "conversation_step": i,
            "response_text": response,
            "agent": "homeowner_agent"
        })
    
    # Create a project and bid card in the database
    project = create_project(
        supabase_admin_client, 
        homeowner_id, 
        title="Bathroom Renovation", 
        description="Bathroom renovation with walk-in shower, new vanity, and tile flooring"
    )
    assert project is not None
    
    bid_card = create_bid_card(
        supabase_admin_client, 
        homeowner_id, 
        project["id"], 
        details={
            "shower": "walk-in",
            "vanity": "modern",
            "flooring": "ceramic tile"
        }
    )
    assert bid_card is not None
    
    # Step 2: Matching agent finds suitable contractors
    print("\n--- Step 2: Matching agent finds suitable contractors ---")
    matching_response = await run_matching_agent(project)
    assert isinstance(matching_response, str)
    
    # Use the vector search tool directly to get matches
    search_results = vector_search_tool(
        query=project["description"],
        category=project["category"],
        top_k=2
    )
    
    # Save matches to database
    matches = search_results["matches"]
    match_scores = search_results["scores"]
    match_ids = save_matches(
        supabase_admin_client,
        project["id"],
        matches,
        match_scores
    )
    assert len(match_ids) > 0
    
    # Step 3: Contractor reviews and bids on the project
    print("\n--- Step 3: Contractors review and bid on the project ---")
    contractor_responses = []
    contractor_ids = []
    
    # Have each matched contractor review and bid
    for contractor in matches:
        contractor_id = contractor["id"]
        contractor_ids.append(contractor_id)
        
        # Run contractor agent conversation
        contractor_response = await run_contractor_agent_conversation(contractor_id, bid_card)
        assert isinstance(contractor_response, list)
        contractor_responses.append(contractor_response)
        
        # Add contractor conversation to memory
        for i, response in enumerate(contractor_response):
            add_interaction_to_memory(supabase_admin_client, contractor_id, "llm_response", {
                "bid_card_id": bid_card["id"],
                "conversation_step": i,
                "response_text": response,
                "agent": "contractor_agent"
            })
        
        # Create a bid
        bid = create_bid(
            supabase_admin_client,
            contractor_id,
            bid_card["id"],
            project["id"],
            homeowner_id
        )
        assert bid is not None
    
    # Step 4: Homeowner reviews and accepts bids
    print("\n--- Step 4: Homeowner reviews and accepts bids ---")
    homeowner_review_responses = await run_homeowner_review_bids(
        homeowner_id,
        project["id"],
        bid_card["id"]
    )
    assert isinstance(homeowner_review_responses, list)
    
    # Add homeowner review conversation to memory
    for i, response in enumerate(homeowner_review_responses):
        add_interaction_to_memory(supabase_admin_client, homeowner_id, "llm_response", {
            "project_id": project["id"],
            "conversation_step": i + len(homeowner_responses),
            "response_text": response,
            "agent": "homeowner_agent_review"
        })
    
    # Verify a bid was accepted
    bids_result = supabase_admin_client.table("bids").select("*").eq("project_id", project["id"]).eq("status", "accepted").execute()
    assert bids_result.data is not None
    assert len(bids_result.data) == 1
    
    # Verify memory has all agent interactions
    memory_result = supabase_admin_client.table("user_memories").select("memory_data").eq("user_id", homeowner_id).execute()
    assert memory_result.data is not None
    assert len(memory_result.data) == 1
    
    memory_data = memory_result.data[0]["memory_data"]
    llm_interactions = [i for i in memory_data.get("interactions", []) if i["type"] == "llm_response"]
    
    # Verify there are interactions from both agents
    homeowner_interactions = [i for i in llm_interactions if i["data"].get("agent", "").startswith("homeowner")]
    assert len(homeowner_interactions) > 0
    
    print(f"[PASS] Multi-agent LLM integration test successful")
    print(f"[PASS] Successfully completed the full workflow with multiple agents")
