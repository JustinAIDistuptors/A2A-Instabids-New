from fastapi import APIRouter, HTTPException
from instabids.agents.factory import get_homeowner_agent
from instabids.data import bidcard_repo
from typing import Dict, Any, List

router = APIRouter(prefix="/projects")

@router.post("/{project_id}/bid-card/refresh")
async def refresh(project_id: str, user_id: str) -> Dict[str, Any]:
    """Refresh a bid card for a project."""
    agent = get_homeowner_agent()
    res = await agent.process_input(user_id, description="REFRESH")
    if res["project_id"] != project_id:
        raise HTTPException(status_code=400, detail="Wrong project")
    return res["bid_card"]

@router.get("/{project_id}/bid-card")
async def get_card(project_id: str) -> Dict[str, Any]:
    """Get a bid card for a project."""
    card = bidcard_repo.fetch(project_id)
    if not card:
        raise HTTPException(status_code=404)
    return card

# Additional endpoints for bid card operations
@router.get("/owner/{owner_id}/bid-cards")
async def list_owner_cards(owner_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """List all bid cards for a homeowner."""
    cards = bidcard_repo.get_bid_cards_by_homeowner(owner_id)
    return {"owner_id": owner_id, "cards": cards}
