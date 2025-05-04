"""
Enhanced vision analysis tool using GPT-4o Vision.

This module provides advanced image analysis capabilities using OpenAI's GPT-4o Vision model.
It extracts structured information from images including labels and dimensions.
"""
from openai import OpenAI
import os
import json
import logging
from typing import Dict, Any, Tuple, List, Optional
import base64
from pathlib import Path

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)

async def analyse(path: str) -> Dict[str, Any]:
    """
    Return {'labels': [...], 'dimensions': (w,h)}.
    
    Args:
        path: Path to the image file
        
    Returns:
        Dictionary containing labels and dimensions
    
    Raises:
        FileNotFoundError: If the image file doesn't exist
        Exception: For API errors or other issues
    """
    try:
        # Ensure the file exists
        if not Path(path).exists():
            raise FileNotFoundError(f"Image file not found: {path}")
            
        # Read the image file
        with open(path, "rb") as f:
            image_data = f.read()
            
            # Call the OpenAI API with vision capabilities
            resp = await client.chat.completions.create(
                model="gpt-4o-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze this image and identify key elements."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"}}
                        ]
                    }
                ],
                tools=[{"type": "classification"}],
            )
            
            # Extract the tool call results
            labels = resp.choices[0].message.tool_calls[0].function.arguments
            labels = json.loads(labels)["labels"]
            
            # Get image dimensions from the response usage info
            dimensions = resp.usage.get("image_size", (0, 0))
            
            # Return structured data
            return {
                "labels": labels,
                "dimensions": dimensions
            }
        
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        raise
    except Exception as e:
        logger.error(f"Vision API error: {e}")
        raise

async def analyze_base64(b64_image: str) -> Dict[str, Any]:
    """
    Analyze an image from base64 data and return structured information.
    
    Args:
        b64_image: Base64-encoded image data
        
    Returns:
        Dictionary containing labels and dimensions
    
    Raises:
        Exception: For API errors or other issues
    """
    try:
        # Call the OpenAI API with vision capabilities
        resp = await client.chat.completions.create(
            model="gpt-4o-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this image and identify key elements."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }
            ],
            tools=[{"type": "classification"}],
        )
        
        # Extract the tool call results
        labels = resp.choices[0].message.tool_calls[0].function.arguments
        labels = json.loads(labels)["labels"]
        
        # Get image dimensions from the response usage info
        dimensions = resp.usage.get("image_size", (0, 0))
        
        # Return structured data
        return {
            "labels": labels,
            "dimensions": dimensions
        }
        
    except Exception as e:
        logger.error(f"Vision API error: {e}")
        raise