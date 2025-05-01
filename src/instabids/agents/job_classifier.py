"""Simple rule‑based job classifier (placeholder until ML model)."""
from __future__ import annotations

from typing import Dict, Tuple

CATEGORIES = {
    "roof": "One‑Off Project",
    "lawn": "Ongoing Service",
    "leak": "Handyman",
    "demolition": "Labor‑Only",
    "remodel": "Multi‑Phase Project",
    "burst": "Emergency Repair",
}

URGENCY_KEYWORDS = {
    "emergency": "Emergency",
    "asap": "Urgent",
    "dream": "Dream",
}


def classify_job(desc: str, vision_ctx: Dict) -> Dict[str, str]:
    desc_lower = desc.lower()
    category = "One‑Off Project"
    for kw, cat in CATEGORIES.items():
        if kw in desc_lower:
            category = cat
            break

    urgency = "Dream"
    for kw, urg in URGENCY_KEYWORDS.items():
        if kw in desc_lower:
        urgency = urg
            break

    return {"category": category, "urgency": urgency}
