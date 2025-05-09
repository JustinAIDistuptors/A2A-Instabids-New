# src/instabids/tools/gemini_vision_tool.py
"""Gemini 1.5 Vision wrapper — returns (labels, embedding, confidence)."""
from __future__ import annotations
import base64, os
import logging # Added for logging
from typing import Dict, List, Any

from google.generativeai import GenerativeModel, configure

logger = logging.getLogger(__name__) # Setup logger

_API_KEY = os.getenv("GEMINI_API_KEY")  # set in CI / Cloud Run
# Add a check for the API key and log a warning if not found
if not _API_KEY:
    logger.warning("GEMINI_API_KEY environment variable not set. Vision tool will not function.")
    # Consider raising an error or providing a default stub if appropriate
else:
    try:
        configure(api_key=_API_KEY)
    except Exception as e:
        logger.error(f"Failed to configure Google Generative AI: {e}", exc_info=True)
        _API_KEY = None # Treat as not configured if error occurs

# Ensure model initialization happens only if API key is configured
_model = None
if _API_KEY:
    try:
        # Using a specific, available model version for stability. Adjust if needed.
        # The sprint mentions "gemini-1.5-vision-preview", but we might use a more stable one if available.
        # Let's stick to the sprint plan for now, using flash as a likely candidate.
        _model = GenerativeModel("models/gemini-1.5-flash") # Changed to 1.5 flash - generally available
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model: {e}", exc_info=True)
        _model = None # Ensure model is None if init fails

def analyse(image_path: str) -> Dict[str, Any] | None:
    """
    Analyzes an image using Gemini 1.5 Vision.

    Args:
        image_path: Path to the image file.

    Returns:
        A dictionary containing 'labels', 'embedding', and 'confidence',
        or None if the API key is not set, the model failed to initialize,
        or the API call fails.
    """
    if not _model:
        logger.error("Gemini model not initialized. Cannot analyze image.")
        return None # Return None or raise error if model is unavailable

    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        # Determine MIME type based on file extension (simple approach)
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            # Add other supported types if needed
        }.get(ext, "image/jpeg") # Default to JPEG

        prompt = "Analyze this image. Extract the main subject, scene context, and up to 5 relevant descriptive labels. Provide an embedding vector and confidence score."

        # Define the function declaration for the tool
        extract_tool = {
            "function_declarations": [{
                "name": "extract_image_metadata",
                "description": "Extracts labels, embedding, and confidence score from an image analysis.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Descriptive labels for the image content."},
                        "embedding": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Vector embedding representing the image."},
                        "confidence": {"type": "NUMBER", "description": "Confidence score of the analysis (0.0 to 1.0)."}
                    },
                    "required": ["labels", "embedding", "confidence"]
                }
            }]
        }

        # Prepare the image part
        image_part = {"mime_type": mime_type, "data": b64}

        # Generate content with the tool
        response = _model.generate_content(
            [prompt, image_part],
            generation_config={"max_output_tokens": 200}, # Adjusted tokens if needed
            tools=extract_tool,
            tool_config={"function_calling_config": "AUTO"} # Specify auto function calling
        )

        # Check for function call in response
        if response.candidates and response.candidates[0].content.parts:
             for part in response.candidates[0].content.parts:
                 if part.function_call:
                     # Ensure args is a dict before returning
                     args = part.function_call.args
                     if isinstance(args, dict):
                         # Validate required keys are present (optional but good practice)
                         if all(k in args for k in ["labels", "embedding", "confidence"]):
                             # Add rudimentary type check/conversion if necessary
                             if not isinstance(args.get('labels'), list):
                                 args['labels'] = []
                             if not isinstance(args.get('embedding'), list):
                                 args['embedding'] = [] # Or handle error
                             if not isinstance(args.get('confidence'), (int, float)):
                                 args['confidence'] = 0.0 # Or handle error
                             return args
                         else:
                             logger.warning(f"Gemini response missing required keys in function call args: {args}")
                             return None
                     else:
                         logger.warning(f"Unexpected function call args format: {type(args)}")
                         return None

        # Handle cases where no function call was returned or response format is unexpected
        # Check if response has text attribute before accessing it
        response_text = "No text content available" # Default message
        try:
            if hasattr(response, 'text'):
                response_text = response.text
        except Exception as text_err:
            logger.warning(f"Could not access response text: {text_err}")

        logger.warning(f"Gemini analysis did not return the expected function call. Response snippet: {response_text[:500]}") # Log part of text response for debugging
        return None

    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        return None
    except Exception as e:
        logger.error(f"Error during Gemini vision analysis for {image_path}: {e}", exc_info=True)
        return None # Return None on error