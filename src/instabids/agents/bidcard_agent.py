"""BidCardAgent - generates and manages bid cards from project data."""
from __future__ import annotations
from datetime import datetime
import re, uuid, logging
from typing import Tuple, Dict, Any, Optional, List
from dataclasses import dataclass, field

# Try to import from google.adk first, if not available use mock implementation
try:
    from google.adk import LlmAgent
except ImportError:
    from instabids.mock_adk import LlmAgent

from instabids.data import bidcard_repo

logger = logging.getLogger(__name__)

# Data model for BidCard
@dataclass
class BidCard:
    """Data model for a contractor bid card."""
    project_id: str
    homeowner_id: str
    category: str = "other"
    job_type: str = "Unknown"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    timeline: Optional[str] = None
    location: Optional[str] = None
    group_bidding: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "draft"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "homeowner_id": self.homeowner_id,
            "category": self.category,
            "job_type": self.job_type,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "timeline": self.timeline,
            "location": self.location,
            "group_bidding": self.group_bidding,
            "details": self.details,
            "status": self.status,
            "created_at": self.created_at
        }

# Text classification rules - used by both functions
TXT_RULES = {
    "repair": ["leak", "burst", "urgent", "fix", "patch"],
    "renovation": ["renovation", "remodel", "kitchen", "bathroom"],
    "installation": ["install", "replace", "mount", "setup"],
    "maintenance": ["clean", "service", "maintain", "inspect"],
    "construction": ["build", "addition", "foundation"],
}

def _classify(text: str) -> Tuple[str, float]:
    """Classify text into a category with confidence score."""
    t = text.lower()
    best, score = "other", 0.0
    for cat, words in TXT_RULES.items():
        hits = sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", t))
        conf = hits / len(words) if hits > 0 else 0.0
        if conf > score:
            best, score = cat, conf
    return best, score

class BidCardAgent(LlmAgent):
    """Agent for generating bid cards from projects."""
    
    def __init__(self) -> None:
        """Initialize the BidCardAgent."""
        super().__init__(
            name="BidCardAgent",
            system_prompt="You help classify and create bid cards for home improvement projects."
        )
        # Define tools here if needed
        self.tools = []
    
    def map_category(self, description: str) -> str:
        """Map text description to a category."""
        category, _ = _classify(description)
        return category
    
    async def generate(self, bid_card_data: Dict[str, Any]) -> str:
        """Generate a bid card from the given data and save it.
        
        This is an async version to support the async interface required by tests.
        """
        logger.info(f"Generating bid card for project {bid_card_data.get('project_id')}")
        
        # Convert to BidCard object if not already
        if not isinstance(bid_card_data, BidCard):
            # Handle both dictionary and BidCard input formats
            if isinstance(bid_card_data, dict):
                bid_card = BidCard(
                    project_id=bid_card_data.get("project_id", "unknown"),
                    homeowner_id=bid_card_data.get("homeowner_id", "unknown"),
                    category=bid_card_data.get("category", "other"),
                    job_type=bid_card_data.get("job_type", "Unknown"),
                    budget_min=bid_card_data.get("budget_min"),
                    budget_max=bid_card_data.get("budget_max"),
                    timeline=bid_card_data.get("timeline"),
                    location=bid_card_data.get("location"),
                    group_bidding=bid_card_data.get("group_bidding", False),
                    details=bid_card_data.get("details", {})
                )
            else:
                # Invalid type, raise error
                raise TypeError("bid_card_data must be a dict or BidCard object")
        else:
            bid_card = bid_card_data
        
        # Fill in any missing information
        if not bid_card.category or bid_card.category == "other":
            bid_card.category, _ = _classify(bid_card.job_type)
        
        # Set status to final if we have enough information
        required_fields = ["project_id", "homeowner_id", "job_type", "location"]
        has_required = all(getattr(bid_card, field) for field in required_fields)
        bid_card.status = "final" if has_required else "draft"
        
        # Save the bid card to the repo
        try:
            # Convert to dict for storage
            card_dict = bid_card.to_dict() if hasattr(bid_card, "to_dict") else bid_card
            # Save to repo
            bid_id = bidcard_repo.upsert(card_dict)
            logger.info(f"Bid card saved with ID: {bid_id}")
            return bid_id
        except Exception as e:
            logger.error(f"Error saving bid card: {e}", exc_info=True)
            raise

def create_bid_card(project: dict, vision: dict) -> Tuple[dict, float]:
    """Legacy function for creating a bid card from project data."""
    cat, txt_score = _classify(project["description"])
    img_score = 0.9 if vision else 0.5
    confidence = round(txt_score*0.6 + img_score*0.4, 2)
    
    card = {
        "id": str(uuid.uuid4()),
        "project_id": project["id"],
        "homeowner_id": project.get("homeowner_id", "unknown"),
        "category": cat,
        "job_type": project["description"],
        "budget_min": None,
        "budget_max": None,
        "timeline": "2-3 weeks",
        "location": project.get("location", "Unknown"),
        "group_bidding": False,
        "details": {
            "source": "auto-generated",
            "confidence": confidence,
        },
        "status": "draft",
        "created_at": datetime.utcnow().isoformat(),
    }
    bidcard_repo.upsert(card)
    return card, confidence