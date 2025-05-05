"""Job classification module for identifying project types."""
from typing import Dict, Any, Tuple
import re

# Classification rules based on keywords
CLASSIFICATION_RULES = {
    "bathroom": ["bathroom", "toilet", "shower", "sink", "bathtub", "vanity"],
    "kitchen": ["kitchen", "cabinets", "countertop", "appliance", "sink", "stove"],
    "repair": ["leak", "burst", "urgent", "fix", "patch", "broken", "damage"],
    "renovation": ["renovation", "remodel", "upgrade", "modernize"],
    "installation": ["install", "replace", "mount", "setup", "assemble"],
    "maintenance": ["clean", "service", "mowing", "trim", "maintain", "inspect"],
    "construction": ["build", "addition", "foundation", "construct", "new"],
    "electrical": ["electrical", "wiring", "outlet", "circuit", "breaker", "panel"],
    "plumbing": ["plumbing", "pipe", "drain", "water", "faucet", "toilet"],
    "roofing": ["roof", "shingle", "gutter", "flashing", "leak"],
    "landscaping": ["landscaping", "yard", "garden", "lawn", "plant", "tree"],
    "flooring": ["floor", "tile", "hardwood", "carpet", "vinyl", "laminate"],
    "painting": ["paint", "stain", "wallpaper", "caulk", "primer"],
}

def classify(text: str) -> Tuple[str, float]:
    """
    Classify a job description into a primary category with confidence score.
    
    Args:
        text: The job description text
        
    Returns:
        Tuple containing (category, confidence_score)
    """
    # Normalize text
    if text is None:
        return "other", 0.0
        
    t = text.lower()
    
    # Initialize best match
    best_category, confidence = "other", 0.0
    
    # Check each category's keywords
    for category, keywords in CLASSIFICATION_RULES.items():
        hits = sum(1 for word in keywords if re.search(r'\b' + re.escape(word) + r'\b', t))
        
        # Calculate confidence based on keyword matches
        if hits > 0:
            score = hits / len(keywords)
            if score > confidence:
                best_category, confidence = category, score
    
    return best_category, confidence

def get_subcategory(category: str, description: str) -> str:
    """
    Extract a subcategory based on the category and description.
    
    Args:
        category: Primary category
        description: Job description
        
    Returns:
        Subcategory string
    """
    # Common subcategories by category
    subcategories = {
        "repair": ["roof", "plumbing", "electrical", "appliance", "structural", "fence"],
        "renovation": ["kitchen", "bathroom", "basement", "living room", "bedroom", "exterior"],
        "installation": ["appliance", "fixture", "window", "door", "flooring", "lighting"],
        "maintenance": ["lawn", "garden", "pool", "hvac", "gutter", "driveway"],
        "construction": ["addition", "shed", "deck", "patio", "garage", "fence"]
    }
    
    # Return category directly if it's a specialized one
    if category in ["bathroom", "kitchen", "electrical", "plumbing", "roofing", 
                    "landscaping", "flooring", "painting"]:
        return category
    
    # Check for subcategory terms in description
    if category in subcategories and description:
        description_lower = description.lower()
        for subcategory in subcategories[category]:
            if subcategory in description_lower:
                return subcategory
    
    # Default subcategory is "general"
    return f"general {category}"

def classify_with_metadata(text: str) -> Dict[str, Any]:
    """
    Classify a job description and return full metadata.
    
    Args:
        text: Job description
        
    Returns:
        Dictionary with classification metadata
    """
    category, confidence = classify(text)
    subcategory = get_subcategory(category, text)
    
    return {
        "category": category,
        "subcategory": subcategory,
        "confidence": confidence,
        "description": text[:150] if text else ""  # Truncated description
    }