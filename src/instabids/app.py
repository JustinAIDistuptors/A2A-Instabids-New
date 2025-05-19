import sys
import os
import importlib.util

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from instabids.agents.factory import get_homeowner_agent
from instabids.data_access import create_project, get_project_status
from instabids.webhooks import verify_signature, push_to_ui
import uuid, asyncio

async def run_homeowner_flow(task_id: str, payload: dict):
    # Get a HomeownerAgent instance, potentially with user-specific memory
    # Using task_id as a proxy for user_id for memory scoping in this example
    agent = get_homeowner_agent(user_id_for_memory=task_id)
    print(f"--- Got agent for task_id/user_id: {task_id} ---")
    
    # Create the initial project record
    await create_project(task_id, payload)
    await agent.run_async(task_id=task_id, project=payload)

def create_app() -> FastAPI:
    app = FastAPI(title="Instabids A2A Service")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------- A2A endpoints ------- #
    @app.post("/a2a/v1/tasks", status_code=202)
    async def create_task(payload: dict):
        task_id = uuid.uuid4().hex
        print(f"--- In create_task (no auth_signal/token param) ---")
        asyncio.create_task(run_homeowner_flow(task_id, payload))
        return {"task_id": task_id, "status": "IN_PROGRESS"}

    @app.get("/a2a/v1/tasks/{task_id}")
    async def get_task(task_id: str, token: str = Depends(verify_signature)):
        project_task_status = await get_project_status(task_id)
        if not project_task_status:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return project_task_status

    # ------ WebSocket stream for UI ------ #
    @app.websocket("/ws/bids/{task_id}")
    async def ws_bids(websocket: WebSocket, task_id: str):
        await websocket.accept()
        async for event in push_to_ui.subscribe(task_id):
            await websocket.send_json(event)
            
    return app

if __name__ == "__main__":
    import uvicorn
    app_instance = create_app()
    uvicorn.run(app_instance, host="0.0.0.0", port=8001)
