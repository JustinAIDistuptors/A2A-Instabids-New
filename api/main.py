"""FastAPI service exposing HomeownerAgent endpoints."""
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from instabids.agents.factory import get_homeowner_agent
import os
import uuid
import shutil
import tempfile
import logging
from typing import List, Optional

# Set up logging
logger = logging.getLogger(__name__)

app = FastAPI(title="InstaBids API", version="0.1.0")

class ProjectIn(BaseModel):
    """Input model for project creation."""
    description: str

@app.post("/projects", status_code=201)
async def create_project(data: ProjectIn, images: Optional[List[UploadFile]] = File(None)):
    """
    Create a new project with optional images.
    
    Args:
        data: Project data including description
        images: Optional list of image files
        
    Returns:
        Dict with project_id
        
    Raises:
        HTTPException: If project creation fails
    """
    try:
        # save any uploaded images to /tmp and build metadata list
        temp_dir = tempfile.mkdtemp(prefix="ib_img_")
        img_meta = []
        
        if images:
            for f in images:
                dest = os.path.join(temp_dir, f.filename)
                with open(dest, "wb") as out:
                    shutil.copyfileobj(f.file, out)
                img_meta.append({"storage_path": dest, "photo_type": "current"})
                
        pid = get_homeowner_agent().start_project(data.description, img_meta)
        return {"project_id": pid}
    except Exception as exc:
        logger.error(f"Error creating project: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))