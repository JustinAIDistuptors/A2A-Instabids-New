"""Job classification logic for HomeownerAgent."""
from __future__ import annotations
from typing import Literal
import re

JobCategory = Literal[
    "ONE_OFF", "ONGOING_SERVICE", "HANDYMAN",
    "LABOR_ONLY", "MULTI_PHASE", "EMERGENCY",
]

_KEYWORDS = {
    "ONE_OFF": ["roof", "fence", "gate", "turf", "deck", "paint", "window replace"],
    "ONGOING_SERVICE": ["lawn", "pool", "maintenance", "cleaning"],
    "HANDYMAN": ["leaky", "patch", "door knob", "fixture", "install"],
    "LABOR_ONLY": ["demo", "haul", "dig", "move"],
    "MULTI_PHASE": ["kitchen", "bathroom", "remodel", "renovation"],
    "EMERGENCY": ["burst", "no heat", "urgent", "emergency", "asap"],
}

def classify(text: str) -> JobCategory:
    tl = text.lower()
    for cat, words in _KEYWORDS.items():
        if any(re.search(rf"\\b{re.escape(w)}\\b", tl) for w in words):
            return cat  # type: ignore[return-value]
    if "help" in tl and "now" in tl:
        return "EMERGENCY"
    return "ONE_OFF"