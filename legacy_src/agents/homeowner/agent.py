"""
Implementation for the Homeowner Agent.

Handles homeowner onboarding, project creation (photo-first optional flow),
competitive quote upload, and bid selection interactions. Orchestrates
calls to utility functions and ADK flows.
"""

import logging
from typing import Any, Dict, Optional, Union, List, Tuple, Callable
import uuid
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
import asyncio
import datetime

# Google Cloud Vision client library
from google.cloud import vision

# ADK Components
# Use instabids_google.adk instead of google.adk to fix import conflicts
from instabids_google.adk.agents import Agent as AdkAgent
from instabids_google.adk.flows import LLMFlow, FlowInput, FlowResult
from instabids_google.adk.models import Llm
from instabids_google.adk.models.google import Gemini
from instabids_google.adk.memory import Memory
from instabids_google.adk.memory.in_memory import InMemoryMemory

# Local A2A Types and Client
from ...a2a_types.core import (
    Task, Message, Artifact, AgentId, TaskId, MessageId, 
    Agent as A2aAgentInfo, ArtifactType, TaskStatus
)
from ...a2a_comm import client as a2a_client

# Local utilities and flows
from . import utils as homeowner_utils
from . import flows as homeowner_flows

# Import PersistentMemory
from ...memory.persistent_memory import PersistentMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

AGENT_ID: AgentId = "homeowner-agent-001"

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

# --- Flow Session Management ---
class FlowSession:
    """
    Manages a session for a specific ADK flow.
    
    Tracks flow state, input/output, and handles flow execution.
    """
    
    def __init__(
        self, 
        flow: LLMFlow, 
        task_id: TaskId, 
        initial_input: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new flow session.
        
        Args:
            flow: The LLMFlow to execute
            task_id: The ID of the task this flow is for
            initial_input: Optional initial input for the flow
        """
        self.flow = flow
        self.task_id = task_id
        self.state: Dict[str, Any] = {}
        self.messages: List[Dict[str, Any]] = []
        self.initial_input = initial_input or {}
        self.result: Optional[FlowResult] = None
        
    async def start(self) -> FlowResult:
        """
        Start the flow execution.
        
        Returns:
            The result of the flow execution
        """
        logger.info(f"Starting flow for task {self.task_id}")
        flow_input = FlowInput(
            **self.initial_input,
            task_id=self.task_id,
        )
        self.result = await self.flow.execute(flow_input)
        return self.result
        
    def get_result(self) -> Optional[FlowResult]:
        """
        Get the current result of the flow.
        
        Returns:
            The current flow result, or None if not completed
        """
        return self.result


class HomeownerAgent:
    """
    Agent responsible for homeowner-related operations.
    
    Handles project creation, bid management, and homeowner interactions.
    """
    
    def __init__(self, memory: Optional[PersistentMemory] = None):
        """
        Initialize the Homeowner Agent.
        
        Args:
            memory: Optional persistent memory system
        """
        self.agent_info = A2aAgentInfo(
            id=AGENT_ID,
            name="Homeowner Agent",
            description="Handles homeowner project creation and bid management",
            capabilities=[
                "project_creation",
                "photo_analysis",
                "bid_management",
                "homeowner_interaction",
            ],
        )
        
        # Initialize memory
        self.memory = memory or PersistentMemory()
        
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
            
        # Initialize ADK agent
        self.adk_agent = AdkAgent(
            name="HomeownerAgent",
            memory=InMemoryMemory(),  # Use ADK's memory for flow execution
        )
        
        # Initialize Vision client
        self.vision_client = None
        try:
            self.vision_client = vision.ImageAnnotatorClient()
            logger.info("Successfully initialized Vision client")
        except Exception as e:
            logger.error(f"Failed to initialize Vision client: {e}", exc_info=True)
            
        # Flow management
        self._active_flow_sessions: Dict[TaskId, FlowSession] = {}
        
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
            if task.type == "create_project":
                await self._handle_create_project(task)
            elif task.type == "analyze_photos":
                await self._handle_analyze_photos(task)
            elif task.type == "manage_bids":
                await self._handle_manage_bids(task)
            elif task.type == "homeowner_chat":
                await self._handle_homeowner_chat(task)
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
            
    async def _handle_create_project(self, task: Task) -> None:
        """
        Handle a create_project task.
        
        Args:
            task: The task containing project details
        """
        logger.info(f"Handling create_project task: {task.id}")
        
        # Extract project details from task
        project_details = task.details.get("project", {})
        photos = task.details.get("photos", [])
        
        # Validate required fields
        if not project_details.get("description"):
            raise ValueError("Project description is required")
            
        # Create project in database
        try:
            # TODO: Implement project creation logic
            project_id = str(uuid.uuid4())  # Placeholder
            
            # Return result
            result = {
                "project_id": project_id,
                "status": "created",
            }
            
            # Update task with result
            await self._update_task_status(task.id, "COMPLETED", result=result)
            
        except Exception as e:
            logger.error(f"Error creating project: {e}", exc_info=True)
            raise
            
    async def _handle_analyze_photos(self, task: Task) -> None:
        """
        Handle an analyze_photos task.
        
        Args:
            task: The task containing photo details
        """
        logger.info(f"Handling analyze_photos task: {task.id}")
        
        # Extract photo details from task
        photos = task.details.get("photos", [])
        
        if not photos:
            raise ValueError("No photos provided for analysis")
            
        # Analyze photos using Vision API
        if not self.vision_client:
            raise RuntimeError("Vision client not available")
            
        # TODO: Implement photo analysis logic
        
        # Return result
        result = {
            "analysis": "Placeholder analysis result",
        }
        
        # Update task with result
        await self._update_task_status(task.id, "COMPLETED", result=result)
        
    async def _handle_manage_bids(self, task: Task) -> None:
        """
        Handle a manage_bids task.
        
        Args:
            task: The task containing bid management details
        """
        logger.info(f"Handling manage_bids task: {task.id}")
        
        # Extract bid details from task
        project_id = task.details.get("project_id")
        action = task.details.get("action")
        
        if not project_id:
            raise ValueError("Project ID is required")
            
        if not action:
            raise ValueError("Bid management action is required")
            
        # TODO: Implement bid management logic
        
        # Return result
        result = {
            "status": "success",
            "action": action,
        }
        
        # Update task with result
        await self._update_task_status(task.id, "COMPLETED", result=result)
        
    async def _handle_homeowner_chat(self, task: Task) -> None:
        """
        Handle a homeowner_chat task.
        
        Args:
            task: The task containing chat details
        """
        logger.info(f"Handling homeowner_chat task: {task.id}")
        
        # Extract chat details from task
        message = task.details.get("message")
        
        if not message:
            raise ValueError("Chat message is required")
            
        # Create or get flow session
        if task.id not in self._active_flow_sessions:
            # Initialize a new flow session
            flow = homeowner_flows.create_chat_flow(self.adk_agent)
            session = FlowSession(
                flow=flow,
                task_id=task.id,
                initial_input={"message": message},
            )
            self._active_flow_sessions[task.id] = session
        else:
            session = self._active_flow_sessions[task.id]
            
        # Execute flow
        result = await session.start()
        
        # Clean up flow session if completed
        if result.is_final:
            if task.id in self._active_flow_sessions:
                del self._active_flow_sessions[task.id]
                
        # Return result
        chat_result = {
            "response": result.response,
            "is_final": result.is_final,
        }
        
        # Update task with result
        await self._update_task_status(task.id, "COMPLETED", result=chat_result)
        
    def _cancel_flow_session(self, task_id: TaskId) -> None:
        """
        Cancel an active flow session.
        
        Args:
            task_id: The ID of the task whose flow session to cancel
        """
        if task_id in self._active_flow_sessions:
            del self._active_flow_sessions[task_id]
            logger.info(f"Cancelled flow session for task {task_id}")
            
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
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        if status in ["COMPLETED", "FAILED", "CANCELLED"]:
            update_data["completed_at"] = update_data["updated_at"]
        if result:
            try:
                update_data["result"] = json.dumps(result)
            except TypeError:
                logger.error(f"Task {task_id}: Result dictionary is not JSON serializable.")
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