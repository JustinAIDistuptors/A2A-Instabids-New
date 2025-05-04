"""
WebSocket route for real-time chat with the homeowner agent.

This module provides a WebSocket endpoint for real-time communication
with the homeowner agent, handling incoming messages and sending responses.
"""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from instabids.agents.homeowner_agent import HomeownerAgent
from instabids.data import messages_repo
from instabids.models.bid_card import BidCard

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/chat/{project_id}")
async def chat_ws(ws: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time chat with the homeowner agent.
    
    Args:
        ws: WebSocket connection
        project_id: ID of the project to chat about
    """
    await ws.accept()
    
    # Initialize agent for this project
    agent = HomeownerAgent(project_id)
    
    try:
        while True:
            # Receive message from client
            data = await ws.receive_text()
            message = json.loads(data)
            
            # Extract user ID and message content
            user_id = message.get("user_id")
            text = message.get("text", "")
            audio = message.get("audio")
            form_data = message.get("form_data", {})
            
            if not user_id:
                await ws.send_json({"error": "User ID is required"})
                continue
            
            # Save incoming message to database
            if text:
                await messages_repo.insert_message(
                    project_id=project_id,
                    user_id=user_id,
                    role="homeowner",
                    content=text
                )
            
            # Process the input with the agent
            try:
                res = await agent.process_input({
                    "user_id": user_id,
                    "text": text,
                    "audio": audio,
                    "form_data": form_data
                })
                
                # Save agent response to database
                if "follow_up" in res:
                    await messages_repo.insert_message(
                        project_id=project_id,
                        user_id=user_id,
                        role="agent",
                        content=res["follow_up"]
                    )
                
                # If we have a complete bid card, format it using the Pydantic model
                if not res.get("need_more", True) and "project_id" in res:
                    # Retrieve the complete bid card data
                    bid_card_data = {
                        "id": res["project_id"],
                        "user_id": user_id,
                        **agent.memory
                    }
                    
                    # Validate and serialize using the Pydantic model
                    await ws.send_text(BidCard(**bid_card_data).model_dump_json())
                else:
                    # Send the regular response
                    await ws.send_json(res)
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await ws.send_json({"error": str(e)})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for project {project_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws.close()