"""Advanced job‑classification with confidence + optional vision features."""
from __future__ import annotations
from typing import Literal, Tuple, Dict
import re

JobCategory = Literal[
    "RENOVATION",      # major remodel / multi‑phase
    "REPAIR",          # fix something broken
    "INSTALLATION",    # put in a new unit/fixture
    "MAINTENANCE",     # recurring upkeep
    "CONSTRUCTION",    # build new structure
    "OTHER",           # fallback
]

_TEXT_RULES: Dict[JobCategory, list[str]] = {
    "RENOVATION":   ["remodel", "renovation", "kitchen", "bathroom", "gut"],
    "REPAIR":       ["leak", "broken", "damage", "replace shingle", "hole"],
    "INSTALLATION": ["install", "mount", "set up", "new unit", "replace faucet"],
    "MAINTENANCE":  ["mow", "clean", "service", "maintenance", "upkeep"],
    "CONSTRUCTION": ["add on", "extension", "build deck", "foundation", "concrete"],
}

# rudimentary mapping of simple vision tags → category boosts
_VISION_HINTS: Dict[str, JobCategory] = {
    "rubble": "REPAIR",
    "blueprint": "CONSTRUCTION",
    "grass": "MAINTENANCE",
}

def _score(text: str, hints: list[str]|None=None) -> Tuple[JobCategory, float]:
    tl = text.lower()
    best_cat: JobCategory = "OTHER"
    best_score = 0.0
    # text keyword scoring
    for cat, words in _TEXT_RULES.items():
        hits = sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", tl))
        score = hits / len(words)
        if score > best_score:
            best_cat, best_score = cat, score
    # vision hint boost
    if hints:
        for h in hints:
            if h in _VISION_HINTS:
                if best_score < 0.4:  # small nudge if weak text match
                    best_cat, best_score = _VISION_HINTS[h], 0.45
    return best_cat, best_score

def classify(text: str, vision_tags: list[str]|None=None) -> dict[str,str|float]:
    cat, score = _score(text, vision_tags)
    if score < 0.25:
        cat = "OTHER"
    return {"category": cat, "confidence": round(score, 3)}