# src/instabids/agents/bidcard_agent.py
from __future__ import annotations
from datetime import datetime
import re, uuid
import logging # Added logging
from typing import Tuple, Dict, Any, List # Added Dict, Any, List
from instabids.data import bidcard_repo

logger = logging.getLogger(__name__) # Added logger instance

# Simple keyword rules for classification
TXT_RULES = {
    "repair": ["leak", "burst", "urgent", "fix", "patch", "broken", "damaged"],
    "renovation": ["renovation", "remodel", "kitchen", "bathroom", "update", "upgrade"],
    "installation": ["install", "replace", "mount", "new", "setup"],
    "maintenance": ["clean", "service", "mowing", "upkeep", "tune-up"],
    "construction": ["build", "addition", "foundation", "new construction", "frame"],
}

def _classify(text: str) -> Tuple[str, float]:
    """Classifies text into a category based on keyword matching."""
    t = text.lower()
    if not t: # Handle empty input text
        return "other", 0.0
    best, score = "other", 0.0
    for cat, words in TXT_RULES.items():
        # Consider word boundaries for more accurate matching
        hits = sum(1 for w in words if re.search(rf'\b{re.escape(w)}\b', t))
        # Simple confidence: ratio of hits to total keywords for the category
        # Avoid division by zero if a category has no keywords (shouldn't happen here)
        conf = hits / len(words) if len(words) > 0 else 0.0
        if conf > score:
            best, score = cat, conf
    # Basic confidence boost if score is low but text exists
    if score < 0.1 and len(t) > 5:
        score = 0.1
    logger.debug(f"Classified text '{t[:50]}...' as '{best}' with score {score:.2f}")
    return best, score

def create_bid_card(project: Dict[str, Any], vision: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
    """
    Creates a bid card dictionary, classifying based on project text and optionally vision tags.

    Args:
        project: Dictionary containing project details like 'description', 'job_type', 'vision_tags', 'id'.
        vision: Dictionary containing photo metadata (or None). Used for confidence scoring.

    Returns:
        A tuple containing the created bid card dictionary and the AI confidence score.
    """
    # S2-5: Consider vision tags for classification
    # Prioritize job_type if available, fallback to description
    job_text_for_classification = project.get("job_type") or project.get("description", "")
    vision_tags: List[str] = project.get("vision_tags", []) # Get tags passed from HomeownerAgent

    # If primary job text is minimal/missing, use vision tags as primary input
    if not job_text_for_classification or len(job_text_for_classification) < 10: # Arbitrary length check
        if vision_tags: # Only use tags if they exist
            job_text_for_classification = " ".join(vision_tags)
            logger.info(f"Using vision tags for classification: {' '.join(vision_tags)}")
        else:
            logger.warning("No job text or vision tags available for classification. Category set to 'other'.")
            # Fallback to default if both are empty
            job_text_for_classification = "" # Ensure it's a string for _classify
            cat = "other"
            txt_score = 0.0
    # else:
         # Alternative: Append vision tags even if text exists? Could improve classification.
         # job_text_for_classification += " " + " ".join(vision_tags)

    # Classify only if we haven't defaulted due to missing info
    if 'cat' not in locals(): # Check if cat was already set to 'other'
        cat, txt_score = _classify(job_text_for_classification)

    # Confidence scoring - adjust weights as needed
    img_score = 0.9 if vision else 0.5 # Existing logic - maybe refine based on vision quality?
    # Ensure txt_score is used in confidence calculation
    confidence = round(txt_score*0.6 + img_score*0.4, 2)

    # Ensure required fields for the DB are present
    project_id = project.get("id")
    if not project_id:
        logger.error("Project ID missing, cannot create bid card.")
        # Decide how to handle this - raise error, return dummy?
        # Returning a partial card might cause DB errors. Let's log and return None for card part.
        return {"error": "Missing project ID"}, 0.0

    card = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "category": cat, # Category determined potentially using vision tags
        "job_type": project.get("job_type", "tbd"), # Keep original job_type if provided
        "budget_range": project.get("budget_range"),
        "timeline": project.get("timeline"),
        "location": project.get("location"), # Added location field
        "group_bidding": project.get("group_bidding", False),
        "scope_json": project, # Store the original project data as scope
        "photo_meta": vision, # Store photo metadata if provided
        "ai_confidence": confidence,
        # Status based on confidence threshold
        "status": "final" if confidence >= .7 else "draft",
        "created_at": datetime.utcnow().isoformat(),
        # Add other fields from project if they map directly to bidcard table
        "title": project.get("title"),
        "budget_min": project.get("budget_min"),
        "budget_max": project.get("budget_max"),
        "details": project.get("details"), # Catch-all for extra info
    }

    # Clean up None values before inserting if DB schema requires non-null
    card_to_save = {k: v for k, v in card.items() if v is not None}

    try:
        # Assuming bidcard_repo.upsert handles creation/update based on some logic (e.g., project_id?)
        # If it's strictly insert, use bidcard_repo.insert or similar
        bidcard_repo.upsert(card_to_save) # Use cleaned card
        logger.info(f"Bid card upserted for project {project_id}, category: {cat}, confidence: {confidence}")
    except Exception as e:
        logger.error(f"Failed to save bid card for project {project_id}: {e}", exc_info=True)
        # Return error indication?
        return {"error": "Failed to save bid card to database", "details": str(e)}, confidence


    return card, confidence # Return the full card (including Nones) and confidence
