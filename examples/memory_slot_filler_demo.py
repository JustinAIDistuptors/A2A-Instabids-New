#!/usr/bin/env python
"""
Demo application showing memory and slot-filling integration.

This example demonstrates how to use the persistent memory and slot-filling
features of InstaBids' ADK implementation.
"""

import os
import logging
import asyncio
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path
import uuid

from supabase import create_client, Client

from src.memory.persistent_memory import PersistentMemory
from src.slot_filler.slot_filler_factory import SlotFillerFactory, SlotFiller


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def create_supabase_client() -> Client:
    """Create and return a Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE")
    
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE environment variables must be set"
        )
    
    return create_client(url, key)


def extract_location(text: str) -> Optional[str]:
    """Simple location extractor."""
    locations = ["Denver", "New York", "Miami", "Chicago", "Los Angeles"]
    for location in locations:
        if location.lower() in text.lower():
            return location
    return None


def extract_project_type(text: str) -> Optional[str]:
    """Simple project type extractor."""
    project_types = ["bathroom", "kitchen", "bedroom", "living room"]
    for project_type in project_types:
        if project_type.lower() in text.lower():
            return project_type
    return None


async def demo_conversation(
    user_id: str,
    conversation_id: str,
    messages: Dict[str, str],
    image_paths: Optional[Dict[str, str]] = None,
) -> None:
    """Runs a demo conversation with memory and slot filling."""
    # Create Supabase client
    try:
        db = create_supabase_client()
        logger.info("Supabase client created successfully")
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return
    
    # Ensure user_id is a valid UUID
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid4()
        logger.warning(f"Provided user_id '{user_id}' is not a valid UUID. Using generated UUID: {user_uuid}")
        user_id = str(user_uuid)
    
    # Create memory for user
    memory = PersistentMemory(db, user_id)
    await memory.load()
    logger.info(f"Loaded memory for user {user_id}")
    
    # Create slot filler factory
    factory = SlotFillerFactory(memory)
    
    # Create slot filler for conversation
    slot_filler = await factory.create_slot_filler(
        conversation_id,
        ["location", "project_type"],  # Required slots
        ["timeline", "budget"]         # Optional slots
    )
    
    # Create extractors
    text_extractors = {
        "location": extract_location,
        "project_type": extract_project_type,
    }
    
    # Process messages in sequence
    for role, message in messages.items():
        print(f"{role.upper()}: {message}")
        
        # Update conversation history
        await slot_filler.update_from_message(role, message)
        
        # If user message, extract slots
        if role == "user":
            extracted = await slot_filler.extract_slots_from_message(message, text_extractors)
            if extracted:
                print(f"  Extracted slots: {extracted}")
        
    # Process images if provided
    if image_paths:
        for image_id, image_path in image_paths.items():
            print(f"Processing image: {image_path}")
            
            # In a real implementation, this would use vision APIs
            # Here we're just simulating based on the filename
            project_type = None
            style = None
            
            path = Path(image_path).name.lower()
            if "bathroom" in path:
                project_type = "bathroom"
            elif "kitchen" in path:
                project_type = "kitchen"
                
            if "modern" in path:
                style = "modern"
            elif "traditional" in path:
                style = "traditional"
            
            # Process image
            image_data = {
                "id": image_id,
                "url": image_path,
                "metadata": {
                    "width": 800,
                    "height": 600,
                    "filename": Path(image_path).name
                }
            }
            
            vision_extractors = {}
            if project_type:
                vision_extractors["project_type"] = lambda _: project_type
            if style:
                vision_extractors["style_preference"] = lambda _: style
                
            if vision_extractors:
                extracted = await slot_filler.process_vision_inputs(image_data, vision_extractors)
                print(f"  Extracted from image: {extracted}")
    
    # Print final state
    print("\n" + "=" * 50)
    print("FINAL STATE:")
    filled_slots = slot_filler.get_filled_slots()
    print(f"Filled slots: {filled_slots}")
    
    if slot_filler.all_required_slots_filled():
        print("All required slots are filled!")
        print(f"Ready to create {filled_slots.get('project_type')} project in {filled_slots.get('location')}")
    else:
        missing = slot_filler.get_missing_required_slots()
        print(f"Missing required slots: {missing}")
        
    # Save state
    await slot_filler.save()
    print("State saved to database.")
    
    # Get conversation history
    history = slot_filler.get_history()
    print(f"Conversation history ({len(history)} messages):")
    for i, msg in enumerate(history):
        print(f"  {i+1}. {msg['role'].upper()}: {msg['content']}")
    
    # Get recently stored interactions
    interactions = memory.get_recent_interactions(limit=3)
    print(f"Recent interactions ({len(interactions)}):")
    for i, interaction in enumerate(interactions):
        print(f"  {i+1}. {interaction['type']} at {interaction['timestamp']}")


async def main():
    """Main entry point for the demo application."""
    parser = argparse.ArgumentParser(description="Demo of memory and slot filling integration")
    parser.add_argument("--user", type=str, default="550e8400-e29b-41d4-a716-446655440000", help="User ID for the demo (must be a valid UUID)")
    parser.add_argument("--conversation", type=str, default="demo-conversation-123", help="Conversation ID for the demo")
    parser.add_argument("--image", type=str, help="Optional path to a sample image")
    args = parser.parse_args()
    
    # Sample conversation
    messages = {
        "user": "I'm looking to renovate my bathroom in Denver",
        "assistant": "Great! I can help with your bathroom renovation in Denver. What's your timeline for this project?",
        "user": "I'm hoping to start within the next 1-3 months",
        "assistant": "Perfect! A 1-3 month timeline works well for bathroom renovations. Do you have a budget in mind?",
    }
    
    # Process images if provided
    image_paths = None
    if args.image:
        image_paths = {"img1": args.image}
    
    # Run the demo
    await demo_conversation(args.user, args.conversation, messages, image_paths)


if __name__ == "__main__":
    asyncio.run(main())