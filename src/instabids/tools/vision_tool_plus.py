'''
Enhanced vision tool for image analysis using OpenAI's GPT-4o Vision API.

This module provides functions for analyzing images and extracting structured
information such as labels, object detection, and dimensions.
'''
import os
import json
import base64
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from openai import AsyncOpenAI

# Initialize the OpenAI client
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def analyse(image_path: str) -> Dict[str, Any]:
    '''
    Analyze an image using OpenAI's GPT-4o Vision API.
    
    Args:
        image_path: Path to the image file to analyze
        
    Returns:
        Dict containing analysis results with labels and dimensions
        
    Raises:
        FileNotFoundError: If the image file does not exist
        Exception: If the API call fails
    '''
    # Validate file exists
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Read and encode the image
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    try:
        # Call the OpenAI API with the vision model
        response = await client.chat.completions.create(
            model="gpt-4o-vision-preview",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert image analyzer for construction and home repair projects.
                    Analyze the image and extract relevant labels and information.
                    Focus on identifying construction elements, damage, materials, and architectural features."""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this image and identify key elements related to construction or home repair. Return the results as structured data."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "extract_image_data",
                        "description": "Extract structured data from the image analysis",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "labels": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "List of labels identifying elements in the image"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Brief description of what's in the image"
                                },
                                "damage_assessment": {
                                    "type": "string",
                                    "description": "Assessment of any visible damage"
                                }
                            },
                            "required": ["labels"]
                        }
                    }
                }
            ],
            tool_choice={"type": "function", "function": {"name": "extract_image_data"}},
            max_tokens=1000
        )
        
        # Extract the structured data from the response
        tool_call = response.choices[0].message.tool_calls[0]
        result = json.loads(tool_call.function.arguments)
        
        # Add image dimensions if available
        dimensions = getattr(response.usage, "image_size", (0, 0))
        
        return {
            "labels": result.get("labels", []),
            "description": result.get("description", ""),
            "damage_assessment": result.get("damage_assessment", ""),
            "dimensions": dimensions
        }
        
    except Exception as e:
        # Log the error and re-raise
        print(f"Error analyzing image: {e}")
        raise

async def batch_analyse(image_paths: List[str]) -> List[Dict[str, Any]]:
    '''
    Analyze multiple images in batch.
    
    Args:
        image_paths: List of paths to image files
        
    Returns:
        List of dictionaries containing analysis results
    '''
    results = []
    for path in image_paths:
        try:
            result = await analyse(path)
            results.append({
                "path": path,
                "analysis": result,
                "success": True
            })
        except Exception as e:
            results.append({
                "path": path,
                "error": str(e),
                "success": False
            })
    
    return results

async def validate_image_for_bid_card(image_path: str) -> Dict[str, Any]:
    '''
    Validate an image for use in a bid card.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dict containing validation results
    '''
    analysis = await analyse(image_path)
    
    # Check if the image is suitable for a bid card
    is_valid = len(analysis.get("labels", [])) > 0
    
    return {
        "is_valid": is_valid,
        "analysis": analysis,
        "recommendation": "Image is suitable for bid card" if is_valid else "Image may not be relevant to construction or repair"
    }