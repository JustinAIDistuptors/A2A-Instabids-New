"""
OpenAI Vision Tool for analyzing project images.
"""
from typing import Dict, Any, List, Optional
import base64
import logging
import os
import time
import openai

logger = logging.getLogger(__name__)

# Configure the OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.warning("OPENAI_API_KEY not set in environment variables")

async def analyze_image(base64_image: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze an image using OpenAI's Vision API.
    
    Args:
        base64_image: Base64-encoded image data
        prompt: Optional specific instructions for image analysis
        
    Returns:
        Analysis results
    """
    try:
        default_prompt = "Analyze this construction or home project image. What work needs to be done?"
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or default_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        return {
            "analysis": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens
        }
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        return {
            "error": str(e),
            "analysis": "Failed to analyze image"
        }

async def extract_text_from_image(base64_image: str) -> str:
    """
    Extract text from an image using OCR via OpenAI's Vision API.
    
    Args:
        base64_image: Base64-encoded image data
        
    Returns:
        Extracted text
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image, preserving layout if possible."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        return ""

async def classify_project_from_images(
    images: List[str], 
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify the type of project based on images and optional description.
    
    Args:
        images: List of base64-encoded image data
        description: Optional project description
        
    Returns:
        Classification results
    """
    try:
        # Build messages with all images
        content = [{"type": "text", "text": "Classify this home improvement project. What category is it (renovation, repair, maintenance, installation, construction)?"}]
        
        if description:
            content.append({"type": "text", "text": f"Project description: {description}"})
            
        # Add up to 4 images (API limit)
        for i, img in enumerate(images[:4]):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img}"
                }
            })
            
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=150
        )
        
        analysis = response.choices[0].message.content
        
        # Simple parsing of category from response
        categories = ["renovation", "repair", "maintenance", "installation", "construction"]
        detected = next((c for c in categories if c.lower() in analysis.lower()), "other")
        
        return {
            "category": detected,
            "confidence": 0.8,  # Mock confidence score
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Error classifying project from images: {str(e)}")
        return {
            "category": "other",
            "confidence": 0.5,
            "error": str(e)
        }

# Export as a tool for agent use
openai_vision_tool = {
    "name": "analyze_image",
    "description": "Analyze a project image to identify issues, work needed, or project classification",
    "parameters": {
        "base64_image": "Base64-encoded image data",
        "prompt": "Optional specific instructions for image analysis"
    },
    "function": analyze_image
}