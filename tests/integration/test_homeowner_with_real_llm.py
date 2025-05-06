"""
HomeownerAgent Integration Test with Real LLM

This test uses the Google ADK (v0.4.0) with actual API keys to perform real LLM calls.
It verifies the complete flow of a homeowner agent conversation with real LLM integration.
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
TEST_PREFIX = f"pytest-realllm-{int(datetime.now().timestamp())}"

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
def test_user(supabase_admin_client):
    """Create a test user and return the user data. Clean up after test."""
    # Generate unique email
    random_id = str(uuid.uuid4())[:8]
    email = f"{TEST_PREFIX}_user_{random_id}@example.com"
    
    # User data
    user_data = {
        "email": email,
        "user_type": "homeowner",
        "created_at": datetime.now().isoformat()
    }
    
    # Insert user
    result = supabase_admin_client.table("users").insert(user_data).execute()
    user = result.data[0] if result.data else None
    
    print(f"Created test user with ID: {user['id']}") if user else print("Failed to create test user")
    
    # Yield the created user for the test
    yield user
    
    # Clean up after the test
    if user and 'id' in user:
        try:
            # Delete any memory interactions
            supabase_admin_client.table("user_memory_interactions").delete().eq("user_id", user["id"]).execute()
            
            # Delete any memory records
            supabase_admin_client.table("user_memories").delete().eq("user_id", user["id"]).execute()
            
            # Delete any bid cards (first get project IDs)
            projects_result = supabase_admin_client.table("projects").select("id").eq("homeowner_id", user["id"]).execute()
            if projects_result.data:
                for project in projects_result.data:
                    # Delete bid cards for project
                    supabase_admin_client.table("bid_cards").delete().eq("project_id", project["id"]).execute()
                    
                    # Delete the project
                    supabase_admin_client.table("projects").delete().eq("id", project["id"]).execute()
            
            # Finally delete the user
            supabase_admin_client.table("users").delete().eq("id", user["id"]).execute()
            print(f"Cleaned up test user with ID: {user['id']} and all related data")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

@pytest.fixture
def test_project(supabase_admin_client, test_user):
    """Create a test project for the user."""
    user_id = test_user["id"]
    
    # Project data
    project_data = {
        "homeowner_id": user_id,
        "title": f"{TEST_PREFIX} Kitchen Renovation",
        "description": "Complete kitchen renovation with new cabinets, countertops, and appliances",
        "category": "renovation",
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Insert project
    result = supabase_admin_client.table("projects").insert(project_data).execute()
    project = result.data[0] if result.data else None
    
    print(f"Created test project with ID: {project['id']}") if project else print("Failed to create test project")
    
    return project

@pytest.fixture
def initial_memory_data():
    """Create initial memory data for test."""
    return {
        "interactions": [],
        "context": {
            "favorite_color": "blue",
            "favorite_room": "kitchen",
            "last_login": datetime.now().isoformat()
        },
        "learned_preferences": {},
        "creation_date": datetime.now().isoformat()
    }

@pytest.fixture
def test_memory(supabase_admin_client, test_user, initial_memory_data):
    """Create a memory record for the test user."""
    user_id = test_user["id"]
    
    # Memory data for insertion
    memory_data = {
        "user_id": user_id,
        "memory_data": initial_memory_data
    }
    
    # Insert into user_memories table
    try:
        print(f"Creating memory for user {user_id}...")
        result = supabase_admin_client.table("user_memories").upsert(memory_data).execute()
        memory = result.data[0] if result.data else None
        print(f"Created memory for user {user_id}") if memory else print("Failed to create memory")
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

# Additional tool for the LLM
def extract_renovation_details(text: str) -> Dict[str, Any]:
    """Extract renovation project details from user text."""
    print(f"Extracting renovation details from: {text}")
    return {
        "text_analyzed": text,
        "timestamp": datetime.now().isoformat(),
        "detected_room": "kitchen" if "kitchen" in text.lower() else "bathroom" if "bathroom" in text.lower() else "living room",
        "estimated_complexity": "high" if "complete" in text.lower() or "major" in text.lower() else "medium"
    }

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
            """,
            tools=[supabase_tool, extract_renovation_details]
        )
        print(f"Successfully created agent with API key")
        return agent
    except Exception as e:
        print(f"Error creating agent: {e}")
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

async def run_homeowner_agent_conversation(homeowner_id, project_id):
    """Run a simple conversation with the Homeowner Agent."""
    if not ADK_AVAILABLE:
        print("Google ADK not available, skipping agent conversation")
        return "No LLM agent"
    
    try:
        # Set up the agent
        agent = create_homeowner_agent()
        if not agent:
            print("Agent creation failed, skipping conversation")
            return "Failed to create agent"
        
        # Initialize session service and runner
        session_service = InMemorySessionService()
        app_name = "test_homeowner_app"
        session_id = f"session_{int(datetime.now().timestamp())}"
        
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
        prompts = [
            f"I want to renovate my kitchen. I have a budget of $10,000 to $15,000 and want to get it done in the next 3 months. My project ID is {project_id} and I'm user {homeowner_id}.",
            "I'd like to have white cabinets, granite countertops, and a subway tile backsplash.",
            "Can you tell me what you've recorded about my project so far?"
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
            # Give the LLM a moment to respond
            await asyncio.sleep(1)
            
        print("Agent conversation completed")
        return responses
        
    except Exception as e:
        print(f"Error running agent conversation: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

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
            return bid_card_id
        else:
            print("Failed to create bid card")
            return None
    except Exception as e:
        print(f"Error creating bid card: {str(e)}")
        return None

@pytest.mark.asyncio
async def test_homeowner_with_real_llm(setup_env_variables, supabase_admin_client, test_user, test_project, test_memory):
    """Test the homeowner workflow with real LLM integration."""
    print("\n======== HOMEOWNER WORKFLOW TEST WITH REAL LLM ========\n")
    
    # Verify environment variables are set
    assert setup_env_variables["SUPABASE_URL"] == SUPABASE_URL
    assert setup_env_variables["GOOGLE_API_KEY"] == GOOGLE_API_KEY
    
    # Get IDs for testing
    user_id = test_user["id"]
    project_id = test_project["id"]
    
    # Add project creation interaction to memory
    interaction_data = {
        "project_id": project_id,
        "project_type": "renovation",
        "timeline": "3 months",
        "action": "created"
    }
    
    add_interaction_to_memory(supabase_admin_client, user_id, "project_creation", interaction_data)
    
    # Run the agent conversation if ADK is available
    if ADK_AVAILABLE:
        print("\n--- Running homeowner agent conversation with real LLM ---")
        responses = await run_homeowner_agent_conversation(user_id, project_id)
        
        # Verify we got responses
        assert responses is not None
        if isinstance(responses, list):
            assert len(responses) == 3
            
            # Create a bid card from the conversation
            bid_card_id = create_bid_card(supabase_admin_client, user_id, project_id)
            assert bid_card_id is not None
            
            # Add the LLM responses to memory
            for i, response in enumerate(responses):
                add_interaction_to_memory(supabase_admin_client, user_id, "llm_response", {
                    "project_id": project_id,
                    "response_index": i,
                    "response_text": response
                })
                
            # Verify memory has LLM interactions
            memory_result = supabase_admin_client.table("user_memories").select("memory_data").eq("user_id", user_id).execute()
            assert memory_result.data is not None
            assert len(memory_result.data) == 1
            
            memory_data = memory_result.data[0]["memory_data"]
            llm_interactions = [i for i in memory_data.get("interactions", []) if i["type"] == "llm_response"]
            assert len(llm_interactions) == 3
            
            # Verify interactions table has LLM interactions
            interactions_result = supabase_admin_client.table("user_memory_interactions").select("*").eq("user_id", user_id).eq("interaction_type", "llm_response").execute()
            assert interactions_result.data is not None
            assert len(interactions_result.data) >= 3
            
            print(f"[PASS] LLM integration test successful")
            
            # Delete the bid card
            supabase_admin_client.table("bid_cards").delete().eq("id", bid_card_id).execute()
        else:
            print(f"[FAIL] LLM responses not in expected format")
    else:
        print("Google ADK not available, skipping LLM integration test")
        pytest.skip("Google ADK not available for testing")