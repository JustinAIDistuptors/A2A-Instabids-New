from __future__ import annotations
from datetime import datetime
import re, uuid
from typing import Tuple
from instabids.data import bidcard_repo

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
        hits = sum(1 for w in words if re.search(rf"\\b{re.escape(w)}\\b", t))
        conf = hits / len(words)
        if conf > score:
            best, score = cat, conf
    return best, score

def create_bid_card(project: dict, vision: dict) -> Tuple[dict, float]:
    cat, txt_score = _classify(project["description"])
    img_score = 0.9 if vision else 0.5
    confidence = round(txt_score*0.6 + img_score*0.4, 2)

    card = {
        "id": str(uuid.uuid4()),
        "project_id": project["id"],
        "category": cat,
        "job_type": project.get("job_type", "tbd"),
        "scope_json": project,
        "photo_meta": vision,
        "ai_confidence": confidence,
        "status": "final" if confidence >= .7 else "draft",
        "created_at": datetime.utcnow().isoformat(),
    }
    bidcard_repo.upsert(card)
    return card, confidence