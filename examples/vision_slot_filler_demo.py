'''
Demonstration of the vision-enhanced slot filler functionality.

This example shows how to use the slot filler with vision integration
to collect project information from both text and images.

Usage:
    python vision_slot_filler_demo.py [image_path1] [image_path2] ...
'''
import os
import sys
import asyncio
from pathlib import Path
import json
import logging
from typing import Dict, Any, List, Optional

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the modules
from instabids.agents.slot_filler import missing_slots, SLOTS, get_next_question, process_image_for_slots, update_card_from_images
from instabids.tools.vision_tool_plus import analyse, validate_image_for_bid_card

async def main():
    # Check if OpenAI API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key with: export OPENAI_API_KEY=your-key")
        sys.exit(1)
    
    # Get image paths from command line arguments
    image_paths = []
    if len(sys.argv) > 1:
        image_paths = [Path(arg) for arg in sys.argv[1:] if Path(arg).exists()]
        
    if not image_paths:
        print("Warning: No valid image paths provided")
        print("Usage: python vision_slot_filler_demo.py [image_path1] [image_path2] ...")
        print("\nContinuing with text-only slot filling...")
    else:
        print(f"Processing {len(image_paths)} images...")
    
    # Initialize bid card
    bid_card = {}
    
    # Process images if provided
    if image_paths:
        try:
            print("\n--- Processing Images ---")
            for path in image_paths:
                print(f"Analyzing image: {path.name}")
                validation = await validate_image_for_bid_card(str(path))
                if validation["is_valid"]:
                    print(f"✅ Image is valid: {validation['recommendation']}")
                    analysis = validation["analysis"]
                    print(f"Found labels: {', '.join(analysis['labels'][:5])}{'...' if len(analysis['labels']) > 5 else ''}")
                    if analysis.get("damage_assessment"):
                        print(f"Damage assessment: {analysis['damage_assessment']}")
                else:
                    print(f"❌ Image may not be relevant: {validation['recommendation']}")
            
            # Update the bid card with extracted information
            print("\n--- Updating Bid Card with Image Information ---")
            bid_card = await update_card_from_images(bid_card, [str(path) for path in image_paths])
            print("Information extracted from images:")
            for key, value in bid_card.items():
                if key == "project_images":
                    print(f"  project_images: [{len(value)} images]")
                else:
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"Error processing images: {e}")
            print("Continuing with text-only slot filling...")
    
    # Interactive slot filling session
    print("\n--- Interactive Slot Filling Session ---")
    print("Enter information about your project. Type 'exit' to quit.")
    
    while True:
        # Check which slots are still missing
        missing = missing_slots(bid_card)
        if not missing:
            print("\n✅ All required information collected!")
            break
        
        # Get the next question to ask
        next_question = get_next_question(bid_card)
        print(f"\n{next_question}")
        
        # Get user input
        user_input = input("> ")
        if user_input.lower() in ['exit', 'quit']:
            break
        
        # Update the bid card with the user input
        slot_name = missing[0]
        bid_card[slot_name] = user_input
    
    # Display the final bid card
    print("\n--- Final Project Information ---")
    for key, value in bid_card.items():
        if key == "project_images":
            print(f"{key}: [{len(value)} images]")
        else:
            print(f"{key}: {value}")
    
    print("\nProject information successfully collected!")
    print("In a real application, this would be saved to the database and processed further.")

if __name__ == "__main__":
    asyncio.run(main())