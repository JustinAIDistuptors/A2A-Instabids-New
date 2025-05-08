from __future__ import annotations
from datetime import datetime
import re, uuid
from typing import Tuple, Dict, Any, Optional
from instabids.data import bidcard_repo

class BidCardAgent:
    """Agent responsible for managing bid cards."""
    
    def __init__(self):
        """Initialize BidCardAgent."""
        self.project_id = None
    
    async def process_input(self, user_id: str, description: str = "") -> Dict[str, Any]:
        """Process input and return a response with bid card info."""
        # For refresh operation, fetch the current card
        if description == "REFRESH" and self.project_id:
            card = bidcard_repo.fetch(self.project_id)
            return {
                "project_id": self.project_id,
                "bid_card": card
            }
        return {
            "project_id": self.project_id,
            "bid_card": None
        }

TXT_RULES = {
    "repair": ["leak", "burst", "urgent", "fix", "patch"],
    "renovation": ["renovation", "remodel", "kitchen", "bathroom"],
    "installation": ["install", "replace", "mount"],
    "maintenance": ["clean", "service", "mowing"],
    "construction": ["build", "addition", "foundation"],
}

def _classify(text: str) -> Tuple[str, float]:
    t = text.lower()
    best, score = "other", 0.0
    for cat, words in TXT_RULES.items():
        hits = sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", t))
        conf = hits / len(words)
        if conf > score:
            best, score = cat, conf
    return best, score

def create_bid_card(project: Dict[str, Any], vision: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    cat, txt_score = _classify(project["description"])
    img_score = 0.9 if vision else 0.5
    confidence = round(txt_score*0.6 + img_score*0.4, 2)

    card = {
        "id": str(uuid.uuid4()),
        "project_id": project["id"],
        "category": cat,
        "job_type": project.get("job_type", "tbd"),
        "budget_range": project.get("budget_range"),
        "timeline": project.get("timeline"),
        "group_bidding": project.get("group_bidding", False),
        "scope_json": project,
        "photo_meta": vision,
        "ai_confidence": confidence,
        "status": "final" if confidence >= .7 else "draft",
        "created_at": datetime.utcnow().isoformat(),
    }
    bidcard_repo.upsert(card)
    return card, confidence
