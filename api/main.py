"""FastAPI service exposing HomeownerAgent endpoints."""
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from instabids.agents.factory import get_homeowner_agent
import uuid, os, shutil, tempfile

app = FastAPI(title="InstaBids API", version="0.1.0")

class ProjectIn(BaseModel):
    description: str

@app.post("/projects", status_code=201)
async def create_project(data: ProjectIn, images: list[UploadFile] | None = File(None)):
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
        raise HTTPException(status_code=500, detail=str(exc))