"""Agent for on‑platform messaging between homeowners and contractors."""
from __future__ import annotations
# Use the vendor namespace if that's the standard in this project
# from google.adk import LlmAgent
from instabids_google.adk import LlmAgent
from instabids.data.message_repo import (
    create_thread, get_messages, create_message, add_participant # Assuming add_participant might be needed
)
from instabids.a2a_comm import send_envelope
import logging

logger = logging.getLogger(__name__)

class MessagingAgent(LlmAgent):
    """Handles messaging threads and messages."""

    def __init__(self, agent_id: str = "MessagingAgent", **kwargs):
        # Use the vendor namespace LlmAgent if applicable
        super().__init__(agent_id=agent_id, **kwargs)
        logger.info(f"{agent_id} initialized.")

    async def handle_create_thread(self, user_id: str, project_id: str, initial_participants: list[dict] = None) -> dict:
        """Creates a new thread and adds initial participants.

        Args:
            user_id: The ID of the user creating the thread.
            project_id: The ID of the related project.
            initial_participants: Optional list of dicts [{'user_id': '...', 'role': '...'}] to add.

        Returns:
            A dictionary containing the thread_id or an error.
        """
        logger.info(f"Handling create_thread request for project {project_id} by user {user_id}")
        try:
            # create_thread in repo now handles adding the creator
            thread = create_thread(project_id, user_id)
            if not thread:
                logger.error(f"Failed to create thread for project {project_id}")
                return {"error": "Failed to create thread"}

            thread_id = thread["id"]
            logger.info(f"Thread {thread_id} created for project {project_id}")

            # Add other initial participants if provided
            if initial_participants:
                for p in initial_participants:
                    added = add_participant(thread_id, p['user_id'], p['role'])
                    if not added:
                        logger.warning(f"Failed to add participant {p['user_id']} with role {p['role']} to thread {thread_id}")
                    else:
                         logger.info(f"Added participant {p['user_id']} ({p['role']}) to thread {thread_id}")

            return {"thread_id": thread_id}
        except Exception as e:
            logger.exception(f"Error in handle_create_thread for project {project_id}: {e}")
            return {"error": "Internal server error during thread creation"}

    async def handle_send_message(self, user_id: str,
                                  thread_id: str, content: str,
                                  message_type: str = "text", metadata: dict = None
                                 ) -> dict:
        """Sends a message to a thread and notifies via A2A.

        Args:
            user_id: The ID of the user sending the message.
            thread_id: The ID of the thread to send to.
            content: The message content.
            message_type: The type of message (e.g., 'text', 'image').
            metadata: Optional JSON metadata associated with the message.

        Returns:
            The created message data or an error dictionary.
        """
        logger.info(f"Handling send_message request by user {user_id} to thread {thread_id}")
        try:
            msg = create_message(thread_id, user_id, content, message_type, metadata)
            if not msg:
                 logger.error(f"Failed to create message in thread {thread_id} by user {user_id}")
                 return {"error": "Failed to send message. Ensure you are a participant."} # RLS might prevent non-participants

            logger.info(f"Message {msg['id']} sent to thread {thread_id}")
            # Send A2A event asynchronously
            # Consider making send_envelope truly async if it blocks
            await send_envelope("message.sent", {
                "thread_id": thread_id,
                "message_id": msg["id"],
                "sender_id": user_id
            })
            logger.info(f"Sent A2A event 'message.sent' for message {msg['id']}")
            return msg
        except Exception as e:
            logger.exception(f"Error in handle_send_message for thread {thread_id}: {e}")
            return {"error": "Internal server error during message sending"}

    async def handle_get_messages(self, user_id: str,
                                  thread_id: str
                                 ) -> dict:
        """Retrieves messages for a specific thread.

        Args:
            user_id: The ID of the user requesting messages (used for RLS checks).
            thread_id: The ID of the thread.

        Returns:
            A dictionary containing a list of messages or an error.
        """
        # Note: user_id isn't strictly needed by the repo function get_messages
        # itself if RLS is correctly configured and the request context has the user.
        # However, keeping it here might be useful for logging or future checks.
        logger.info(f"Handling get_messages request by user {user_id} for thread {thread_id}")
        try:
            msgs = get_messages(thread_id)
            # The repo function now returns [] on error, so no need to check for None explicitly
            logger.info(f"Retrieved {len(msgs)} messages for thread {thread_id}")
            return {"messages": msgs}
        except Exception as e:
            logger.exception(f"Error in handle_get_messages for thread {thread_id}: {e}")
            return {"error": "Internal server error while fetching messages"}

    # Potential future handlers:
    # async def handle_add_participant(self, user_id: str, thread_id: str, new_user_id: str, role: str) -> dict:
    #     # Check if user_id has permission to add participants
    #     logger.info(f"User {user_id} attempting to add {new_user_id} ({role}) to thread {thread_id}")
    #     participant = add_participant(thread_id, new_user_id, role)
    #     if not participant:
    #         return {"error": f"Failed to add participant {new_user_id}"}
    #     # Send A2A event? ('participant.added')
    #     return {"participant": participant}

    # async def handle_get_user_threads(self, user_id: str) -> dict:
    #     logger.info(f"Handling get_user_threads request for user {user_id}")
    #     threads = get_user_threads(user_id)
    #     return {"threads": threads}
