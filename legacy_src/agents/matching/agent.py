"""
Placeholder implementation for the Matching Agent.

This agent connects relevant projects (Bid Cards) with suitable contractors.
"""

import logging
from typing import Any, Dict, Optional, List
import os
import uuid  # Import uuid
import json  # Add missing json import
import datetime  # Add missing datetime import
from dotenv import load_dotenv
from supabase import create_client, Client

# Assuming ADK and A2A types are accessible
# Adjust import paths based on final project structure
from google.adk.agents import Agent as AdkAgent
from ...a2a_types.core import (
    Task,
    Message,
    Artifact,
    AgentId,
    TaskId,
    MessageId,
    Agent as A2aAgentInfo,
    ArtifactType,
    TaskStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "matching-agent-001"  # Example ID - Should be configurable

# --- Agent Registry (Simple Placeholder) ---
# TODO: Centralize agent registry/discovery
AGENT_REGISTRY_JSON = os.getenv("AGENT_REGISTRY", "{}")
try:
    AGENT_REGISTRY: Dict[AgentId, Dict[str, str]] = json.loads(AGENT_REGISTRY_JSON)
    logger.info(f"Loaded agent registry: {list(AGENT_REGISTRY.keys())}")
except json.JSONDecodeError:
    logger.error(
        "Failed to parse AGENT_REGISTRY env var as JSON. Using empty registry."
    )
    AGENT_REGISTRY = {}

# --- Supabase Setup ---
# TODO: Move to shared database module
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class MatchingAgent:
    """
    Agent responsible for matching projects with contractors.
    
    This agent:
    1. Receives new project notifications
    2. Finds suitable contractors based on project details
    3. Creates bid cards for contractors
    4. Handles contractor responses
    """

    def __init__(self):
        """Initialize the Matching Agent."""
        self.agent_info = A2aAgentInfo(
            id=AGENT_ID,
            name="Matching Agent",
            description="Matches projects with suitable contractors",
            capabilities=["project_matching", "bid_card_creation"],
        )

        # Initialize Supabase client if credentials available
        self.db = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.db = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Successfully connected to Supabase")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}", exc_info=True)
        else:
            logger.warning(
                "Supabase credentials not found. Database operations will be unavailable."
            )

        # Initialize ADK agent (placeholder)
        # self.adk_agent = AdkAgent(name="MatchingAgent")

        # Task tracking
        self._active_tasks: Dict[TaskId, Task] = {}

    async def process_task(self, task: Task) -> None:
        """
        Process an incoming task.
        
        Args:
            task: The task to process
        """
        logger.info(f"Processing task: {task.id} - {task.type}")

        # Store task in our active tasks
        self._active_tasks[task.id] = task

        # Store task in DB
        await self._store_task(task)

        # Update task status to IN_PROGRESS
        await self._update_task_status(task.id, "IN_PROGRESS")

        try:
            # Handle task based on type
            if task.type == "match_project":
                await self._handle_match_project(task)
            elif task.type == "process_contractor_response":
                await self._handle_contractor_response(task)
            else:
                logger.warning(f"Unknown task type: {task.type}")
                await self._update_task_status(
                    task.id, "FAILED", error_message=f"Unknown task type: {task.type}"
                )
                return

            # Mark task as completed
            await self._update_task_status(task.id, "COMPLETED")

        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}", exc_info=True)
            await self._update_task_status(
                task.id, "FAILED", error_message=f"Error: {str(e)}"
            )

    async def _handle_match_project(self, task: Task) -> None:
        """
        Handle a match_project task.
        
        Args:
            task: The task containing project details
        """
        logger.info(f"Handling match_project task: {task.id}")

        # Extract project details from task
        project_id = task.details.get("project_id")
        if not project_id:
            raise ValueError("No project_id provided in task details")

        # TODO: Implement project matching logic
        # 1. Retrieve project details from database
        # 2. Find suitable contractors
        # 3. Create bid cards
        # 4. Notify contractors

        # Placeholder implementation
        logger.info(f"Would match project {project_id} with contractors")

    async def _handle_contractor_response(self, task: Task) -> None:
        """
        Handle a contractor response to a bid card.
        
        Args:
            task: The task containing response details
        """
        logger.info(f"Handling contractor_response task: {task.id}")

        # Extract response details from task
        bid_id = task.details.get("bid_id")
        response = task.details.get("response")
        if not bid_id or response is None:
            raise ValueError("Missing bid_id or response in task details")

        # TODO: Implement response handling logic
        # 1. Update bid status in database
        # 2. Notify homeowner if accepted
        # 3. Update project status if needed

        # Placeholder implementation
        logger.info(f"Would process contractor response for bid {bid_id}: {response}")

    async def _store_task(self, task: Task) -> None:
        """
        Store a task in the database.
        
        Args:
            task: The task to store
        """
        if not self.db:
            logger.warning("Cannot store task: DB client not available")
            return

        # Convert task to DB format
        task_data = {
            "a2a_task_id": task.id,
            "type": task.type,
            "status": "RECEIVED",
            "details": json.dumps(task.details),
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }

        try:
            insert_res = await self.db.table("tasks").insert(task_data).execute()
            if insert_res.data:
                logger.info(f"Successfully stored task {task.id} in DB")
            else:
                logger.warning(f"No data returned when storing task {task.id}")
        except Exception as e:
            # Check if it's a duplicate key error
            if "duplicate key" in str(e):
                logger.warning(
                    f"Task {task.id} already exists in DB (detected via details). Skipping initial store."
                )
            else:
                logger.error(f"Failed to store initial task {task.id}: {e}", exc_info=True)

    async def _update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Updates task status in the database.
        
        Args:
            task_id: ID of the task to update
            status: New status to set
            result: Optional result data
            error_message: Optional error message
        """
        log_message = f"Task {task_id}: Status changed to {status}."
        if result:
            log_message += f" Result: {result}"
        if error_message:
            log_message += f" Error: {error_message}"
        logger.info(log_message)

        if not self.db:
            logger.error(f"Cannot update task {task_id} status: DB client not available.")
            return

        update_data = {
            "status": status,
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }
        if status in ["COMPLETED", "FAILED", "CANCELLED"]:
            update_data["completed_at"] = update_data["updated_at"]
        if result:
            try:
                update_data["result"] = json.dumps(result)
            except TypeError:
                logger.error(
                    f"Task {task_id}: Result dictionary is not JSON serializable."
                )
                update_data["result"] = json.dumps({"error": "Result not serializable"})
        if error_message:
            update_data["error_message"] = error_message

        try:
            update_res = (
                await self.db.table("tasks")
                .update(update_data)
                .eq("a2a_task_id", task_id)
                .execute()
            )
            if update_res.data:
                logger.info(f"Successfully updated status for task {task_id} in DB.")
            else:
                logger.warning(
                    f"No task found with a2a_task_id '{task_id}' to update status."
                )
        except Exception as e:
            logger.error(
                f"Failed to update status for task {task_id} in DB: {e}", exc_info=True
            )

    def get_agent_info(self) -> A2aAgentInfo:
        """Returns the configuration/details of this agent."""
        return self.agent_info


# --- Agent Instantiation ---
# matching_agent_instance = MatchingAgent()