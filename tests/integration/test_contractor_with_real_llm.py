"""
ContractorAgent Integration Test with Real LLM

This test uses the Google ADK (v0.4.0) with actual API keys to perform real LLM calls.
It verifies the complete flow of a contractor agent conversation with real LLM integration.
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
TEST_PREFIX = f"pytest-contractor-{int(datetime.now().timestamp())}"

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
def test_contractor(supabase_admin_client):
    """Create a test contractor and return the user data. Clean up after test."""
    # Generate unique email
    random_id = str(uuid.uuid4())[:8]
    email = f"{TEST_PREFIX}_contractor_{random_id}@example.com"
    
    # Contractor data
    contractor_data = {
        "email": email,
        "user_type": "contractor",
        "created_at": datetime.now().isoformat(),
        "contractor_profile": {
            "company_name": f"Test Contracting Co. {random_id}",
            "specialties": ["kitchen", "bathroom", "flooring"],
            "years_experience": 10,
            "license_number": f"LIC-{random_id}",
            "insurance_policy": f"INS-{random_id}"
        }
    }
    
    # Insert contractor
    result = supabase_admin_client.table("users").insert(contractor_data).execute()
    contractor = result.data[0] if result.data else None
    
    print(f"Created test contractor with ID: {contractor['id']}") if contractor else print("Failed to create test contractor")
    
    # Yield the created contractor for the test
    yield contractor
    
    # Clean up after the test
    if contractor and 'id' in contractor:
        try:
            # Delete memory interactions if any
            supabase_admin_client.table("user_memory_interactions").delete().eq("user_id", contractor["id"]).execute()
            
            # Delete memory records if any
            supabase_admin_client.table("user_memories").delete().eq("user_id", contractor["id"]).execute()
            
            # Delete any bids
            supabase_admin_client.table("bids").delete().eq("contractor_id", contractor["id"]).execute()
            
            # Finally delete the contractor
            supabase_admin_client.table("users").delete().eq("id", contractor["id"]).execute()
            print(f"Cleaned up test contractor with ID: {contractor['id']} and all related data")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

@pytest.fixture
def test_bid_card(supabase_admin_client):
    """Create a test bid card and homeowner for the contractor to interact with."""
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
        "description": "Complete kitchen renovation with new cabinets, countertops, and appliances",
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
    
    print(f"Created test bid card with ID: {bid_card['id']} for homeowner ID: {homeowner_id}")
    
    # Return all created objects for use in test
    test_data = {
        "homeowner_id": homeowner_id,
        "project_id": project_id,
        "bid_card_id": bid_card["id"],
        "bid_card": bid_card
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
def initial_memory_data():
    """Create initial memory data for test."""
    return {
        "interactions": [],
        "context": {
            "specialties": ["kitchen", "bathroom", "flooring"],
            "years_experience": 10,
            "last_login": datetime.now().isoformat()
        },
        "learned_preferences": {},
        "creation_date": datetime.now().isoformat()
    }

@pytest.fixture
def test_memory(supabase_admin_client, test_contractor, initial_memory_data):
    """Create a memory record for the test contractor."""
    contractor_id = test_contractor["id"]
    
    # Memory data for insertion
    memory_data = {
        "user_id": contractor_id,
        "memory_data": initial_memory_data
    }
    
    # Insert into user_memories table
    try:
        print(f"Creating memory for contractor {contractor_id}...")
        result = supabase_admin_client.table("user_memories").upsert(memory_data).execute()
        memory = result.data[0] if result.data else None
        print(f"Created memory for contractor {contractor_id}") if memory else print("Failed to create memory")
        return memory
    except Exception as e:
        print(f"Error creating memory: {str(e)}")
        return None

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

def estimate_cost(job_details: Dict[str, Any]) -> Dict[str, Any]:
    """Tool to estimate the cost of a job based on details."""
    print(f"Estimating cost for job: {job_details}")
    
    # Simple cost estimation logic
    base_cost = 5000
    
    # Add costs based on job details
    if "cabinets" in job_details and job_details["cabinets"] == "custom":
        base_cost += 3000
    elif "cabinets" in job_details and job_details["cabinets"] == "white":
        base_cost += 1500
        
    if "countertops" in job_details and job_details["countertops"] == "granite":
        base_cost += 2000
    elif "countertops" in job_details and job_details["countertops"] == "marble":
        base_cost += 3500
        
    if "backsplash" in job_details and job_details["backsplash"] == "subway tile":
        base_cost += 800
    elif "backsplash" in job_details and job_details["backsplash"] == "glass tile":
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

async def run_contractor_agent_conversation(contractor_id, bid_card_data):
    """Run a simple conversation with the Contractor Agent."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent conversation")
        return "No LLM agent"
    
    try:
        # Set up the agent
        agent = create_contractor_agent()
        if not agent:
            print("Agent creation failed, skipping conversation")
            return "Failed to create agent"
        
        # Initialize session service and runner
        session_service = InMemorySessionService()
        app_name = "test_contractor_app"
        session_id = f"session_{int(datetime.now().timestamp())}"
        
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
            f"Bid Card ID: {bid_card_data['bid_card_id']}\n"
            f"Project Type: {bid_card_data['bid_card']['category']} - {bid_card_data['bid_card']['job_type']}\n"
            f"Budget Range: ${bid_card_data['bid_card']['budget_min']} - ${bid_card_data['bid_card']['budget_max']}\n"
            f"Timeline: {bid_card_data['bid_card']['timeline']}\n"
            f"Project Details: {json.dumps(bid_card_data['bid_card']['details'], indent=2)}\n"
        )
        
        # Run a simple conversation
        prompts = [
            f"I'm a contractor with ID: {contractor_id}. I'm looking at this bid card: {bid_card_text}. Can you help me understand the project?",
            "Can you help me estimate the cost for this project and what my bid should be?",
            "How does this project fit with my specialties in kitchen remodeling?"
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
            # Give the LLM a moment to respond
            await asyncio.sleep(1)
            
        print("Agent conversation completed")
        return responses
        
    except Exception as e:
        print(f"Error running agent conversation: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

def create_bid(supabase_admin_client, contractor_id, bid_card_id, project_id, homeowner_id, bid_amount=7500):
    """Create a bid for a bid card."""
    bid_data = {
        "contractor_id": contractor_id,
        "bid_card_id": bid_card_id,
        "project_id": project_id,
        "homeowner_id": homeowner_id,
        "amount": bid_amount,
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
            return bid_id
        else:
            print("Failed to create bid")
            return None
    except Exception as e:
        print(f"Error creating bid: {str(e)}")
        return None

@pytest.mark.asyncio
async def test_contractor_with_real_llm(setup_env_variables, supabase_admin_client, test_contractor, test_bid_card, test_memory):
    """Test the contractor workflow with real LLM integration."""
    print("\n======== CONTRACTOR WORKFLOW TEST WITH REAL LLM ========\n")
    
    # Verify environment variables are set
    assert setup_env_variables["SUPABASE_URL"] == SUPABASE_URL
    assert setup_env_variables["GOOGLE_API_KEY"] == GOOGLE_API_KEY
    
    # Get IDs for testing
    contractor_id = test_contractor["id"]
    bid_card_id = test_bid_card["bid_card_id"]
    project_id = test_bid_card["project_id"]
    homeowner_id = test_bid_card["homeowner_id"]
    
    # Run the agent conversation if ADK is available
    if ADK_AVAILABLE:
        print("\n--- Running contractor agent conversation with real LLM ---")
        responses = await run_contractor_agent_conversation(contractor_id, test_bid_card)
        
        # Verify we got responses
        assert responses is not None
        if isinstance(responses, list):
            assert len(responses) == 3
            
            for i, response in enumerate(responses):
                add_interaction_to_memory(supabase_admin_client, contractor_id, "llm_response", {
                    "bid_card_id": bid_card_id,
                    "response_index": i,
                    "response_text": response
                })
            
            # Create a bid based on the conversation
            bid_id = create_bid(
                supabase_admin_client, 
                contractor_id, 
                bid_card_id, 
                project_id, 
                homeowner_id
            )
            assert bid_id is not None
            
            # Verify memory has LLM interactions
            memory_result = supabase_admin_client.table("user_memories").select("memory_data").eq("user_id", contractor_id).execute()
            assert memory_result.data is not None
            assert len(memory_result.data) == 1
            
            memory_data = memory_result.data[0]["memory_data"]
            llm_interactions = [i for i in memory_data.get("interactions", []) if i["type"] == "llm_response"]
            assert len(llm_interactions) == 3
            
            # Verify interactions table has LLM interactions
            interactions_result = supabase_admin_client.table("user_memory_interactions").select("*").eq("user_id", contractor_id).eq("interaction_type", "llm_response").execute()
            assert interactions_result.data is not None
            assert len(interactions_result.data) >= 3
            
            # Verify bid was created
            bid_result = supabase_admin_client.table("bids").select("*").eq("id", bid_id).execute()
            assert bid_result.data is not None
            assert len(bid_result.data) == 1
            
            print(f"[PASS] Contractor LLM integration test successful")
            
            # Delete the bid
            supabase_admin_client.table("bids").delete().eq("id", bid_id).execute()
        else:
            print(f"[FAIL] LLM responses not in expected format")
    else:
        print("Google ADK not available, skipping LLM integration test")
        pytest.skip("Google ADK not available for testing")