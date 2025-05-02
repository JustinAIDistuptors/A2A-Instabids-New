"""
OpenAI Vision Tool for image analysis and processing.
"""
from typing import Dict, Any, List, Optional, Union
import os
import logging
import base64
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

class OpenAIVisionTool:
    """
    Tool for analyzing images using OpenAI's vision capabilities.
    Provides methods for extracting tags, descriptions, and other information from images.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI Vision Tool.
        
        Args:
            api_key: Optional API key for OpenAI. If not provided, will attempt to use
                    the OPENAI_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Vision analysis will be limited.")
    
    def analyze_image(self, image_data: Union[str, bytes, Path]) -> Dict[str, Any]:
        """
        Analyze an image and extract relevant information.
        
        Args:
            image_data: The image to analyze. Can be a file path, URL, or raw bytes.
            
        Returns:
            Dictionary containing analysis results, including tags and descriptions.
        """
        try:
            # For testing/CI environments, return mock data if no API key
            if not self.api_key:
                logger.warning("Using mock vision analysis (no API key available)")
                return self._mock_analysis()
            
            # Convert image data to appropriate format for API
            encoded_image = self._prepare_image(image_data)
            
            # Call OpenAI API (implementation would go here)
            # For now, return a mock response
            return self._mock_analysis()
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {"error": str(e), "tags": []}
    
    def extract_tags(self, image_data: Union[str, bytes, Path]) -> List[str]:
        """
        Extract relevant tags from an image.
        
        Args:
            image_data: The image to analyze. Can be a file path, URL, or raw bytes.
            
        Returns:
            List of tags describing the image content.
        """
        analysis = self.analyze_image(image_data)
        return analysis.get("tags", [])
    
    def _prepare_image(self, image_data: Union[str, bytes, Path]) -> str:
        """
        Prepare image data for API submission.
        
        Args:
            image_data: The image to prepare. Can be a file path, URL, or raw bytes.
            
        Returns:
            Base64-encoded image data or URL.
        """
        if isinstance(image_data, str) and (image_data.startswith("http://") or image_data.startswith("https://")):
            # It's a URL, return as is
            return image_data
        
        if isinstance(image_data, Path) or (isinstance(image_data, str) and not image_data.startswith("data:")):
            # It's a file path, read the file
            try:
                with open(image_data, "rb") as f:
                    image_bytes = f.read()
                return base64.b64encode(image_bytes).decode("utf-8")
            except Exception as e:
                logger.error(f"Error reading image file: {e}")
                raise
        
        if isinstance(image_data, bytes):
            # It's already bytes, encode it
            return base64.b64encode(image_data).decode("utf-8")
        
        # If it's already a base64 string, return as is
        return image_data
    
    def _mock_analysis(self) -> Dict[str, Any]:
        """
        Generate mock analysis results for testing or when API is unavailable.
        
        Returns:
            Dictionary containing mock analysis results.
        """
        return {
            "tags": ["construction", "renovation", "home", "building"],
            "description": "A home renovation project showing construction work.",
            "confidence": 0.85,
            "categories": ["construction", "renovation", "home improvement"],
            "objects_detected": ["tools", "building materials", "house structure"]
        }

# Create a singleton instance for easy import
openai_vision_tool = OpenAIVisionTool()