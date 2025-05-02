"""MessagingAgent: filters communications between homeowners and contractors based on platform rules."""
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime

from instabids_google.adk import LlmAgent as LLMAgent, enable_tracing
from instabids_google.adk.messages import UserMessage
from instabids.tools import supabase_tools, moderation_tool
from instabids.a2a_comm import send_envelope
from memory.persistent_memory import PersistentMemory
from .message_filter import filter_message

# enable stdout tracing for dev envs
enable_tracing("stdout")

SYSTEM_PROMPT = (
    "You are MessagingAgent, responsible for managing communications between homeowners and contractors. "
    "Apply platform rules to filter messages, prevent premature contact information sharing, "
    "and emit 'message.filtered' A2A envelopes when messages are processed. Maintain conversation history "
    "and enforce communication rules until a contractor is selected for connection fee payment."
)

class MessagingAgent(LLMAgent):
    """Concrete ADK agent with message filtering and communication management capabilities."""
    
    def __init__(self, memory: PersistentMemory | None = None) -> None:
        super().__init__(
            name="MessagingAgent",
            tools=[*supabase_tools, moderation_tool],
            system_prompt=SYSTEM_PROMPT,
            memory=memory,
        )
        
    async def process_message(
        self,
        message_content: str,
        project_id: str,
        sender_id: str,
        recipient_id: str,
        is_pre_connection: bool = True
    ) -> Dict[str, Any]:
        """
        Process a message between a homeowner and contractor.
        
        Args:
            message_content: The content of the message
            project_id: The ID of the project the message is related to
            sender_id: The ID of the message sender
            recipient_id: The ID of the message recipient
            is_pre_connection: Whether the message is before contractor selection
            
        Returns:
            Dict containing agent response, message ID, filtered content, and filter status
        """
        # Filter message content based on platform rules
        filtered_content = await self._filter_message(
            message_content,
            project_id,
            sender_id,
            recipient_id,
            is_pre_connection
        )
        
        # Create user message for agent
        user_message = UserMessage(
            content=f"Process message for project {project_id}:\n{filtered_content}"
        )
        
        # Process message with agent
        response = await self.process(user_message)
        
        # Generate message ID
        message_id = f"msg_{project_id}_{sender_id}_{int(datetime.now().timestamp())}"
        
        # Emit A2A envelope for message processed
        send_envelope("message.filtered", {
            "message_id": message_id,
            "project_id": project_id,
            "sender": sender_id,
            "recipient": recipient_id,
            "filtered": filtered_content != message_content,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "agent_response": response.content,
            "message_id": message_id,
            "filtered_content": filtered_content,
            "applied_filters": filtered_content != message_content
        }
    
    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    async def _filter_message(
        self,
        content: str,
        project_id: str,
        sender_id: str,
        recipient_id: str,
        is_pre_connection: bool
    ) -> str:
        """Apply platform-specific filtering rules to messages."""
        # 1) Basic moderation
        moderated_content = await moderation_tool.call(content=content)
        
        # 2) Business rule filtering
        filtered_content = await filter_message(
            moderated_content,
            project_id,
            sender_id,
            recipient_id,
            is_pre_connection
        )
        
        return filtered_content