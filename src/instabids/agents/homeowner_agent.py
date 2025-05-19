"""HomeownerAgent: multimodal concierge for homeowners."""
from __future__ import annotations
import asyncio
import json
import logging # Ensure logging is imported
logger = logging.getLogger(__name__) # ADDED
import os
from typing import Any, Dict, List, Optional, Tuple, Union
# import google # google.generativeai will be imported specifically for patching
from pathlib import Path
import inspect # <--- ADDED IMPORT INSPECT HERE
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast
import uuid # For generating session_id
from google.generativeai import types as genai_types # Ensure this alias is available
from google.generativeai import GenerativeModel # ADDED: Missing import
from google.adk.agents.invocation_context import InvocationContext

# --- BEGIN MONKEY PATCH for google-adk==0.2.0 compatibility ---
# LlmAgent in google-adk==0.2.0 expects 'from google.generativeai import protos'
# and then protos.Part, protos.Content, etc.
# However, google-generativeai==0.5.4 (its dependency) does not expose 'protos' this way.
# We are making google.generativeai.protos an alias for the GAPIC types module
# where these types actually reside.
try:
    import google.generativeai
    import google.ai.generativelanguage_v1beta.types as gapic_types # The actual source of protos

    logging.info("Attempting to monkey-patch 'google.generativeai.protos' for google-adk compatibility...")

    # Ensure google.generativeai.protos exists and is essentially an alias for gapic_types
    # or an object we can add attributes to.
    if not hasattr(google.generativeai, 'protos'):
        # If protos doesn't exist at all, create a simple namespace object for it.
        # This might be safer than aliasing the entire gapic_types module if ADK only needs specific items.
        class ProtosNamespace:
            pass
        google.generativeai.protos = ProtosNamespace()
        logging.info("'google.generativeai.protos' created as a new namespace object.")
    else:
        logging.info(f"'google.generativeai.protos' already exists (type: {type(google.generativeai.protos)}).")

    # Attributes to alias directly from gapic_types to google.generativeai.protos
    attributes_to_alias = [
        'Part', 'Content', 'Tool', 'FunctionDeclaration', 
        'ToolConfig', 'FunctionCallingConfig', 'GenerateContentResponse'
    ]

    for attr_name in attributes_to_alias:
        if hasattr(gapic_types, attr_name):
            setattr(google.generativeai.protos, attr_name, getattr(gapic_types, attr_name))
            logging.info(f"'google.generativeai.protos.{attr_name}' has been set to 'gapic_types.{attr_name}'.")
        else:
            logging.warning(f"Could not find '{attr_name}' in 'gapic_types'. 'google.generativeai.protos.{attr_name}' NOT set.")

    # Specifically for FunctionCallingConfig.Mode, ensure it's accessible if ADK needs it.
    # If protos.FunctionCallingConfig is now gapic_types.FunctionCallingConfig, then 
    # protos.FunctionCallingConfig.Mode will naturally point to gapic_types.FunctionCallingConfig.Mode.
    if hasattr(google.generativeai.protos, 'FunctionCallingConfig') and \
       hasattr(gapic_types, 'FunctionCallingConfig') and \
       hasattr(gapic_types.FunctionCallingConfig, 'Mode'):
        logging.info("'google.generativeai.protos.FunctionCallingConfig.Mode' should be accessible via the aliased type.")
    elif hasattr(gapic_types, 'FunctionCallingConfig') and not hasattr(gapic_types.FunctionCallingConfig, 'Mode'):
        logging.warning("'gapic_types.FunctionCallingConfig' exists but does not have a 'Mode' attribute.")
    elif not hasattr(gapic_types, 'FunctionCallingConfig'):
        logging.warning("'FunctionCallingConfig' not found in 'gapic_types', so 'Mode' cannot be patched.")

    logging.info("Monkey-patching for 'google.generativeai.protos' completed.")

except ImportError as e:
    logging.error(f"Failed to import modules required for monkey-patching: {e}")
except Exception as e:
    logging.error(f"An unexpected error occurred during monkey-patching: {e}")
# --- END MONKEY PATCH ---


# Now, LlmAgent can be imported, and its internal 'from google.generativeai import protos' should work.
from src.instabids_google.adk.llm_agent import LLMAgent # <--- UPDATED TO LLMAgent (uppercase)
# from instabids_google.adk.llm_agent import LlmAgent # Using ADK's LlmAgent
from pydantic import BaseModel, Field, PrivateAttr, field_validator, ValidationError
from mem0 import MemoryClient # type: ignore
import os
from ..tools import get_supabase_tools, openai_vision_tool
from ..memory import PersistentMemory # Added import
# import google.generativeai as genai # No longer needed directly here if patch works


# --- Pydantic Schemas ---
class HomeownerAgentInput(BaseModel):
    """Defines the input structure for the HomeownerAgent."""
    user_input: str = Field(description="The raw text input from the user.")
    current_bid_card_state: Optional[Dict[str, Any]] = Field(default=None, description="The current state of the bid card fields collected so far.")
    image_url: Optional[str] = Field(default=None, description="URL of an image provided by the user for context.")
    audio_url: Optional[str] = Field(default=None, description="URL of an audio recording provided by the user.")

class BidCardBase(BaseModel):
    title: Optional[str] = Field(default=None, description="A concise, descriptive title for the project (e.g., 'Living Room Window Replacement', 'Kitchen Faucet Repair').")
    category: Optional[str] = Field(default=None, description="The general category of work (e.g., 'Plumbing', 'Electrical', 'Windows & Doors', 'General Handyman').")
    description: Optional[str] = Field(default=None, description="A general overview of what the homeowner needs done.")
    scope_summary: Optional[str] = Field(default=None, description="Specific details like measurements (e.g., 'window pane 24x36 inches'), material preferences (e.g., 'double-glazed unit'), specific items/areas (e.g., 'living room window'), quantities, or problem descriptions.")
    address: Optional[str] = Field(default=None, description="Street address where the work will be done.")
    city: Optional[str] = Field(default=None, description="City for the project location.")
    state: Optional[str] = Field(default=None, description="State for the project location.")
    zip_code: Optional[str] = Field(default=None, description="Zip code for the project location.")
    urgency: Optional[str] = Field(default=None, description="How soon the work needs to be done (e.g., 'ASAP', 'flexible', 'within 1 month'). Default to 'flexible' if not specified.")
    budget_range: Optional[str] = Field(default=None, description="An estimated budget range (e.g., '$500-$1000'), if the homeowner has one. This is optional.")
    timeline: Optional[str] = Field(default=None, description="Preferred start or completion dates. This is optional.")
    contact_preference: Optional[str] = Field(default=None, description="How the homeowner prefers to be contacted (e.g., 'email', 'phone'). Default to 'email' if not specified.")
    additional_notes: Optional[str] = Field(default=None, alias="homeowner_provided_additional_notes", description="Any other relevant information or special instructions from the homeowner.")

# This class defines the structure the LLM is expected to output, as per SYSTEM_PROMPT.
class HomeownerAgentOutput(BidCardBase):
    """Defines the structured output the LLM should produce, including bid card fields and its thought process."""
    thought: Optional[str] = Field(default=None, description="The AI's reasoning for its response or next question.")
    response_to_user: Optional[str] = Field(default=None, description="The actual conversational response or question to pose to the user.") # ADDED

class BidCardCreate(BidCardBase):
    user_id: str

SYSTEM_PROMPT = (
    "You are HomeownerAgent, a conversational AI assistant for homeowners. "
    "Your primary goal is to dynamically collect all necessary details from the homeowner to create a comprehensive project listing. "
    "You will be provided with the user's input and the current state of the project details collected so far (current_bid_card_state). "
    "Your task is to analyze the input, update any relevant bid card fields based on the new information, and then formulate your next question or statement to the user. "
    "If a field in current_bid_card_state is already filled, only update it if the user explicitly provides new information for that specific field. "
    "If the user provides information that could update multiple fields, update all of them."
    "Prioritize clarifying essential details like 'description', 'scope_summary', 'category', 'address', 'city', 'state', 'zip_code', and 'urgency'."
    "If the user seems to be finishing or has provided substantial details, confirm if they have more to add before finalizing."
    "When you have enough information for a complete bid card (especially title, description, category, location), set your 'thought' to indicate readiness to finalize."
    "If the user's input is unclear, ask clarifying questions. "
    "If the user asks a question, answer it concisely before returning to your goal of collecting information."
    "Always maintain a friendly, helpful, and professional tone. "
    "Your output MUST be a JSON object that strictly matches the HomeownerAgentOutput Pydantic model, including all BidCardBase fields. "
    "The 'thought' field should contain your step-by-step reasoning and reflections on the conversation and bid card status. "
    "The 'response_to_user' field MUST contain the exact text you want to say to the homeowner (e.g., your next question, a confirmation, or a summary). "
    "Example: If asking for the address, 'response_to_user' would be 'What is the full address for the project?'."
    "If all information is gathered, in your 'thought', explain that you are ready to finalize, and set 'response_to_user' to summarize the bid card and ask for confirmation."
)

# Examples for the LLM, showing input and expected JSON output structure
# The output dictionary must match the fields of HomeownerAgentOutput (BidCardBase fields + 'thought')
BID_CARD_EXAMPLES = [
    (
        {"user_input": "I need to fix a leaky faucet in my kitchen.", "current_bid_card_state": {}},
        {
            "thought": "User described a plumbing issue. Identified category and description. Need more details about the faucet.",
            "title": "Kitchen Faucet Repair",
            "category": "Plumbing",
            "description": "Fix a leaky faucet in kitchen.",
            "scope_summary": None, # Explicitly None if not inferable
            "address": None,
            "city": None,
            "state": None,
            "zip_code": None,
            "urgency": "Flexible", # Default if not specified
            "budget_range": None,
            "timeline": None,
            "contact_preference": "email", # Default if not specified
            "additional_notes": None,
            "response_to_user": "What is the full address for the project?" # ADDED
        }
    ),
    (
        {"user_input": "The house is at 123 Main St, Anytown, CA 90210. It's urgent!", "current_bid_card_state": {"title": "Kitchen Faucet Repair", "category": "Plumbing", "description": "Fix a leaky faucet in kitchen."}},
        {
            "thought": "User provided address and urgency. Updated these fields.",
            "title": "Kitchen Faucet Repair",
            "category": "Plumbing",
            "description": "Fix a leaky faucet in kitchen.",
            "address": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "90210",
            "urgency": "ASAP",
            "scope_summary": None, 
            "budget_range": None,
            "timeline": None,
            "contact_preference": "email",
            "additional_notes": None,
            "response_to_user": "Can you please provide more details about the faucet?" # ADDED
        }
    )
]

# from google.adk.tools.tool_utils import make_tool_protos_from_tools # Removed, not available/needed
from google.generativeai.types import ContentDict, GenerateContentResponse, PartDict,Tool as GenAITool, HarmCategory, HarmBlockThreshold 
from google.generativeai.types import GenerationConfig

class HomeownerAgent(LLMAgent): # <--- UPDATED TO LLMAgent (uppercase)
    """Concrete ADK agent with multimodal intake and memory."""
    _logger: logging.Logger = PrivateAttr() # HomeownerAgent's own logger
    _mem0_client: Optional[MemoryClient] = PrivateAttr(default=None)
    _homeowner_memory_instance: Optional[PersistentMemory] = PrivateAttr(default=None)
    _supabase_tool_objects: Optional[List[Any]] = PrivateAttr(default_factory=list) # Renamed to avoid clash with LlmAgent.tools
    _vision_tool_object: Optional[Any] = PrivateAttr(default=None) # Renamed

    # Attributes for GenAI model and configuration, specific to HomeownerAgent
    model_name_str: str # To store the model name string like 'gemini-1.5-flash'
    genai_model_instance: Optional[GenerativeModel] = PrivateAttr(default=None) # For the actual GenerativeModel instance
    agent_instruction: Optional[str] = None
    agent_output_key: Optional[str] = None
    agent_tools_list: List[GenAITool] = PrivateAttr(default_factory=list) # Tools for GenAI model
    agent_generation_config: Optional[GenerationConfig] = None
    # MODIFIED: Changed type hint to use google.generativeai.protos.ToolConfig
    agent_tool_config: Optional[google.generativeai.protos.ToolConfig] = PrivateAttr(default=None) 

    def __init__(
        self,
        model_name: str, # This is the string name like 'gemini-1.5-flash'
        memory: Optional[PersistentMemory] = None,
        mem0_api_key: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_anon_key: Optional[str] = None, 
        supabase_service_role_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        print(f"DEBUG: LLMAgent is being loaded by Python from: {inspect.getfile(LLMAgent)}") # <--- UPDATED to LLMAgent

        # HomeownerAgent specific attributes that need to be initialized early
        self.model_name_str = model_name
        self.agent_instruction = SYSTEM_PROMPT
        self.agent_output_key = "homeowner_agent_output"
        self.agent_tools_list = [] # Initialize early, will be populated below
        self.agent_generation_config = GenerationConfig()
        self.agent_tool_config = None # Initialize early

        # Prepare tool objects for HomeownerAgent's specific use (GenAI tools)
        gen_ai_tools_for_model: List[GenAITool] = []
        self._supabase_tool_objects = [] 
        self._vision_tool_object = None

        if openai_api_key: # Only initialize if key is provided
            try:
                self._vision_tool_object = openai_vision_tool(api_key=openai_api_key)
            except NotImplementedError as e:
                logger.warning(f"OpenAI Vision Tool could not be initialized (NotImplemented or placeholder): {e}")
                self._vision_tool_object = None # Explicitly set to None on error
            except Exception as e:
                logger.error(f"An unexpected error occurred during OpenAI Vision Tool initialization: {e}", exc_info=True)
                self._vision_tool_object = None # Explicitly set to None on error
        else:
            logger.info("OpenAI API key not provided. Vision tool will not be initialized.")
            self._vision_tool_object = None

        if supabase_url and supabase_service_role_key:
            self._supabase_tool_objects = get_supabase_tools()
            if self._supabase_tool_objects:
                gen_ai_tools_for_model.extend(self._supabase_tool_objects)
        if self._vision_tool_object:
            gen_ai_tools_for_model.append(self._vision_tool_object)
        
        self.agent_tools_list = gen_ai_tools_for_model
        if self.agent_tools_list:
            # MODIFIED: Prefixed ToolConfig and FunctionCallingConfig with google.generativeai.protos
            self.agent_tool_config = google.generativeai.protos.ToolConfig(function_calling_config=google.generativeai.protos.FunctionCallingConfig(mode=google.generativeai.protos.FunctionCallingConfig.Mode.AUTO))

        # Call super().__init__
        super().__init__(
            name="HomeownerAgent",
            tools=None, 
            system_prompt=self.agent_instruction, # Use the one set on self
            memory=memory
        )

        # Initialize HomeownerAgent's own logger now that self.name is set by super()
        self._logger = logging.getLogger(self.name)
        self._logger.info(f"HomeownerAgent logger initialized for '{self.name}'.")

        # Initialize self.genai_model_instance (Main initialization after logger and superclass are set up)
        if self.model_name_str:
            try:
                self.genai_model_instance = GenerativeModel(
                    model_name=self.model_name_str,
                    generation_config=self.agent_generation_config,
                    tools=self.agent_tools_list,  # CORRECTED: Use self.agent_tools_list
                    tool_config=self.agent_tool_config, # CORRECTED: Use self.agent_tool_config
                    system_instruction=self.agent_instruction,
                )
                self._logger.info(f"Successfully initialized GenerativeModel '{self.model_name_str}' for HomeownerAgent with tools: {[tool.function_declarations[0].name for tool in self.agent_tools_list] if self.agent_tools_list and self.agent_tools_list[0].function_declarations else 'No tools'}.")
            except Exception as e:
                self._logger.error(f"Failed to initialize GenerativeModel '{self.model_name_str}' for HomeownerAgent: {e}", exc_info=True)
                self.genai_model_instance = None
        else:
            self._logger.error("Cannot initialize GenerativeModel for HomeownerAgent as model_name_str is not set.")
            self.genai_model_instance = None
        
        # Initialize memory systems
        self._homeowner_memory_instance = self.memory # Use the memory instance from LlmAgent
        self._mem0_client: Optional[MemoryClient] = None 
        if mem0_api_key:
            try:
                self._mem0_client = MemoryClient(api_key=mem0_api_key) 
                self._logger.info("Mem0ai client initialized.") 
            except Exception as e:
                self._logger.error(f"Failed to initialize Mem0ai client: {e}")
                self._mem0_client = None 

        self._logger.info(f"HomeownerAgent fully initialized. GenAI Model: {self.model_name_str}. GenAI Tools: {len(self.agent_tools_list)}")

    async def process_input(
        self,
        input_data: HomeownerAgentInput,
        user_id: str, 
        session_id: Optional[str] = None,
    ) -> HomeownerAgentOutput:
        self._logger.info(f"Processing input for user_id: {user_id}, session_id: {session_id}") 
        self._logger.debug(f"Raw input_data: {input_data}") 

        session_id = session_id or str(uuid.uuid4())
        messages: List[ContentDict] = []
        homeowner_agent_output: Optional[HomeownerAgentOutput] = None # Initialize
        llm_response_content: Union[str, ContentDict, None] = None # Initialize

        try:
            # 1. Load and prepare conversation history from PersistentMemory
            if self._homeowner_memory_instance:
                self._logger.info(f"Loading conversation history for session_id: {session_id}") 
                conversation_history_tuples = await self._homeowner_memory_instance.get_history(session_id=session_id)
                for speaker, text in conversation_history_tuples:
                    role = "user" if speaker == "user" else "model"
                    messages.append(ContentDict(role=role, parts=[PartDict(text=text)]))
                self._logger.debug(f"Loaded conversation history (first 2 messages if >2): {messages[:2]}") 
            else:
                self._logger.warning("PersistentMemory (self._homeowner_memory_instance) not initialized. Proceeding without conversation history.") 

            # 2. Augment context with Mem0 (if available and enabled)
            mem0_context = ""
            if self._mem0_client:
                try:
                    self._logger.info("Searching relevant memories in Mem0.") 
                    mem0_response = self._mem0_client.search(
                        query=input_data.user_input,
                        user_id=user_id,
                        limit=3
                    )
                    if mem0_response and mem0_response.get('memories'):
                        mem0_context = "\nRelevant past information (from long-term memory):\n" + "\n".join(
                            [f"- {mem['text']}" for mem in mem0_response['memories']]
                        )
                    self._logger.debug(f"Mem0 context: {mem0_context}") 
                except Exception as e_mem0:
                    self._logger.error(f"Error searching Mem0: {e_mem0}") 

            # 3. Construct the current user message, potentially including image URL
            current_message_parts: List[PartDict] = [PartDict(text=input_data.user_input)]
            if input_data.image_url:
                # Basic image handling for now. If vision tool is available, it might be used.
                # For direct inclusion, model needs to support image URLs in parts.
                # This part might need adjustment based on how the vision tool/model expects image input.
                current_message_parts.append(PartDict(inline_data=PartDict(mime_type="image/jpeg", data=input_data.image_url))) # Placeholder
                self._logger.info(f"Image URL included in message parts: {input_data.image_url}")

            user_query_for_prompt = f"User input: {input_data.user_input}{mem0_context}"
            if input_data.image_url:
                user_query_for_prompt += f"\nImage context: An image has been provided (see attached image)."
            if input_data.audio_url:
                 user_query_for_prompt += f"\nAudio context: An audio recording has been provided."

            current_bid_card_for_prompt = f"Current Bid Card State: {json.dumps(input_data.current_bid_card_state) if input_data.current_bid_card_state else 'empty'}"

            # Append the specially formatted user query and bid card state
            formatted_user_input_text = f"{user_query_for_prompt}\n\n{current_bid_card_for_prompt}"
            
            # Ensure current_message_parts is correctly formed for the model
            # If the model primarily expects text with structured prompts, adjust `current_message_parts`
            # For this iteration, we'll assume the SYSTEM_PROMPT guides the model to use the combined text.
            final_messages_for_llm: List[ContentDict] = messages + [
                ContentDict(role="user", parts=[PartDict(text=formatted_user_input_text)])
            ]
            if input_data.image_url and self._vision_tool_object:
                # If vision tool is active, it might be implicitly used by the LlmAgent
                # or need explicit formatting here. For now, assume LlmAgent handles it if tools are passed.
                # The current_message_parts above already has a placeholder for image data.
                # Let's refine how image data is passed if using specific vision tool patterns.
                # For Google's model, image data might be part of the `parts` list directly.
                # For now, we'll stick to the text prompt and rely on the agent's tool usage if vision tool is present.
                # Add image part if vision tool is not automatically handling it via self.tools
                # Example for google.generativeai, if not using a 'tool' but direct multimodal input:
                # final_messages_for_llm[-1]['parts'].append(PartDict(inline_data=PartDict(mime_type="image/jpeg", data=...))) # Needs actual image data bytes
                pass # Current approach relies on text description or implicit tool use

            # Pass the current bid card state and user input to the prompt context for the LLM call
            # These attributes are used by _call_model_with_tools_and_history to format the final prompt if needed
            # or could be directly part of `final_messages_for_llm` as done above.
            # self.current_bid_card_state_for_prompt = current_bid_card_for_prompt # No longer seems necessary with direct inclusion
            # self.user_input_for_prompt = user_query_for_prompt # No longer seems necessary
            
            self._logger.info("Calling LLM with tools and history...")
            tool_names_for_log = []
            if self.agent_tools_list:
                for tool_instance in self.agent_tools_list:
                    if hasattr(tool_instance, 'function_declarations') and \
                       getattr(tool_instance, 'function_declarations') and \
                       isinstance(getattr(tool_instance, 'function_declarations'), list) and \
                       len(getattr(tool_instance, 'function_declarations')) > 0 and \
                       hasattr(getattr(tool_instance, 'function_declarations')[0], 'name'):
                        tool_names_for_log.append(tool_instance.function_declarations[0].name)
                    elif hasattr(tool_instance, 'name'): # Fallback for other tool types
                        tool_names_for_log.append(f"{tool_instance.name} (type: {type(tool_instance).__name__}, missing/invalid function_declarations)")
                    else:
                        tool_names_for_log.append(f"Unknown_Tool (type: {type(tool_instance).__name__})")
            self._logger.debug(f"Tools being passed to LLM (from self.agent_tools_list): {tool_names_for_log if tool_names_for_log else 'No tools'}")
            self._logger.debug(f"Tool config being passed: {self.agent_tool_config}")

            llm_response_content, tool_parts, homeowner_agent_output = await self._call_model_with_tools_and_history(
                messages=final_messages_for_llm, 
                tools=self.agent_tools_list, # Pass the GenAI specific tools
                tool_config=self.agent_tool_config # Pass the GenAI specific tool_config
            )
            self._logger.info("LLM call successful.")
            self._logger.debug(f"LLM raw response content: {llm_response_content}")
            self._logger.debug(f"LLM tool parts: {tool_parts}")
            self._logger.debug(f"Parsed HomeownerAgentOutput: {homeowner_agent_output}")

            # Save interaction to PersistentMemory
            if self._homeowner_memory_instance:
                self._logger.info(f"Saving user query and LLM response to session: {session_id} in PersistentMemory.")
                # Save user query
                await self._homeowner_memory_instance.add_entry_to_session(
                    session_id=session_id,
                    user_query=input_data.user_input
                )
                # Save LLM response_to_user
                if homeowner_agent_output and homeowner_agent_output.response_to_user:
                    await self._homeowner_memory_instance.add_entry_to_session(
                        session_id=session_id,
                        llm_response=homeowner_agent_output.response_to_user
                    )
                else:
                    self._logger.warning("LLM response_to_user was empty, not saving to PersistentMemory session.")
                
                # Save memory to database if it's dirty (has unsaved changes)
                if self._homeowner_memory_instance._is_dirty: # Consider a public method like 'is_dirty()' and 'commit()' in PersistentMemory
                    await self._homeowner_memory_instance.save()
                    self._logger.info(f"Persistent memory saved for user {user_id}, session {session_id}.")
            else:
                self._logger.warning("PersistentMemory instance not available, skipping save to PersistentMemory.")

            # Save interaction to Mem0 (if enabled and response is text)
            if self._mem0_client and homeowner_agent_output and homeowner_agent_output.response_to_user:
                self._logger.info(f"Saving interaction to Mem0 for user {user_id}, session {session_id}.")
                try:
                    mem0_response = self._mem0_client.add(
                        user_id=user_id,
                        text=homeowner_agent_output.response_to_user,
                        tags=["homeowner_agent_response"]
                    )
                    if mem0_response and mem0_response.get('memory'):
                        self._logger.info(f"Mem0 memory saved: {mem0_response['memory']['id']}")
                    else:
                        self._logger.warning("Mem0 memory not saved (response did not contain 'memory' key).")
                except Exception as e:
                    self._logger.error(f"Error saving interaction to Mem0: {e}")

            if not homeowner_agent_output:
                self._logger.error("homeowner_agent_output is None after LLM call, this should not happen in a successful flow.")
                # Fallback to a generic error, though _call_model_with_tools_and_history should raise or return valid output
                current_fields = input_data.current_bid_card_state or {}
                return HomeownerAgentOutput(
                    thought="Critical error: LLM call completed but no structured output was derived.",
                    response_to_user="I encountered an internal problem processing your request. Please try again.",
                    **current_fields,
                )

            return homeowner_agent_output

        except Exception as e:
            self._logger.error(f"Error in HomeownerAgent.process_input: {e}", exc_info=True) 
            current_fields = input_data.current_bid_card_state or {}
            # Ensure all fields of BidCardBase are handled, defaulting to None if not in current_fields
            bid_card_fields = {field_name: current_fields.get(field_name) for field_name in BidCardBase.model_fields.keys()}

            return HomeownerAgentOutput(
                thought=f"An error occurred during processing: {str(e)}",
                response_to_user=f"I'm sorry, I encountered an issue: {str(e)}. Let's try that again. What were you saying?",
                **bid_card_fields,
            )

    async def _call_model_with_tools_and_history(
        self,
        messages: List[ContentDict],
        tools: Optional[List[GenAITool]] = None, # Tools passed to this method take precedence
        # MODIFIED: Changed type hint to use google.generativeai.protos.ToolConfig
        tool_config: Optional[google.generativeai.protos.ToolConfig] = None,
        generation_config_override: Optional[GenerationConfig] = None, # Override from method param takes precedence
    ) -> Tuple[Union[str, ContentDict, None], List[ContentDict], HomeownerAgentOutput]:
        self._logger.info(f"Calling LLM with tools and history. Messages: {len(messages)}") 
        self._logger.debug(f"Tool config: {tool_config}") 

        if not self.genai_model_instance:
            self._logger.error("GenerativeModel (self.genai_model_instance) is not initialized.")
            # Return a default error output or raise an exception
            error_output = HomeownerAgentOutput(
                thought="Error: Model not initialized.",
                response_to_user="Sorry, I'm having trouble connecting to my core functions. Please try again later."
            )
            return None, [], error_output

        # Determine the generation config: use override if provided, else agent's default
        final_generation_config = generation_config_override if generation_config_override else self.agent_generation_config

        # Determine tools to use: use tools passed to method if provided, else agent's default list
        final_tools = tools if tools is not None else self.agent_tools_list

        raw_response_content, raw_tool_parts = await self.genai_model_instance.generate_content_async(
            messages, 
            tools=final_tools, # Use the tools determined above
            tool_config=tool_config, # Pass through the tool_config from params
            generation_config=final_generation_config # Use the generation config determined above
        )

        self._logger.debug(f"Raw LLM response content type: {type(raw_response_content)}") 
        self._logger.debug(f"Raw LLM response content: {raw_response_content}") 
        self._logger.debug(f"Raw LLM tool parts: {raw_tool_parts}") 

        # Initialize default output structure
        output = HomeownerAgentOutput(
            thought="Default thought if LLM does not provide one.",
            response_to_user="Default response if LLM does not provide one.",
        )

        # Attempt to parse the structured output from the LLM response
        if isinstance(raw_response_content, str):
            # If the response is a string, try to parse it as JSON
            # This might happen if the model doesn't strictly adhere to function calling for the structured output
            try:
                # The string might contain the JSON object we expect for HomeownerAgentOutput
                # Or it might be just the 'thought' or 'summary'
                self._logger.debug(f"LLM response is a string, attempting to parse as JSON: {raw_response_content[:200]}...") 
                parsed_json = json.loads(raw_response_content)
                if isinstance(parsed_json, dict):
                    # Try to load into HomeownerAgentOutput, allowing missing fields to use defaults
                    # This assumes the model's string output *is* the HomeownerAgentOutput structure
                    output = HomeownerAgentOutput(**parsed_json) 
                else:
                    # If it's not a dict, maybe it's just the thought or summary
                    output.thought = raw_response_content # Default to assigning to thought
                    output.summary = raw_response_content # Or summary
            except json.JSONDecodeError:
                self._logger.warning(f"LLM response string was not valid JSON. Treating as plain text thought/summary.") 
                # If parsing fails, treat the whole string as the 'thought' or 'summary'
                output.thought = raw_response_content
                output.summary = raw_response_content # Or a more nuanced assignment based on content
        elif isinstance(raw_response_content, ContentDict):
            # This is the expected path if the model correctly returns a ContentDict (e.g. via Gemini's structured output)
            # We need to extract the HomeownerAgentOutput from the ContentDict
            # The LlmAgent's _call_model typically returns the primary text part or a structured dict
            # if a Pydantic model was used for output_data_model in the ADKAgent's call.
            # Here, we expect the HomeownerAgentOutput to be embedded within the response parts.

            # Look for the output_key in the response content parts if it's structured that way
            # This might need adjustment based on how LlmAgent actually formats the output
            # when an output_data_model is *not* directly used in the call to the model's generate_content.
            # Our SYSTEM_PROMPT asks for JSON matching HomeownerAgentOutput.

            extracted_text = ""
            if raw_response_content.get('parts'):
                for part_dict in raw_response_content['parts']:
                    if 'text' in part_dict and part_dict['text']:
                        extracted_text += part_dict['text'] + " " # Concatenate text parts
            
            extracted_text = extracted_text.strip()
            self._logger.debug(f"Extracted text from ContentDict parts for JSON parsing: {extracted_text[:200]}...") 

            if extracted_text:
                try:
                    # Attempt to parse the concatenated text as JSON matching HomeownerAgentOutput
                    parsed_json = json.loads(extracted_text)
                    if isinstance(parsed_json, dict):
                        output = HomeownerAgentOutput(**parsed_json)
                    else:
                        self._logger.warning("Parsed JSON from ContentDict parts was not a dictionary.") 
                        output.thought = extracted_text # Fallback
                        output.summary = extracted_text # Fallback
                except json.JSONDecodeError as e:
                    self._logger.error(f"Failed to decode JSON from ContentDict text: {e}. Text was: {extracted_text[:200]}...") 
                    # If JSON decoding fails, use the extracted text as thought/summary
                    output.thought = f"Could not parse LLM response as structured JSON. Raw text: {extracted_text}"
                    output.summary = extracted_text
            else:
                self._logger.warning("No text parts found in ContentDict to parse for HomeownerAgentOutput.") 
                output.thought = "LLM returned a ContentDict but no parsable text parts were found."

        # Handle tool calls if any were made by the LLM
        if raw_tool_parts:
            self._logger.info(f"LLM returned tool calls: {len(raw_tool_parts)} part(s).") 
            # For now, we don't have a loop to execute tools and re-prompt. 
            # We'll just log them and assume the primary response contains the bid card info.
            # Future: Implement tool execution loop if agent needs to autonomously use tools.
            tool_call_descriptions = []
            for tool_part in raw_tool_parts:
                if 'function_call' in tool_part:
                    fc = tool_part['function_call']
                    tool_call_descriptions.append(f"Tool call: {fc.get('name')}, Args: {fc.get('args')}")
            
            if tool_call_descriptions:
                # Prepend tool call info to the thought or summary if not already structured
                # This is a simple way to make tool usage visible if not explicitly parsed into output
                tool_info_str = "\nLLM suggested tool calls: " + "\n".join(tool_call_descriptions)
                if not output.thought or output.thought == "Default thought if LLM does not provide one.":
                    output.thought = tool_info_str.strip()
                else:
                    output.thought += tool_info_str
                self._logger.info(tool_info_str) 

        # Final check on the output before returning
        if not output.summary and output.thought and output.thought != "Default thought if LLM does not provide one.":
            # If summary is empty but thought is not, use thought as summary as a fallback
            output.summary = output.thought
        
        self._logger.debug(f"Parsed HomeownerAgentOutput: {output}") 
        return raw_response_content, raw_tool_parts, output