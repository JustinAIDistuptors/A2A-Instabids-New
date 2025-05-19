import asyncio
import os
import logging
import re
import pydantic
import uuid
import json
import sys
from pathlib import Path
import argparse
from typing import Dict, Any, Optional, List
import traceback

import sys # Add sys import
from pathlib import Path # Added import
import argparse # ADDED
# Add the project root to sys.path to allow imports from 'src'
# __file__ is /app/tools/run_homeowner_agent.py inside Docker
# os.path.dirname(__file__) is /app/tools
# os.path.join(os.path.dirname(__file__), '..') is /app
project_root_for_imports = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root_for_imports)

from dotenv import load_dotenv
from supabase import create_async_client, AsyncClient as SupabaseClient
from pydantic.errors import PydanticUserError
from postgrest.exceptions import APIError
import sys
import traceback
import json
from src.instabids.agents.homeowner_agent import HomeownerAgent, HomeownerAgentInput, HomeownerAgentOutput
from src.instabids.memory.persistent_memory import PersistentMemory
from src.instabids.data.supabase_client import get_supabase_client
from typing import Dict, Any, Optional, List

# Set SUPABASE_KEY early, before instabids imports, for OpenAPIToolset initialization
_temp_supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if _temp_supabase_service_role_key:
    os.environ["SUPABASE_KEY"] = _temp_supabase_service_role_key
else:
    _hardcoded_service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rZmJ4dndtdXhlYmdnZmJsamduIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NjA3ODQyMSwiZXhwIjoyMDYxNjU0NDIxfQ.tYXiJWcCUW1qufYDL-9wk9TZu0EQOWrTpA1FBhr6DOw"
    os.environ["SUPABASE_KEY"] = _hardcoded_service_key

print(f"CASCADE_DEBUG: Pydantic version: {pydantic.__version__}")

project_root_for_config_and_log = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def setup_logging():
    log_file_path = project_root_for_config_and_log / "agent_run.log"
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    file_handler = logging.FileHandler(log_file_path, mode='w')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    
    log_message_content = f"Logging configured. Log file: {str(log_file_path)}"
    root_logger.info(log_message_content)

setup_logging()

logger = logging.getLogger(__name__)

def global_exception_handler(exc_type, exc_value, exc_traceback):
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_string = "".join(tb_lines)

    debug_log_path = project_root_for_config_and_log / "agent_run_debug_copy.log"
    try:
        with open(debug_log_path, 'a') as f_debug:
            f_debug.write("\n--- GLOBAL UNHANDLED EXCEPTION TRACEBACK ---\n")
            f_debug.write(tb_string)
            f_debug.write("\n--- END GLOBAL UNHANDLED EXCEPTION TRACEBACK ---\n")
    except Exception as e_handler:
        print(f"CRITICAL: Failed to write unhandled exception to debug log: {e_handler}", file=sys.stderr)
        print(f"ORIGINAL UNHANDLED EXCEPTION:\n{tb_string}", file=sys.stderr)
        sys.stderr.flush()
    
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

async def main():
    sys.excepthook = global_exception_handler

    parser = argparse.ArgumentParser(description="Run Homeowner Agent interactively.")
    parser.add_argument("--initial-message", type=str, help="Optional initial message from the user.")
    args = parser.parse_args()

    agent = None
    persistent_memory_instance = None
    supabase_client: Optional[SupabaseClient] = None
    test_user_id = str(uuid.uuid4())
    session_id = test_user_id

    try:
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL", "https://mkfbxvwmuxebggfbljgn.supabase.co")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rZmJ4dndtdXhlYmdnZmJsamduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTM0NzMzMjUsImV4cCI6MjAyOTA0OTMyNX0.yQce0P3NqD2x19FHF9u0h0xO8F2gS9jXj0S6CRKjD6Y")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rZmJ4dndtdXhlYmdnZmJsamduIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcxMzQ3MzMyNSwiZXhwIjoyMDI5MDQ5MzI1fQ.y2YYx_0Dpp09xQCoq_4cTwK72RGD04_0cf4l4n4sV1E")
        mem0_api_key_from_env = os.getenv("MEM0_API_KEY", "mem0_YOU_SHOULD_REPLACE_THIS_WITH_YOUR_OWN_MEM0_KEY")
        openai_api_key_from_env = os.getenv("OPENAI_API_KEY", "")
        gemini_api_key_from_env = os.getenv("GEMINI_API_KEY_FROM_ENV", "AIzaSyAOgdJnkn09hlOAgXNUVAvPcRNhbg_7RUQ")

        if not gemini_api_key_from_env:
            logger.error("GEMINI_API_KEY_FROM_ENV is not set. Please set it in your environment or .env file.")
            return
        os.environ["GEMINI_API_KEY"] = gemini_api_key_from_env

        logger.info(f"Supabase URL: {supabase_url}")
        logger.info(f"Supabase Anon Key: {'Set' if supabase_anon_key else 'Not Set'}")
        logger.info(f"Supabase Service Key: {'Set' if supabase_service_key else 'Not Set'}")
        logger.info(f"Mem0 API Key: {'Set' if mem0_api_key_from_env else 'Not Set'}")
        logger.info(f"OpenAI API Key: {'Set (but may be empty)' if openai_api_key_from_env is not None else 'Not Set'}")

        supabase_client = await get_supabase_client()
        if not supabase_client:
            logger.error("Failed to initialize Supabase client.")
            return

        logger.info(f"Using test_user_id: {test_user_id} and session_id: {session_id}")

        logger.info(f"Ensuring test user {test_user_id} exists in 'users' table.")
        user_data_to_insert = {'id': test_user_id, 'email': f'{test_user_id}@example.com', 'user_type': 'homeowner'}
        try:
            await supabase_client.table("users").insert(user_data_to_insert).execute()
            logger.info(f"Successfully inserted user {test_user_id} into 'users' table.")
        except APIError as e_insert_user:
            if e_insert_user.code == '23505':
                logger.info(f"User {test_user_id} (or email) already exists in 'users' table. Continuing.")
            else:
                error_details = f"Code: {e_insert_user.code}, Message: {getattr(e_insert_user, 'message', 'N/A')}"
                try:
                    json_payload = e_insert_user.json() if callable(getattr(e_insert_user, 'json', None)) else None
                    if json_payload:
                        error_details += f", Details: {json.dumps(json_payload)}"
                except Exception as json_exc:
                    error_details += f", Error getting/parsing JSON details: {str(json_exc)}"
                logger.error(f"Error inserting user {test_user_id} into 'users' table: {error_details}. Full error: {str(e_insert_user)}")
                raise

        persistent_memory_instance = PersistentMemory(user_id=test_user_id, db=supabase_client)
        await persistent_memory_instance.load()
        logger.info(f"PersistentMemory initialized and loaded for user_id: {test_user_id}")

        agent = HomeownerAgent(
            model_name='gemini-1.5-flash-latest',
            memory=persistent_memory_instance,
            mem0_api_key=mem0_api_key_from_env,
            supabase_url=supabase_url,
            supabase_service_role_key=supabase_service_key,
            openai_api_key=openai_api_key_from_env
        )
        logger.info("HomeownerAgent initialized.")

        current_bid_card_state: Dict[str, Any] = {}
        logger.info("--- Starting Interactive Agent Test Session ---")
        logger.info("Type 'quit' or 'exit' to end.")
        logger.info("Type 'show history' to view conversation turns from PersistentMemory.")
        logger.info("Type 'show memory' to view raw memory dump for the user.")

        first_turn = True
        user_text = None

        while True:
            agent_output = None
            try:
                if first_turn and args.initial_message:
                    user_text = args.initial_message
                    logger.info(f"\nUsing initial message from command line: {user_text}")
                    first_turn = False
                else:
                    user_text = await asyncio.to_thread(input, "\nYou: ")

                if user_text.lower() in ["quit", "exit"]:
                    logger.info("Exiting interactive session.")
                    break

                if user_text.lower() == "show history":
                    if persistent_memory_instance:
                        history = await persistent_memory_instance.get_history(session_id=session_id)
                        logger.info(f"\n--- Conversation History (Session: {session_id}) ---")
                        if history:
                            turn_counter = 1
                            current_turn_user = None
                            for speaker, text_content in history:
                                if speaker.lower() == 'user':
                                    current_turn_user = text_content
                                elif speaker.lower() in ['llm', 'model', 'agent'] and current_turn_user is not None:
                                    logger.info(f"  Turn {turn_counter} - User: {current_turn_user}")
                                    logger.info(f"  Turn {turn_counter} - Agent: {text_content}")
                                    current_turn_user = None
                                    turn_counter += 1
                                elif speaker.lower() in ['llm', 'model', 'agent'] and current_turn_user is None:
                                    logger.info(f"  Turn {turn_counter} - Agent (no preceding user message in pair): {text_content}")
                                    turn_counter += 1
                            if current_turn_user is not None:
                                logger.info(f"  Turn {turn_counter} - User: {current_turn_user} (No agent response yet in history)")

                        else:
                            logger.info("  No history found for this session.")
                        logger.info("--- End History ---")
                    else:
                        logger.warning("PersistentMemory not initialized, cannot show history.")
                    continue

                if user_text.lower() == "show memory":
                    if persistent_memory_instance:
                        logger.info(f"\n--- Raw Memory Dump (User: {test_user_id}) ---")
                        await persistent_memory_instance.load()
                        raw_memory_content = persistent_memory_instance._memory_cache
                        logger.info(json.dumps(raw_memory_content, indent=2, default=str))
                        logger.info("--- End Memory Dump ---")
                    else:
                        logger.warning("PersistentMemory not initialized, cannot show memory dump.")
                    continue

                homeowner_input = HomeownerAgentInput(
                    user_input=user_text,
                    current_bid_card_state=current_bid_card_state.copy()
                )

                logger.info(f"Processing input: {homeowner_input.user_input}")
                agent_output: HomeownerAgentOutput = await agent.process_input(
                    homeowner_input,
                    user_id=test_user_id,
                    session_id=session_id
                )
                
                logger.info(f"\nAgent thought: {agent_output.thought}")
                logger.info(f"Agent to you: {agent_output.response_to_user}")

                if agent_output:
                    updated_bid_card_fields = agent_output.model_dump(exclude={"thought", "response_to_user"}, exclude_none=True)
                    current_bid_card_state.update(updated_bid_card_fields)
            
                logger.info(f"\n--- Current Bid Card State ---")
                logger.info(json.dumps(current_bid_card_state, indent=2))
                logger.info("--- End Bid Card State ---")

            except Exception as e_loop:
                logger.error(f"An error occurred during interaction: {e_loop}", exc_info=True)
                error_message_to_user = f"I'm sorry, I encountered an issue: {type(e_loop).__name__}. Let's try that again."
                if agent_output and hasattr(agent_output, 'response_to_user') and agent_output.response_to_user:
                    logger.info(f"\nAgent thought: Error occurred: {e_loop}")
                    logger.info(f"Agent to you: {agent_output.response_to_user} (but an error occurred: {type(e_loop).__name__})")
                else:
                    logger.info(f"\nAgent thought: Error occurred: {e_loop}")
                    logger.info(f"Agent to you: {error_message_to_user}")
                logger.info(f"\n--- Current Bid Card State (at time of error) ---")
                logger.info(json.dumps(current_bid_card_state, indent=2))
                logger.info("--- End Bid Card State ---")

    except APIError as e_setup:
        logger.error(f"A Supabase APIError occurred during setup: {e_setup.code} - {e_setup.message}", exc_info=True)
    except Exception as e_global_setup:
        logger.error(f"An unexpected error occurred during setup: {e_global_setup}", exc_info=True)
        traceback.print_exc()
    finally:
        logger.info("--- Agent run script finished ---")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user (KeyboardInterrupt).")
    except Exception as e_async_run:
        logger.error(f"Critical error running main_async: {e_async_run}", exc_info=True)
        traceback.print_exc()