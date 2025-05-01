"""MessagingAgent: filters communications between homeowners and contractors based on platform rules."""
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime

from google.adk import LLMAgent, enable_tracing
from google.adk.messages import UserMessage
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
            memory=memory or PersistentMemory(),
        )
    
    # ────────────────────────────────────────────────────────────────────────
    # Public API used by FastAPI / CLI
    # ────────────────────────────────────────────────────────────────────────

    async def process_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_content: str,
        project_id: str,
        is_pre_connection: bool = True
    ) -> dict[str, Any]:
        """Main entry. Process and filter messages between parties."""
        
        # 1) Get conversation history from Supabase
        from instabids.data_access import get_conversation_history
        
        history = await get_conversation_history(project_id, sender_id, recipient_id)
        
        # 2) Build prompt for ADK
        prompt = f"Process message for project {project_id}:\n{message_content}"
        user_msg = UserMessage(prompt)
        response = await self.chat(user_msg)
        
        # 3) Apply message filtering rules
        filtered_content = await self._filter_message(
            message_content, 
            project_id, 
            sender_id, 
            recipient_id,
            is_pre_connection
        )
        
        # 4) Persist message to Supabase
        from instabids.data_access import save_message
        
        message_id = await save_message(
            project_id=project_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            original_content=message_content,
            filtered_content=filtered_content,
            timestamp=datetime.now().isoformat(),
            is_pre_connection=is_pre_connection
        )
        
        # 5) Emit A2A envelope
        await send_envelope("message.filtered", {
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
