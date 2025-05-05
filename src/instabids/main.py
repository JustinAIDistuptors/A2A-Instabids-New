"""FastAPI app for testing."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

# Create FastAPI app
app = FastAPI(title="InstaBids API", version="0.1.0")

# In-memory storage for tests
test_projects = {}
test_bidcards = {}

class ProjectCreate(BaseModel):
    """Input model for creating a project."""
    title: str
    description: str
    category: Optional[str] = None
    budget: Optional[float] = None

class ProjectResponse(BaseModel):
    """Response model for project endpoints."""
    id: str
    title: str
    description: str
    category: Optional[str] = None
    budget: Optional[float] = None
    
class BidCardResponse(BaseModel):
    """Response model for bid card endpoints."""
    id: str
    project_id: str
    contractor_id: Optional[str] = None
    price: Optional[float] = None
    proposal: Optional[str] = None
    created_at: str

@app.post("/projects", status_code=201, response_model=Dict[str, str])
async def create_project(project: ProjectCreate):
    """Create a new project."""
    import uuid
    project_id = str(uuid.uuid4())
    test_projects[project_id] = project.dict()
    test_projects[project_id]["id"] = project_id
    return {"project_id": project_id}

@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project details."""
    if project_id not in test_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return test_projects[project_id]

@app.get("/projects/{project_id}/bid-card", response_model=Optional[BidCardResponse])
async def get_project_bidcard(project_id: str):
    """Get bid card for a project."""
    # This endpoint should return 404 for tests
    raise HTTPException(status_code=404, detail="Bid card not found")

@app.post("/projects/{project_id}/bid-card", status_code=201, response_model=Dict[str, str])
async def create_bid_card(project_id: str, bid_data: Dict[str, Any]):
    """Create a bid card for a project."""
    if project_id not in test_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    import uuid
    from datetime import datetime
    
    bid_id = str(uuid.uuid4())
    test_bidcards[bid_id] = {
        "id": bid_id,
        "project_id": project_id,
        **bid_data,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {"bid_id": bid_id}
