"""
BidCardAgent – builds a normalized bid‑card JSON for a project.

create_bid_card() returns (bid_card_dict, confidence_float).
For now it does simple keyword classification + dummy image score.
"""

from __future__ import annotations
from typing import List, Tuple
import re
import uuid
from datetime import datetime
from instabids.data import bidcard_repo

CATEGORIES = {
    "renovation": ["kitchen", "bathroom", "remodel", "renovation"],
    "repair": ["leak", "patch", "burst", "fix"],
    "installation": ["install", "replace", "mount"],
    "maintenance": ["clean", "service", "tune‑up", "maintenance"],
    "construction": ["build", "add‑on", "foundation"],
}

def _classify(desc: str) -> Tuple[str, float]:
    desc_l = desc.lower()
    for cat, words in CATEGORIES.items():
        if any(re.search(rf"\\b{re.escape(w)}\\b", desc_l) for w in words):
            return cat, 0.8
    return "other", 0.4

def create_bid_card(project: dict, vision_ctx: dict) -> Tuple[dict, float]:
    cat, txt_score = _classify(project["description"])
    img_score = 0.9 if vision_ctx else 0.5
    confidence = round(txt_score * 0.6 + img_score * 0.4, 2)

    bid_card = {
        "id": str(uuid.uuid4()),
        "project_id": project["id"],
        "created_at": datetime.utcnow().isoformat(),
        "status": "draft" if confidence < 0.7 else "final",
        "category": cat,
        "scope_json": {
            "title": project["title"],
            "description": project["description"],
            "category": cat,
        },
        "photo_meta": vision_ctx,
        "ai_confidence": confidence,
    }
    bidcard_repo.save_bid_card(bid_card)
    return bid_card, confidence