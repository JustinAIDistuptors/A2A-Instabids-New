"""WebSocket endpoints for real-time chat with agents."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from instabids.agents.factory import get_homeowner_agent
from typing import Dict, Any, Optional
import json
import uuid
import asyncio
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws")

@router.websocket("/chat/{project_id}")
async def chat_ws(ws: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time chat with the homeowner agent.

    Args:
        ws: WebSocket connection
        project_id: ID of the project to chat about
    """
    await ws.accept()  # FastAPI WS pattern
    agent = get_homeowner_agent()
    
    try:
        while True:
            # Receive message from client
            data = await ws.receive_json()
            
            # Validate required fields
            if "user_id" not in data:
                await ws.send_json({
                    "error": "Missing required field: user_id",
                    "status": 400
                })
                continue
            
            # Process the input through the agent
            try:
                res = await agent.process_input(
                    user_id=data["user_id"],
                    description=data.get("text"),
                    form_payload=data.get("form"),
                    project_id=project_id
                )
                
                # Send response back to client
                await ws.send_text(json.dumps(res))
                
                # Close connection if conversation is complete
                if res.get("need_more") is False:
                    await ws.close()
                    break
                    
            except Exception as e:
                logger.error(f"Error processing agent input: {str(e)}")
                await ws.send_json({
                    "error": f"Failed to process input: {str(e)}",
                    "status": 500
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for project {project_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await ws.close(code=1011, reason=str(e))
        except:
            pass