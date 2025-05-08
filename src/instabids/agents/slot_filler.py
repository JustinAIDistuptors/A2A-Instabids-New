'''
Slot filling module for structured data collection in conversations.

This module provides utilities for tracking and filling required information slots
in a conversation, helping guide users through providing all necessary details.
Now enhanced with vision analysis to extract information from images.
'''
from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

# Import vision tool integration
from instabids.tools.vision_tool_plus import analyse, validate_image_for_bid_card

# Logger setup
logger = logging.getLogger(__name__)

# Define slots with their questions and any validation/extraction logic
SLOTS = {
    "category": {
        "q": "What category best fits this project (repair, renovation, installation, maintenance, construction, other)?",
        "options": ["repair", "renovation", "installation", "maintenance", "construction", "other"],
        "vision_field": "labels"  # Field from vision analysis to use for this slot
    },
    "job_type": {
        "q": "Which specific job is it? (e.g. roof repair, lawn mowing)",
        "vision_field": "labels"  # Can also be extracted from labels
    },
    "damage_assessment": {  # New slot for damage info from images
        "q": "Can you describe any damage that needs to be addressed?",
        "vision_field": "damage_assessment"  # Direct field from vision analysis
    },
    "budget_range": {
        "q": "What budget range do you have in mind (rough estimate is fine)?"
    },
    "timeline": {
        "q": "When would you like the work to start and finish?"
    },
    "location": {
        "q": "Where is the project located?"
    },
    "group_bidding": {
        "q": "Are you open to group bidding to lower cost? (yes/no)",
        "options": ["yes", "no"]
    },
    "project_images": {  # New slot for storing image paths or data
        "q": "Do you have any photos of the project you'd like to share? You can upload them now.",
        "is_media": True  # Flag indicating this slot expects media content
    }
}

def missing_slots(card: Dict[str, Any]) -> List[str]:
    '''
    Return slots still empty, in priority order.
    
    Args:
        card: Dictionary containing slot values
        
    Returns:
        List of slot names that are still empty, in priority order
    '''
    # Define the order in which slots should be filled
    order = ["category", "job_type", "damage_assessment", "budget_range", 
             "timeline", "location", "group_bidding", "project_images"]
    
    # Return slots that are empty or None
    return [s for s in order if not card.get(s)]

def validate_slot(slot_name: str, value: Any) -> bool:
    '''
    Validate a slot value against any defined constraints.
    
    Args:
        slot_name: Name of the slot to validate
        value: Value to validate
        
    Returns:
        True if valid, False otherwise
    '''
    slot_def = SLOTS.get(slot_name, {})
    
    # If the slot is for media, check if it's a valid path or data structure
    if slot_def.get("is_media", False):
        if isinstance(value, list):
            # For lists of image paths, check that at least one exists
            return len(value) > 0 and any(Path(p).exists() for p in value if isinstance(p, str))
        elif isinstance(value, str):
            # For a single path, check that it exists
            return Path(value).exists()
        else:
            # For other data structures, just check that it has content
            return bool(value)
    
    # If the slot has defined options, check that the value is one of them
    if "options" in slot_def and value:
        return str(value).lower() in [opt.lower() for opt in slot_def["options"]]
    
    # For slots without specific validation, just check they're not empty
    return bool(value)

def get_next_question(card: Dict[str, Any]) -> str:
    '''
    Get the next question to ask based on missing slots.
    
    Args:
        card: Dictionary containing slot values
        
    Returns:
        Question string to ask the user, or empty string if all slots are filled
    '''
    missing = missing_slots(card)
    if not missing:
        return ""
    
    return SLOTS[missing[0]]["q"]

async def process_image_for_slots(image_path: str) -> Dict[str, Any]:
    '''
    Process an image to extract slot values where possible.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary of extracted slot values
    '''
    try:
        # Validate the image is meaningful for our context
        validation = await validate_image_for_bid_card(image_path)
        
        if not validation.get("is_valid", False):
            logger.warning(f"Image not valid for bid card: {image_path}")
            return {}
        
        # Get the detailed analysis
        analysis = validation.get("analysis", {})
        
        # Extract slot values from analysis
        extracted = {}
        
        # Go through all slots and check if they can be populated from vision data
        for slot_name, slot_def in SLOTS.items():
            if "vision_field" in slot_def:
                field = slot_def["vision_field"]
                if field in analysis and analysis[field]:
                    # For label fields (usually lists), use the most relevant label
                    if field == "labels" and isinstance(analysis[field], list):
                        if slot_name == "category":
                            # Try to map to one of our categories
                            categories = slot_def.get("options", [])
                            for label in analysis[field]:
                                if any(cat in label.lower() for cat in categories):
                                    extracted[slot_name] = next(
                                        cat for cat in categories 
                                        if cat in label.lower()
                                    )
                                    break
                        elif slot_name == "job_type" and analysis[field]:
                            # Use the first couple of labels to suggest a job type
                            extracted[slot_name] = " ".join(analysis[field][:2])
                    else:
                        # For string fields, use directly
                        extracted[slot_name] = analysis[field]
        
        # Add the image path to project_images slot
        if "project_images" not in extracted:
            # Initialize as a list if this is the first image
            extracted["project_images"] = [image_path]
        elif isinstance(extracted.get("project_images"), list):
            # Append to existing list if we already have images
            if image_path not in extracted["project_images"]:
                extracted["project_images"].append(image_path)
        
        return extracted
        
    except Exception as e:
        logger.error(f"Error processing image for slots: {e}")
        return {}

async def update_card_from_images(card: Dict[str, Any], image_paths: List[str]) -> Dict[str, Any]:
    '''
    Update a card with information extracted from multiple images.
    
    Args:
        card: Existing card data
        image_paths: List of paths to image files
        
    Returns:
        Updated card with information from images
    '''
    # Process each image and collect results
    results = await asyncio.gather(
        *[process_image_for_slots(path) for path in image_paths]
    )
    
    # Merge results into card
    updated_card = card.copy()
    
    # Track all images we've processed
    all_images = []
    
    for result in results:
        for slot_name, value in result.items():
            # For project_images slot, we collect all images
            if slot_name == "project_images":
                if isinstance(value, list):
                    all_images.extend(value)
                else:
                    all_images.append(value)
            # For other slots, only update if the slot is empty or has lower confidence
            elif not updated_card.get(slot_name):
                updated_card[slot_name] = value
    
    # Update the project_images slot with all unique images
    updated_card["project_images"] = list(set(all_images))
    
    return updated_card
