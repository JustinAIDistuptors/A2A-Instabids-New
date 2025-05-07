"""
Test Data Manager for InstaBids

This module provides a comprehensive utility for managing test data for the InstaBids application.
It handles creation, tracking, and cleanup of test resources in the Supabase database.
"""

import os
import uuid
import json
import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set

# Import real or mock Supabase client based on environment
if os.environ.get("MOCK_SERVICES", "false").lower() in ["true", "1", "yes"] or os.environ.get("CI"):
    # Use mock client in tests
    from tests.mocks.supabase_mock import create_mock_supabase_client as create_client
    from tests.mocks.supabase_mock import MockSupabaseClient as Client
else:
    # Use real client in development
    from supabase import create_client, Client

# Get Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://mkfbxvwmuxebggfbljgn.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE", "")

# Constants for test data
DEFAULT_TEST_PREFIX = f"test-{int(datetime.now().timestamp())}"
DEFAULT_CATEGORIES = ["renovation", "repair", "installation"]
DEFAULT_JOB_TYPES = ["kitchen", "bathroom", "plumbing", "electrical", "flooring"]

class TestDataManager:
    """
    Manager for test data - creates, tracks, and cleans up test resources.
    
    This class provides methods for creating test data and automatically
    tracks all created resources for easy cleanup.
    """
    
    def __init__(self, client: Optional[Client] = None, test_prefix: str = DEFAULT_TEST_PREFIX):
        """
        Initialize the TestDataManager.
        
        Args:
            client: Supabase client (created if not provided)
            test_prefix: Prefix for generated test data
        """
        if client is None:
            client = self._get_supabase_client()
        
        self.client = client
        self.test_prefix = test_prefix
        
        # Generate a unique test ID
        self.test_id = str(uuid.uuid4())[:8]
        if not test_prefix.endswith("-"):
            self.test_prefix = f"{test_prefix}-"
        self.test_prefix = f"{self.test_prefix}{self.test_id}"
        
        # Track resources for cleanup
        self.users: List[str] = []
        self.projects: List[str] = []
        self.bid_cards: List[str] = []
        self.bids: List[str] = []
        self.contractor_matches: List[str] = []
        self.other_resources: Dict[str, List[str]] = {}
        
        # Track schema information
        self._schema_info = {}
        self._schema_queried = False
    
    def _get_supabase_client(self) -> Client:
        """Get a Supabase client using the environment variables."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE environment variables must be set")
        
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    
    async def query_schema_info(self) -> None:
        """Query schema information to determine table and column existence."""
        if self._schema_queried:
            return
        
        try:
            # Check for the existence of specific tables and columns
            tables_to_check = ["users", "projects", "bid_cards", "bids", "contractor_matches",
                              "user_memories", "user_memory_interactions"]
            
            # Use pgmeta_query if it exists
            try:
                query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = ANY($1)
                """
                result = self.client.rpc("pgmeta_query", {"query": query, "params": [tables_to_check]}).execute()
                if result.data:
                    for row in result.data:
                        table_name = row["table_name"]
                        self._schema_info[f"has_{table_name}_table"] = True
            except Exception:
                # Fallback if pgmeta_query doesn't exist - assume tables exist
                for table in tables_to_check:
                    self._schema_info[f"has_{table}_table"] = True
            
            # Check for specific columns
            column_checks = [
                ("bids", "bid_card_id"),
                ("bids", "details"),
                ("bids", "homeowner_id")
            ]
            
            for table, column in column_checks:
                key = f"has_{table}_{column}_column"
                try:
                    query = f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = '{table}'
                    AND column_name = '{column}'
                    """
                    result = self.client.rpc("pgmeta_query", {"query": query}).execute()
                    self._schema_info[key] = result.data and len(result.data) > 0
                except Exception:
                    # Assume column exists if query fails
                    self._schema_info[key] = True
            
            self._schema_queried = True
        
        except Exception as e:
            print(f"Error querying schema info: {str(e)}")
            # Set defaults - assume updated schema
            self._schema_info = {
                "has_users_table": True,
                "has_projects_table": True,
                "has_bid_cards_table": True,
                "has_bids_table": True,
                "has_contractor_matches_table": True,
                "has_user_memories_table": True,
                "has_user_memory_interactions_table": True,
                "has_bids_bid_card_id_column": True,
                "has_bids_details_column": True,
                "has_bids_homeowner_id_column": True
            }
            self._schema_queried = True
    
    def has_table(self, table_name: str) -> bool:
        """Check if a table exists in the schema."""
        key = f"has_{table_name}_table"
        return self._schema_info.get(key, False)
    
    def has_column(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        key = f"has_{table_name}_{column_name}_column"
        return self._schema_info.get(key, False)
    
    async def create_homeowner(
        self,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a test homeowner and return the user ID.
        
        Args:
            email: Email for the homeowner (generated if not provided)
            metadata: Additional metadata for the homeowner
            
        Returns:
            The ID of the created homeowner
        """
        if email is None:
            random_id = str(uuid.uuid4())[:8]
            email = f"{self.test_prefix}_homeowner_{random_id}@example.com"
        
        homeowner_data = {
            "email": email,
            "user_type": "homeowner",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        if metadata:
            homeowner_data["metadata"] = metadata
        else:
            homeowner_data["metadata"] = {
                "name": f"Test Homeowner {str(uuid.uuid4())[:4]}",
                "preferences": {
                    "response_time": "quick",
                    "communication": "email",
                    "budget_sensitivity": "medium"
                }
            }
        
        result = self.client.table("users").insert(homeowner_data).execute()
        if not result.data:
            raise ValueError("Failed to create test homeowner")
        
        homeowner_id = result.data[0]["id"]
        self.users.append(homeowner_id)
        print(f"Created test homeowner: {email} (ID: {homeowner_id})")
        
        return homeowner_id
    
    async def create_contractor(
        self,
        email: Optional[str] = None,
        specialties: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a test contractor and return the user ID.
        
        Args:
            email: Email for the contractor (generated if not provided)
            specialties: List of specialties for the contractor
            metadata: Additional metadata for the contractor
            
        Returns:
            The ID of the created contractor
        """
        if email is None:
            random_id = str(uuid.uuid4())[:8]
            email = f"{self.test_prefix}_contractor_{random_id}@example.com"
        
        # Default specialties if not provided
        if specialties is None:
            specialties = random.sample(DEFAULT_JOB_TYPES, min(3, len(DEFAULT_JOB_TYPES)))
        
        # Build contractor metadata
        contractor_metadata = {
            "name": f"Test Contractor {str(uuid.uuid4())[:4]}",
            "specialties": specialties,
            "rating": round(random.uniform(3.5, 5.0), 1),
            "years_experience": random.randint(1, 20),
            "business_name": f"Test Contracting Co. {str(uuid.uuid4())[:4]}"
        }
        
        # Add additional metadata if provided
        if metadata:
            contractor_metadata.update(metadata)
        
        contractor_data = {
            "email": email,
            "user_type": "contractor",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": contractor_metadata
        }
        
        result = self.client.table("users").insert(contractor_data).execute()
        if not result.data:
            raise ValueError("Failed to create test contractor")
        
        contractor_id = result.data[0]["id"]
        self.users.append(contractor_id)
        print(f"Created test contractor: {email} (ID: {contractor_id})")
        
        return contractor_id
    
    async def create_project(
        self,
        homeowner_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "renovation",
        status: str = "open"
    ) -> str:
        """
        Create a test project and return the project ID.
        
        Args:
            homeowner_id: ID of the homeowner (created if not provided)
            title: Title for the project (generated if not provided)
            description: Description for the project (generated if not provided)
            category: Category for the project
            status: Status for the project
            
        Returns:
            The ID of the created project
        """
        # Ensure category is one of the allowed values
        if category not in DEFAULT_CATEGORIES:
            raise ValueError(f"Category must be one of {DEFAULT_CATEGORIES}")
        
        # Create a homeowner if not provided
        if homeowner_id is None:
            homeowner_id = await self.create_homeowner()
        
        if title is None:
            random_id = str(uuid.uuid4())[:8]
            title = f"{self.test_prefix} Project {random_id}"
        
        if description is None:
            descriptions = [
                "A test project for renovating a kitchen",
                "A test project for repairing plumbing issues",
                "A test project for installing new flooring",
                "A test project for bathroom renovation"
            ]
            description = random.choice(descriptions)
        
        # Create the project
        project_data = {
            "homeowner_id": homeowner_id,
            "title": title,
            "description": description,
            "category": category,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = self.client.table("projects").insert(project_data).execute()
        if not result.data:
            raise ValueError("Failed to create test project")
        
        project_id = result.data[0]["id"]
        self.projects.append(project_id)
        print(f"Created test project: {title} (ID: {project_id})")
        
        return project_id
    
    async def create_bid_card(
        self,
        project_id: Optional[str] = None,
        homeowner_id: Optional[str] = None,
        category: str = "renovation",
        job_type: Optional[str] = None,
        budget_min: int = 1000,
        budget_max: int = 5000,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a test bid card and return the bid card ID.
        
        Args:
            project_id: ID of the project (created if not provided)
            homeowner_id: ID of the homeowner (created if not provided, required if project_id not provided)
            category: Category for the bid card (must be one of the allowed values)
            job_type: Job type for the bid card (generated if not provided)
            budget_min: Minimum budget for the bid card
            budget_max: Maximum budget for the bid card
            details: Additional details for the bid card
            
        Returns:
            The ID of the created bid card
        """
        # Ensure category is one of the allowed values
        if category not in DEFAULT_CATEGORIES:
            raise ValueError(f"Category must be one of {DEFAULT_CATEGORIES}")
        
        # Create a project if not provided
        if project_id is None:
            if homeowner_id is None:
                raise ValueError("Either project_id or homeowner_id must be provided")
            
            project_id = await self.create_project(
                homeowner_id=homeowner_id,
                category=category
            )
        
        # If homeowner_id is not provided, get it from the project
        if homeowner_id is None:
            project_result = self.client.table("projects").select("homeowner_id").eq("id", project_id).execute()
            if not project_result.data:
                raise ValueError(f"Project with ID {project_id} not found")
            
            homeowner_id = project_result.data[0]["homeowner_id"]
        
        # Generate a job type if not provided
        if job_type is None:
            job_type = random.choice(DEFAULT_JOB_TYPES)
        
        # Default details if not provided
        if details is None:
            details = {
                "scope": f"Test {job_type} project",
                "materials": "Standard quality materials",
                "special_requirements": "Must be completed within timeline"
            }
        
        # Create the bid card
        bid_card_data = {
            "homeowner_id": homeowner_id,
            "project_id": project_id,
            "category": category,
            "job_type": job_type,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "timeline": f"{random.randint(1, 8)} weeks",
            "location": "Home",
            "group_bidding": False,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = self.client.table("bid_cards").insert(bid_card_data).execute()
        if not result.data:
            raise ValueError("Failed to create test bid card")
        
        bid_card_id = result.data[0]["id"]
        self.bid_cards.append(bid_card_id)
        print(f"Created test bid card for project (ID: {bid_card_id})")
        
        return bid_card_id
    
    async def create_bid(
        self,
        project_id: Optional[str] = None,
        contractor_id: Optional[str] = None,
        bid_card_id: Optional[str] = None,
        amount: Optional[int] = None,
        status: str = "pending",
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a test bid and return the bid ID.
        
        Args:
            project_id: ID of the project (created if not provided)
            contractor_id: ID of the contractor (created if not provided)
            bid_card_id: ID of the bid card (retrieved from project if not provided)
            amount: Amount for the bid (generated if not provided)
            status: Status for the bid
            details: Additional details for the bid
            
        Returns:
            The ID of the created bid
        """
        # Query schema if not already done
        if not self._schema_queried:
            await self.query_schema_info()
        
        # Create a project if not provided
        if project_id is None:
            homeowner_id = None
            project_id = await self.create_project(homeowner_id=homeowner_id)
            
            # Get the homeowner ID
            project_result = self.client.table("projects").select("homeowner_id").eq("id", project_id).execute()
            if project_result.data:
                homeowner_id = project_result.data[0]["homeowner_id"]
        else:
            # Get the homeowner ID
            project_result = self.client.table("projects").select("homeowner_id").eq("id", project_id).execute()
            if project_result.data:
                homeowner_id = project_result.data[0]["homeowner_id"]
            else:
                homeowner_id = None
        
        # Create a contractor if not provided
        if contractor_id is None:
            contractor_id = await self.create_contractor()
        
        # Check if bid_card_id is required (depends on schema)
        has_bid_card_id_column = self.has_column("bids", "bid_card_id")
        
        # If bid_card_id is required but not provided, try to get it from the project
        if has_bid_card_id_column and bid_card_id is None:
            bid_card_result = self.client.table("bid_cards").select("id").eq("project_id", project_id).execute()
            if bid_card_result.data and len(bid_card_result.data) > 0:
                bid_card_id = bid_card_result.data[0]["id"]
            else:
                # Create a new bid card
                bid_card_id = await self.create_bid_card(
                    project_id=project_id,
                    homeowner_id=homeowner_id
                )
        
        # Generate a bid amount if not provided
        if amount is None:
            # Try to get budget from bid card
            if bid_card_id:
                bid_card_result = self.client.table("bid_cards").select("budget_min", "budget_max").eq("id", bid_card_id).execute()
                if bid_card_result.data and len(bid_card_result.data) > 0:
                    budget_min = bid_card_result.data[0].get("budget_min", 1000)
                    budget_max = bid_card_result.data[0].get("budget_max", 5000)
                    amount = random.randint(budget_min, budget_max)
                else:
                    amount = random.randint(1000, 5000)
            else:
                amount = random.randint(1000, 5000)
        
        # Default details if not provided
        if details is None:
            details = {
                "timeline": f"{random.randint(2, 10)} weeks",
                "materials_included": True,
                "warranty": f"{random.randint(1, 3)} year on workmanship",
                "notes": "Can start immediately upon acceptance"
            }
        
        # Create the bid data based on schema
        bid_data = {
            "project_id": project_id,
            "contractor_id": contractor_id,
            "amount": amount,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add bid_card_id if the column exists
        if has_bid_card_id_column and bid_card_id:
            bid_data["bid_card_id"] = bid_card_id
        
        # Check if details column exists
        has_details_column = self.has_column("bids", "details")
        
        # Add details if the column exists
        if has_details_column and details:
            bid_data["details"] = details
        
        # Check if homeowner_id column exists
        has_homeowner_id_column = self.has_column("bids", "homeowner_id")
        
        # Add homeowner_id if the column exists
        if has_homeowner_id_column and homeowner_id:
            bid_data["homeowner_id"] = homeowner_id
        
        # Create the bid
        result = self.client.table("bids").insert(bid_data).execute()
        if not result.data:
            raise ValueError("Failed to create test bid")
        
        bid_id = result.data[0]["id"]
        self.bids.append(bid_id)
        print(f"Created test bid from contractor {contractor_id} (ID: {bid_id}) for amount ${amount}")
        
        return bid_id
    
    async def create_user_memory(
        self,
        user_id: Optional[str] = None,
        memory_data: Optional[Dict[str, Any]] = None,
        user_type: str = "homeowner"
    ) -> Dict[str, Any]:
        """
        Create a test user memory and return the memory data.
        
        Args:
            user_id: ID of the user (created if not provided)
            memory_data: Memory data (generated if not provided)
            user_type: Type of user to create if user_id is not provided
            
        Returns:
            The created memory data
        """
        # Create a user if not provided
        if user_id is None:
            if user_type == "homeowner":
                user_id = await self.create_homeowner()
            else:
                user_id = await self.create_contractor()
        
        # Get user data
        user_result = self.client.table("users").select("*").eq("id", user_id).execute()
        if not user_result.data:
            raise ValueError(f"User with ID {user_id} not found")
        
        user = user_result.data[0]
        user_type = user.get("user_type", user_type)
        
        # Generate default memory data if not provided
        if memory_data is None:
            memory_data = {
                "context": {
                    "user_info": {
                        "id": user_id,
                        "email": user.get("email", "unknown@example.com"),
                        "type": user_type
                    }
                },
                "interactions": [],
                "learned_preferences": {}
            }
        
        # Create or update the memory
        result = self.client.table("user_memories").upsert({
            "user_id": user_id,
            "memory_data": memory_data
        }).execute()
        
        if not result.data:
            raise ValueError("Failed to create user memory")
        
        print(f"Created memory for user {user_id}")
        
        return memory_data
    
    async def add_memory_interaction(
        self,
        user_id: str,
        interaction_type: str,
        interaction_data: Dict[str, Any]
    ) -> str:
        """
        Add an interaction to a user's memory.
        
        Args:
            user_id: ID of the user
            interaction_type: Type of interaction
            interaction_data: Interaction data
            
        Returns:
            The ID of the created interaction
        """
        # Add timestamp if not present
        if "timestamp" not in interaction_data:
            interaction_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Create the interaction record
        interaction_record = {
            "user_id": user_id,
            "interaction_type": interaction_type,
            "interaction_data": interaction_data,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = self.client.table("user_memory_interactions").insert(interaction_record).execute()
        if not result.data:
            raise ValueError("Failed to create memory interaction")
        
        interaction_id = result.data[0]["id"]
        
        # Update the memory data with the new interaction
        memory_result = self.client.table("user_memories").select("memory_data").eq("user_id", user_id).execute()
        if memory_result.data and len(memory_result.data) > 0:
            memory_data = memory_result.data[0]["memory_data"]
            
            if "interactions" not in memory_data:
                memory_data["interactions"] = []
            
            memory_data["interactions"].append({
                "id": interaction_id,
                "type": interaction_type,
                "timestamp": interaction_data.get("timestamp"),
                "data": interaction_data
            })
            
            self.client.table("user_memories").update({"memory_data": memory_data}).eq("user_id", user_id).execute()
        
        print(f"Added {interaction_type} interaction for user {user_id}")
        
        return interaction_id
    
    async def match_contractors_to_project(
        self,
        project_id: str,
        contractor_ids: Optional[List[str]] = None,
        min_score: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Match contractors to a project.
        
        Args:
            project_id: ID of the project
            contractor_ids: IDs of contractors to match (generated if not provided)
            min_score: Minimum score for a match
            
        Returns:
            List of match data
        """
        # Query schema if not already done
        if not self._schema_queried:
            await self.query_schema_info()
        
        # Get project data
        project_result = self.client.table("projects").select("*").eq("id", project_id).execute()
        if not project_result.data:
            raise ValueError(f"Project with ID {project_id} not found")
        
        project = project_result.data[0]
        
        # Get bid card data
        bid_card_result = self.client.table("bid_cards").select("*").eq("project_id", project_id).execute()
        if not bid_card_result.data:
            raise ValueError(f"Bid card for project {project_id} not found")
        
        bid_card = bid_card_result.data[0]
        job_type = bid_card.get("job_type")
        
        # Create contractors if not provided
        if contractor_ids is None or len(contractor_ids) == 0:
            contractor_ids = []
            # Create 3 contractors with different specialties
            for i in range(3):
                # For the first contractor, make sure they have the job type specialty
                if i == 0:
                    specialties = [job_type]
                else:
                    specialties = random.sample(DEFAULT_JOB_TYPES, min(2, len(DEFAULT_JOB_TYPES)))
                    if job_type not in specialties and random.random() < 0.5:
                        specialties.append(job_type)
                
                contractor_id = await self.create_contractor(
                    specialties=specialties
                )
                contractor_ids.append(contractor_id)
        
        # Get contractor data
        contractors_result = self.client.table("users").select("*").in_("id", contractor_ids).execute()
        contractors = contractors_result.data
        
        # Match contractors to the project
        matches = []
        for contractor in contractors:
            metadata = contractor.get("metadata", {})
            specialties = metadata.get("specialties", [])
            score = 0
            
            # Base score on specialty match
            if job_type in specialties:
                score += 0.8
            
            # Add some score variation based on rating and experience
            rating = metadata.get("rating", 0)
            experience = metadata.get("years_experience", 0)
            
            score += (rating / 10)  # Up to 0.5 additional points
            score += (min(experience, 10) / 20)  # Up to 0.5 additional points
            
            # Normalize score to 0-1 range
            score = min(score, 1.0)
            
            if score >= min_score:
                match_data = {
                    "project_id": project_id,
                    "contractor_id": contractor["id"],
                    "score": score,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                matches.append(match_data)
                
                print(f"Matched contractor {contractor.get('email', 'Unknown')}: Score = {score:.2f}")
        
        # Try to store matches in the contractor_matches table if it exists
        has_contractor_matches_table = self.has_table("contractor_matches")
        
        if has_contractor_matches_table:
            # Store matches in the database
            for match in matches:
                result = self.client.table("contractor_matches").insert(match).execute()
                if result.data:
                    match_id = result.data[0]["id"]
                    self.contractor_matches.append(match_id)
            print(f"Stored {len(matches)} matches in the contractor_matches table")
        else:
            print("Note: contractor_matches table not found. Matches stored in memory only.")
        
        return matches
    
    async def setup_basic_test_environment(
        self
    ) -> Tuple[str, str, str, str]:
        """
        Set up a basic test environment with a homeowner, contractor, project, and bid card.
        
        Returns:
            Tuple of (homeowner_id, contractor_id, project_id, bid_card_id)
        """
        # Create a homeowner
        homeowner_id = await self.create_homeowner()
        
        # Create a contractor
        contractor_id = await self.create_contractor()
        
        # Create a project
        project_id = await self.create_project(
            homeowner_id=homeowner_id
        )
        
        # Create a bid card
        bid_card_id = await self.create_bid_card(
            project_id=project_id,
            homeowner_id=homeowner_id
        )
        
        return homeowner_id, contractor_id, project_id, bid_card_id
    
    async def setup_full_test_environment(
        self,
        num_contractors: int = 3
    ) -> Tuple[str, List[str], str, str]:
        """
        Set up a full test environment with a homeowner, multiple contractors, project, bid card, and bids.
        
        Args:
            num_contractors: Number of contractors to create
            
        Returns:
            Tuple of (homeowner_id, contractor_ids, project_id, bid_card_id)
        """
        # Create a homeowner
        homeowner_id = await self.create_homeowner()
        
        # Create contractors
        contractor_ids = []
        for i in range(num_contractors):
            specialties = random.sample(DEFAULT_JOB_TYPES, min(2, len(DEFAULT_JOB_TYPES)))
            contractor_id = await self.create_contractor(
                specialties=specialties
            )
            contractor_ids.append(contractor_id)
        
        # Create a project
        project_id = await self.create_project(
            homeowner_id=homeowner_id
        )
        
        # Create a bid card
        bid_card_id = await self.create_bid_card(
            project_id=project_id,
            homeowner_id=homeowner_id
        )
        
        # Create memory for homeowner
        await self.create_user_memory(
            user_id=homeowner_id,
            user_type="homeowner"
        )
        
        # Create memory for contractors
        for contractor_id in contractor_ids:
            await self.create_user_memory(
                user_id=contractor_id,
                user_type="contractor"
            )
        
        # Match contractors to the project
        await self.match_contractors_to_project(
            project_id=project_id,
            contractor_ids=contractor_ids
        )
        
        # Create bids from the contractors
        for i, contractor_id in enumerate(contractor_ids):
            # First contractor bids low, second in the middle, third high
            bid_card_result = self.client.table("bid_cards").select("budget_min", "budget_max").eq("id", bid_card_id).execute()
            if bid_card_result.data and len(bid_card_result.data) > 0:
                min_budget = bid_card_result.data[0].get("budget_min", 1000)
                max_budget = bid_card_result.data[0].get("budget_max", 5000)
                
                if i == 0:
                    amount = min_budget + (max_budget - min_budget) * 0.2
                elif i == 1:
                    amount = min_budget + (max_budget - min_budget) * 0.5
                else:
                    amount = min_budget + (max_budget - min_budget) * 0.8
                    
                amount = int(amount)
            else:
                amount = 1000 + i * 500
            
            await self.create_bid(
                project_id=project_id,
                contractor_id=contractor_id,
                bid_card_id=bid_card_id,
                amount=amount
            )
        
        return homeowner_id, contractor_ids, project_id, bid_card_id
    
    async def cleanup(self, silent: bool = False) -> None:
        """
        Clean up all test data.
        
        Args:
            silent: Whether to suppress output
        """
        # Delete test data in reverse order to avoid foreign key constraints
        
        # Delete contractor matches (if table exists)
        for match_id in self.contractor_matches:
            try:
                self.client.table("contractor_matches").delete().eq("id", match_id).execute()
                if not silent:
                    print(f"Deleted contractor match: {match_id}")
            except Exception as e:
                if not silent:
                    print(f"Failed to delete contractor match {match_id}: {str(e)}")
        
        # Delete bids
        for bid_id in self.bids:
            try:
                self.client.table("bids").delete().eq("id", bid_id).execute()
                if not silent:
                    print(f"Deleted bid: {bid_id}")
            except Exception as e:
                if not silent:
                    print(f"Failed to delete bid {bid_id}: {str(e)}")
        
        # Delete bid cards
        for bid_card_id in self.bid_cards:
            try:
                self.client.table("bid_cards").delete().eq("id", bid_card_id).execute()
                if not silent:
                    print(f"Deleted bid card: {bid_card_id}")
            except Exception as e:
                if not silent:
                    print(f"Failed to delete bid card {bid_card_id}: {str(e)}")
        
        # Delete projects
        for project_id in self.projects:
            try:
                self.client.table("projects").delete().eq("id", project_id).execute()
                if not silent:
                    print(f"Deleted project: {project_id}")
            except Exception as e:
                if not silent:
                    print(f"Failed to delete project {project_id}: {str(e)}")
        
        # Delete users and related data
        for user_id in self.users:
            try:
                # Delete memory interactions first
                self.client.table("user_memory_interactions").delete().eq("user_id", user_id).execute()
                
                # Delete memory records
                self.client.table("user_memories").delete().eq("user_id", user_id).execute()
                
                # Delete the user
                self.client.table("users").delete().eq("id", user_id).execute()
                
                if not silent:
                    print(f"Deleted user and related memory records: {user_id}")
            except Exception as e:
                if not silent:
                    print(f"Failed to delete user {user_id}: {str(e)}")
        
        # Delete other resources
        for resource_type, resource_ids in self.other_resources.items():
            for resource_id in resource_ids:
                try:
                    self.client.table(resource_type).delete().eq("id", resource_id).execute()
                    if not silent:
                        print(f"Deleted {resource_type}: {resource_id}")
                except Exception as e:
                    if not silent:
                        print(f"Failed to delete {resource_type} {resource_id}: {str(e)}")


async def run_simple_test():
    """Run a simple test to verify the TestDataManager."""
    # Create a test data manager
    manager = TestDataManager()
    
    try:
        # Query schema info
        await manager.query_schema_info()
        
        # Set up a test environment
        homeowner_id, contractor_id, project_id, bid_card_id = await manager.setup_basic_test_environment()
        
        # Create a bid
        bid_id = await manager.create_bid(
            project_id=project_id,
            contractor_id=contractor_id,
            bid_card_id=bid_card_id,
            amount=1500
        )
        
        # Create memories
        await manager.create_user_memory(user_id=homeowner_id)
        await manager.create_user_memory(user_id=contractor_id)
        
        # Add interactions
        await manager.add_memory_interaction(
            user_id=homeowner_id,
            interaction_type="project_created",
            interaction_data={
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        await manager.add_memory_interaction(
            user_id=contractor_id,
            interaction_type="bid_created",
            interaction_data={
                "bid_id": bid_id,
                "project_id": project_id,
                "amount": 1500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        print("\nTest data manager working correctly!")
        
    finally:
        # Clean up test data
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(run_simple_test())
