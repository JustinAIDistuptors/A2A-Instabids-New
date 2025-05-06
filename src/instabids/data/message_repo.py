"""Message repository for threads & messages."""
from typing import List, Dict, Any
from instabids.data.supabase_client import create_client

_sb = create_client()

def create_thread(project_id: str, created_by: str) -> Dict[str, Any]:
    # Note: SQL uses 'threads' table, not 'message_threads'
    # Note: SQL doesn't have 'created_by' on threads table. Participants table links users.
    # Need to adjust based on actual SQL schema.
    # Let's assume we need to insert into 'threads' and then 'thread_participants'.

    # 1. Create the thread
    thread_resp = _sb.table("threads").insert({
        "project_id": project_id
    }).single().execute()

    if thread_resp.error:
        # Handle error appropriately, e.g., raise exception or log
        print(f"Error creating thread: {thread_resp.error}")
        return None # Or raise an exception

    thread_data = thread_resp.data
    thread_id = thread_data['id']

    # 2. Add creator as participant (assuming 'homeowner' role for creator? Needs clarification)
    # Role needs to be determined based on the user creating the thread.
    # For now, let's assume 'system' or require role passed in.
    # For this example, let's assume 'homeowner' for created_by user.
    part_resp = _sb.table("thread_participants").insert({
        "thread_id": thread_id,
        "user_id": created_by,
        "role": "homeowner" # ASSUMPTION - Needs verification
    }).execute()

    if part_resp.error:
        # Handle participant creation error (maybe rollback thread creation?)
        print(f"Error adding participant: {part_resp.error}")
        # Consider deleting the thread if participant add fails
        _sb.table("threads").delete().eq("id", thread_id).execute()
        return None # Or raise an exception

    # Return the created thread data
    return thread_data

def get_thread(thread_id: str) -> Dict[str, Any]:
    # Fetching from 'threads' table as per SQL
    resp = _sb.table("threads").select("*, participants:thread_participants(*)") \
             .eq("id", thread_id).maybe_single().execute() # Use maybe_single for safety

    if resp.error:
        print(f"Error fetching thread: {resp.error}")
        return None
    return resp.data

def delete_thread(thread_id: str) -> None:
    # Deleting from 'threads' table
    # Cascades should handle participants and messages due to FK constraints
    resp = _sb.table("threads").delete().eq("id", thread_id).execute()
    if resp.error:
        print(f"Error deleting thread: {resp.error}")
        # Handle error as needed

def create_message(thread_id: str, sender_id: str,
                   content: str, message_type: str = "text", # Use message_type from SQL
                   metadata: dict = None
                  ) -> Dict[str, Any]:
    insert_data = {
        "thread_id": thread_id,
        "sender_id": sender_id,
        "content": content,
        "message_type": message_type # Renamed from content_type
    }
    if metadata:
        insert_data["metadata"] = metadata

    # Inserting into 'messages' table
    resp = _sb.table("messages").insert(insert_data).single().execute()

    if resp.error:
        print(f"Error creating message: {resp.error}")
        return None
    return resp.data

def get_messages(thread_id: str) -> List[Dict[str, Any]]:
    # Selecting from 'messages' table
    resp = _sb.table("messages").select("*, sender:users(id, email, full_name)") \
             .eq("thread_id", thread_id) \
             .order("created_at", desc=False) \
             .execute()
    if resp.error:
        print(f"Error fetching messages: {resp.error}")
        return [] # Return empty list on error
    return resp.data

def add_participant(thread_id: str, user_id: str, role: str) -> Dict[str, Any]:
    """Adds a user to a thread.

    Args:
        thread_id: The ID of the thread.
        user_id: The ID of the user to add.
        role: The role of the user ('homeowner', 'contractor', 'system').

    Returns:
        The participant data if successful, None otherwise.
    """
    resp = _sb.table("thread_participants").insert({
        "thread_id": thread_id,
        "user_id": user_id,
        "role": role
    }).single().execute()

    if resp.error:
        print(f"Error adding participant {user_id} to thread {thread_id}: {resp.error}")
        # Check for specific errors like duplicate key violation (already exists)
        if '23505' in str(resp.error): # Unique violation code for PostgreSQL
             print(f"User {user_id} is already a participant in thread {thread_id}.")
             # Optionally, return existing participant info or just None
        return None
    return resp.data

def get_user_threads(user_id: str) -> List[Dict[str, Any]]:
    """Fetches all threads a user is participating in.

    Args:
        user_id: The ID of the user.

    Returns:
        A list of thread data the user participates in.
    """
    # We need to join threads with thread_participants
    # RLS policy on threads handles the filtering based on auth.uid(),
    # so a simple select on threads should work if run by the authenticated user.
    # If run server-side with service key, we need explicit filtering.
    # Assuming this is called with user context (RLS handles filtering):
    resp = _sb.table("threads") \
             .select("id, project_id, title, created_at, updated_at, participants:thread_participants(user_id, role)") \
             .execute()
    # If run with service role key (bypassing RLS), need explicit join/filter:
    # resp = _sb.table('thread_participants') \
    #          .select('thread:threads(*, participants:thread_participants(*))') \
    #          .eq('user_id', user_id) \
    #          .execute()
    # This would return a list like [{'thread': {...}}, {'thread': {...}}] - needs flattening

    if resp.error:
        print(f"Error fetching threads for user {user_id}: {resp.error}")
        return []

    # If using the service role approach, flatten the list:
    # return [item['thread'] for item in resp.data if item.get('thread')]
    return resp.data
