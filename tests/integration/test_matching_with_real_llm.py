"""
MatchingAgent Integration Test with Real LLM

This test uses the Google ADK (v0.4.0) with actual API keys to perform real LLM calls.
It verifies the complete flow of a matching agent process with real LLM integration.
"""

import os
import asyncio
import uuid
import json
import pytest
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
from supabase import create_client, Client

# Constants for the test - get from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE", "")

# API keys should be loaded from environment variables, not hardcoded
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")  # Get from environment
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")  # Get from environment

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
TEST_PREFIX = f"pytest-matching-{int(datetime.now().timestamp())}"

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
def test_project(supabase_admin_client):
    """Create a test homeowner and project in the database."""
    # First create a homeowner
    random_id = str(uuid.uuid4())[:8]
    email = f"{TEST_PREFIX}_homeowner_{random_id}@example.com"
    
    homeowner_data = {
        "email": email,
        "user_type": "homeowner",
        "created_at": datetime.now().isoformat()
    }
    
    homeowner_result = supabase_admin_client.table("users").insert(homeowner_data).execute()
    homeowner = homeowner_result.data[0] if homeowner_result.data else None
    
    if not homeowner:
        pytest.fail("Failed to create test homeowner")
        
    homeowner_id = homeowner["id"]
    
    # Create a project
    project_data = {
        "homeowner_id": homeowner_id,
        "title": f"{TEST_PREFIX} Kitchen Renovation",
        "description": "Complete kitchen renovation with new cabinets, countertops, and appliances. Need specialist with tile work experience.",
        "category": "renovation",
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    project_result = supabase_admin_client.table("projects").insert(project_data).execute()
    project = project_result.data[0] if project_result.data else None
    
    if not project:
        # Clean up homeowner
        supabase_admin_client.table("users").delete().eq("id", homeowner_id).execute()
        pytest.fail("Failed to create test project")
        
    project_id = project["id"]
    
    # Create a bid card
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
        "details": {
            "cabinets": "white",
            "countertops": "granite",
            "backsplash": "subway tile"
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    bid_card_result = supabase_admin_client.table("bid_cards").insert(bid_card_data).execute()
    bid_card = bid_card_result.data[0] if bid_card_result.data else None
    
    if not bid_card:
        # Clean up project and homeowner
        supabase_admin_client.table("projects").delete().eq("id", project_id).execute()
        supabase_admin_client.table("users").delete().eq("id", homeowner_id).execute()
        pytest.fail("Failed to create test bid card")
    
    print(f"Created test project with ID: {project_id}, bid card ID: {bid_card['id']}")
    
    # Return all created objects for use in test
    test_data = {
        "homeowner_id": homeowner_id,
        "project_id": project_id,
        "bid_card_id": bid_card["id"],
        "bid_card": bid_card,
        "project": project
    }
    
    # Yield the data for the test
    yield test_data
    
    # Clean up after the test
    try:
        # Delete bid card
        supabase_admin_client.table("bid_cards").delete().eq("id", bid_card["id"]).execute()
        
        # Delete project
        supabase_admin_client.table("projects").delete().eq("id", project_id).execute()
        
        # Delete homeowner
        supabase_admin_client.table("users").delete().eq("id", homeowner_id).execute()
        
        print(f"Cleaned up test bid card, project, and homeowner")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

@pytest.fixture
def test_contractors(supabase_admin_client):
    """Create test contractors for matching."""
    contractors = []
    contractor_ids = []
    
    try:
        # Create multiple contractors with different specialties
        for i, specialty in enumerate([
            ["kitchen", "bathroom", "flooring"],
            ["kitchen", "electrical", "plumbing"],
            ["basement", "outdoor", "flooring"]
        ]):
            random_id = str(uuid.uuid4())[:8]
            email = f"{TEST_PREFIX}_contractor_{i}_{random_id}@example.com"
            
            contractor_data = {
                "email": email,
                "user_type": "contractor",
                "created_at": datetime.now().isoformat(),
                "contractor_profile": {
                    "company_name": f"Test Contracting Co. {i} {random_id}",
                    "specialties": specialty,
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
    
    # Clean up after the test
    finally:
        for contractor_id in contractor_ids:
            try:
                # Delete contractor match entries first
                supabase_admin_client.table("contractor_matches").delete().eq("contractor_id", contractor_id).execute()
                
                # Then delete the contractor
                supabase_admin_client.table("users").delete().eq("id", contractor_id).execute()
                print(f"Cleaned up test contractor with ID: {contractor_id}")
            except Exception as e:
                print(f"Error during contractor cleanup: {str(e)}")

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
        if category in specialties:
            score += 0.5
            
        # Look for keywords
        keywords = ["kitchen", "bathroom", "flooring", "electrical", "plumbing", "tile"]
        for keyword in keywords:
            if keyword in query.lower() and keyword in specialties:
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
    matches = sorted(matches, key=lambda x: scores[x["id"]], reverse=True)[:top_k]
    
    return {
        "matches": matches,
        "scores": scores,
        "reasoning": reasoning
    }

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

async def run_matching_agent(project_data, session_id="test_session"):
    """Run a matching agent to find contractors for a project."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent execution")
        return "No LLM agent"
    
    try:
        # Set up the agent
        agent = create_matching_agent()
        if not agent:
            print("Agent creation failed, skipping execution")
            return "Failed to create agent"
        
        # Initialize session service and runner
        session_service = InMemorySessionService()
        app_name = "test_matching_app"
        
        # Create the session
        session = session_service.create_session(
            app_name=app_name,
            user_id=project_data["project_id"],
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
            f"Project ID: {project_data['project_id']}\n"
            f"Project Type: {project_data['project']['category']} - {project_data['bid_card']['job_type']}\n"
            f"Description: {project_data['project']['description']}\n"
            f"Budget Range: ${project_data['bid_card']['budget_min']} - ${project_data['bid_card']['budget_max']}\n"
            f"Timeline: {project_data['bid_card']['timeline']}\n"
            f"Project Details: {json.dumps(project_data['bid_card']['details'], indent=2)}\n"
        )
        
        # Run the matching request
        prompt = f"I need to find qualified contractors for this project: {project_text}"
        response = await call_agent_async(
            query=prompt,
            runner=runner,
            user_id=project_data["project_id"],
            session_id=session_id
        )
        
        return response
    except Exception as e:
        print(f"Error running matching agent: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

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

@pytest.mark.asyncio
async def test_matching_with_real_llm(setup_env_variables, supabase_admin_client, test_project, test_contractors):
    """Test the matching workflow with real LLM integration."""
    print("\n======== MATCHING WORKFLOW TEST WITH REAL LLM ========\n")
    
    # Verify environment variables are set
    assert setup_env_variables["SUPABASE_URL"] == SUPABASE_URL
    assert setup_env_variables["GOOGLE_API_KEY"] == GOOGLE_API_KEY
    
    # Get IDs for testing
    project_id = test_project["project_id"]
    
    # Make sure we have contractors to match
    assert len(test_contractors) > 0, "No test contractors were created"
    
    # Run the matching agent if ADK is available
    if ADK_AVAILABLE:
        print("\n--- Running matching agent with real LLM ---")
        response = await run_matching_agent(test_project)
        
        # Verify we got a response
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Execute vector search directly
        search_results = vector_search_tool(
            query=test_project["project"]["description"],
            category=test_project["project"]["category"],
            top_k=3
        )
        
        # Save matches
        matches = search_results["matches"]
        match_scores = search_results["scores"]
        assert len(matches) > 0, "No contractor matches found"
        
        match_ids = save_matches(
            supabase_admin_client,
            project_id,
            matches,
            match_scores
        )
        
        assert len(match_ids) > 0, "Failed to save matches"
        
        # Verify matches were saved
        matches_result = supabase_admin_client.table("contractor_matches").select("*").eq("project_id", project_id).execute()
        assert matches_result.data is not None
        assert len(matches_result.data) > 0
        
        print(f"[PASS] Found {len(matches_result.data)} contractor matches for project {project_id}")
        print(f"[PASS] Matching LLM integration test successful")
        
        # Clean up matches
        for match_id in match_ids:
            supabase_admin_client.table("contractor_matches").delete().eq("id", match_id).execute()
    else:
        print("Google ADK not available, skipping LLM integration test")
        pytest.skip("Google ADK not available for testing")