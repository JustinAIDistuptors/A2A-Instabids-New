from fastapi import APIRouter, Depends, HTTPException
from instabids.agents.factory import get_homeowner_agent

router = APIRouter(prefix="/projects")

@router.post("/{project_id}/bid-card/refresh")
async def refresh(project_id: str, user_id: str):
    agent = get_homeowner_agent()
    res = await agent.process_input(user_id, description="REFRESH")
    if res["project_id"] != project_id:
        raise HTTPException(status_code=400, detail="Wrong project")
    return res["bid_card"]

@router.get("/{project_id}/bid-card")
async def get_card(project_id: str):
    from instabids.data.bidcard_repo import fetch
    card = fetch(project_id)
    if not card:
        raise HTTPException(status_code=404)
    return card