"""Homeowner Agent with integrated memory and slot filling capabilities."""

import logging
import json
import re
import datetime
from typing import Dict, Any, List, Optional, Callable
import asyncio

from supabase import Client
from google.adk.conversation import Agent, Response, Message, ConversationHandler

from src.memory.persistent_memory import PersistentMemory
from src.slot_filler.slot_filler_factory import SlotFillerFactory, SlotFiller
from src.agents.memory_enabled_agent import MemoryEnabledAgent

logger = logging.getLogger(__name__)


class HomeownerAgent(MemoryEnabledAgent):
    """Agent for homeowners with memory persistence and slot filling."""

    def __init__(self, db: Client):
        """Initialize with database connection."""
        super().__init__(db)
        self.project_types = [
            "bathroom", "kitchen", "bedroom", "living room", "basement", 
            "attic", "garage", "deck", "patio", "landscaping", "roofing",
            "flooring", "painting", "plumbing", "electrical", "hvac",
            "windows", "doors", "siding", "insulation", "drywall",
            "general remodeling"
        ]
        self.timeline_options = [
            "immediately", "within 1 month", "1-3 months", 
            "3-6 months", "6-12 months", "more than a year"
        ]
        self.budget_options = [
            "under $5,000", "$5,000-$15,000", "$15,000-$30,000", 
            "$30,000-$50,000", "$50,000-$100,000", "$100,000+"
        ]
        self.default_required_slots = ["location", "project_type"]
        self.default_optional_slots = ["timeline", "budget", "size", "style_preference"]
    
    async def _process_message_with_memory(self, message: Message, user_id: str, conversation_id: str) -> str:
        """Process a message with memory and slot filling."""
        # Create text extractors
        text_extractors = {
            "location": self._extract_location,
            "project_type": self._extract_project_type,
            "timeline": self._extract_timeline,
            "budget": self._extract_budget
        }
        
        # Create vision extractors
        vision_extractors = {
            "project_type": self._extract_project_type_from_image,
            "style_preference": self._extract_style_from_image
        }
        
        # Process with slot filling
        slot_result = await self._process_with_slot_filling(
            message,
            user_id,
            conversation_id,
            self.default_required_slots,
            self.default_optional_slots,
            text_extractors,
            vision_extractors,
            self._handle_all_slots_filled
        )
        
        # Generate response based on slot filling status
        if slot_result["all_required_slots_filled"]:
            return await self._generate_response_with_all_slots(slot_result)
        else:
            return await self._generate_response_for_missing_slots(slot_result)
    
    async def _handle_all_slots_filled(self, slot_filler: SlotFiller) -> None:
        """Handle when all required slots are filled."""
        # Check for optional slots that could be prompted next
        filled_slots = slot_filler.get_filled_slots()
        
        # If we have project type and location but no budget, we might want to suggest ranges
        if "project_type" in filled_slots and "location" in filled_slots and "budget" not in filled_slots:
            # This is where we could look up typical budget ranges for this project type and location
            # For now, just suggesting all budget options
            logger.info(f"All required slots filled, suggesting budget options")
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from message text."""
        # Simple pattern matching for location
        # In a real implementation, this would use more sophisticated NER or geocoding
        location_patterns = [
            r"in\s+([A-Za-z\s]+(?:,\s*[A-Za-z]{2})?)\b",
            r"(?:from|at|near)\s+([A-Za-z\s]+(?:,\s*[A-Za-z]{2})?)\b",
            r"([A-Za-z\s]+)\s+area\b"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_project_type(self, text: str) -> Optional[str]:
        """Extract project type from message text."""
        text_lower = text.lower()
        
        # Check if any of our project types are directly mentioned
        for project_type in self.project_types:
            if project_type in text_lower:
                return project_type
        
        # Look for phrases suggesting a project type
        if any(term in text_lower for term in ["bathroom", "shower", "tub", "toilet", "bath"]):
            return "bathroom"
        elif any(term in text_lower for term in ["kitchen", "cabinets", "countertop", "appliance"]):
            return "kitchen"
        elif any(term in text_lower for term in ["bedroom", "master bedroom", "guest room"]):
            return "bedroom"
        elif any(term in text_lower for term in ["living room", "family room", "sitting area"]):
            return "living room"
        
        # No clear project type found
        return None
    
    def _extract_timeline(self, text: str) -> Optional[str]:
        """Extract project timeline from message text."""
        text_lower = text.lower()
        
        # Look for direct mentions of timeline options
        for timeline in self.timeline_options:
            if timeline in text_lower:
                return timeline
        
        # Look for phrases suggesting a timeline
        if any(term in text_lower for term in ["asap", "right away", "immediately", "urgent"]):
            return "immediately"
        elif any(term in text_lower for term in ["soon", "next month", "within a month"]):
            return "within 1 month"
        elif any(term in text_lower for term in ["a few months", "couple months", "2-3 months"]):
            return "1-3 months"
        elif any(term in text_lower for term in ["later this year", "second half of the year", "fall", "winter"]):
            return "3-6 months"
        elif any(term in text_lower for term in ["next year", "in a year", "12 months"]):
            return "6-12 months"
        elif any(term in text_lower for term in ["long term", "future", "someday", "eventually"]):
            return "more than a year"
        
        return None
    
    def _extract_budget(self, text: str) -> Optional[str]:
        """Extract budget from message text."""
        text_lower = text.lower()
        
        # Look for direct mentions of budget options
        for budget in self.budget_options:
            if budget in text_lower:
                return budget
        
        # Look for patterns indicating budget ranges
        budget_patterns = [
            (r"under\s+\$?5[k,\s]*(?:thousand|k)?\b", "under $5,000"),
            (r"less than\s+\$?5[k,\s]*(?:thousand|k)?\b", "under $5,000"),
            (r"\$?5[k,\s]*(?:thousand|k)?\s*-\s*\$?15[k,\s]*(?:thousand|k)?\b", "$5,000-$15,000"),
            (r"\$?15[k,\s]*(?:thousand|k)?\s*-\s*\$?30[k,\s]*(?:thousand|k)?\b", "$15,000-$30,000"),
            (r"\$?30[k,\s]*(?:thousand|k)?\s*-\s*\$?50[k,\s]*(?:thousand|k)?\b", "$30,000-$50,000"),
            (r"\$?50[k,\s]*(?:thousand|k)?\s*-\s*\$?100[k,\s]*(?:thousand|k)?\b", "$50,000-$100,000"),
            (r"over\s+\$?100[k,\s]*(?:thousand|k)?\b", "$100,000+"),
            (r"more than\s+\$?100[k,\s]*(?:thousand|k)?\b", "$100,000+")
        ]
        
        for pattern, budget_range in budget_patterns:
            if re.search(pattern, text_lower):
                return budget_range
        
        return None
    
    def _extract_project_type_from_image(self, image_data: Dict[str, Any]) -> Optional[str]:
        """Extract project type from image data."""
        # In a real implementation, this would use computer vision
        # For now, we'll simply check if the URL has any hints
        url = image_data.get("url", "").lower()
        
        for project_type in self.project_types:
            if project_type in url:
                return project_type
        
        # Check for common room types in URL
        if any(term in url for term in ["bath", "shower", "toilet"]):
            return "bathroom"
        elif any(term in url for term in ["kitchen", "countertop", "cabinet"]):
            return "kitchen"
        
        # If no type detected, just return None
        return None
    
    def _extract_style_from_image(self, image_data: Dict[str, Any]) -> Optional[str]:
        """Extract style preference from image data."""
        # In a real implementation, this would use computer vision
        # For now, we'll simply check if the URL has any hints
        url = image_data.get("url", "").lower()
        
        styles = [
            "modern", "contemporary", "traditional", "rustic", 
            "farmhouse", "industrial", "coastal", "bohemian",
            "minimalist", "scandinavian", "mid-century", "eclectic"
        ]
        
        for style in styles:
            if style in url:
                return style
        
        # If no style detected, just return None
        return None
    
    async def _generate_response_with_all_slots(self, slot_result: Dict[str, Any]) -> str:
        """Generate response when all required slots are filled."""
        slot_filler = slot_result["slot_filler"]
        filled_slots = slot_filler.get_filled_slots()
        
        # Build response
        response_parts = []
        
        # Reference what was learned in this interaction
        if slot_result["extracted_from_text"]:
            extracted = slot_result["extracted_from_text"]
            for slot_name, value in extracted.items():
                if slot_name == "location":
                    response_parts.append(f"I see you're in {value}.")
                elif slot_name == "project_type":
                    response_parts.append(f"You're looking to renovate your {value}.")
                elif slot_name == "timeline":
                    response_parts.append(f"You want to get started {value}.")
                elif slot_name == "budget":
                    response_parts.append(f"Your budget is {value}.")
        
        # Reference what was extracted from images
        if slot_result["extracted_from_vision"]:
            extracted = slot_result["extracted_from_vision"]
            for slot_name, value in extracted.items():
                if slot_name == "project_type":
                    response_parts.append(f"Based on your image, I can see you're working on a {value}.")
                elif slot_name == "style_preference":
                    response_parts.append(f"I notice you like {value} style designs.")
        
        # Summarize what we know
        response_parts.append("\n\nBased on what you've told me, here's what I know so far:")
        
        if "location" in filled_slots:
            response_parts.append(f"- Location: {filled_slots['location']}")
        if "project_type" in filled_slots:
            response_parts.append(f"- Project: {filled_slots['project_type']} renovation")
        if "timeline" in filled_slots:
            response_parts.append(f"- Timeline: {filled_slots['timeline']}")
        if "budget" in filled_slots:
            response_parts.append(f"- Budget: {filled_slots['budget']}")
        if "style_preference" in filled_slots:
            response_parts.append(f"- Style preference: {filled_slots['style_preference']}")
        
        # Ask for any missing optional slots
        missing_optional = [s for s in self.default_optional_slots if s not in filled_slots]
        if missing_optional:
            response_parts.append("\nTo further customize your experience:")
            
            if "budget" in missing_optional:
                response_parts.append("- What's your approximate budget for this project?")
            if "timeline" in missing_optional:
                response_parts.append("- When are you looking to start this project?")
            if "style_preference" in missing_optional and "project_type" in filled_slots:
                response_parts.append(f"- Do you have any style preferences for your {filled_slots['project_type']}?")
            if "size" in missing_optional and "project_type" in filled_slots:
                response_parts.append(f"- What's the approximate size of your {filled_slots['project_type']}?")
        
        # Add next step information
        response_parts.append("\nI can help you find qualified contractors for your project and get competitive bids.")
        response_parts.append("Would you like me to create a project listing now?")
        
        return "\n".join(response_parts)
    
    async def _generate_response_for_missing_slots(self, slot_result: Dict[str, Any]) -> str:
        """Generate response when some required slots are missing."""
        slot_filler = slot_result["slot_filler"]
        filled_slots = slot_filler.get_filled_slots()
        missing_slots = slot_result["missing_slots"]
        
        # Build response
        response_parts = []
        
        # Thank for information provided
        if slot_result["extracted_from_text"] or slot_result["extracted_from_vision"]:
            response_parts.append("Thanks for sharing that information with me.")
            
            # Reference what was learned in this interaction
            if slot_result["extracted_from_text"]:
                extracted = slot_result["extracted_from_text"]
                for slot_name, value in extracted.items():
                    if slot_name == "location":
                        response_parts.append(f"I see you're in {value}.")
                    elif slot_name == "project_type":
                        response_parts.append(f"You're looking to renovate your {value}.")
            
            # Reference what was extracted from images
            if slot_result["extracted_from_vision"]:
                extracted = slot_result["extracted_from_vision"]
                for slot_name, value in extracted.items():
                    if slot_name == "project_type":
                        response_parts.append(f"Based on your image, I can see you're working on a {value}.")
        else:
            response_parts.append("I'm here to help with your home improvement project.")
        
        # Ask for missing required information
        response_parts.append("\nTo help you better, I need a few more details:")
        
        if "location" in missing_slots:
            response_parts.append("- Where are you located? (city or zip code)")
        
        if "project_type" in missing_slots:
            # If we have images but failed to extract project type, ask more specifically
            if slot_result["slot_filler"].state._multi_modal_context:
                response_parts.append("- What type of room or area are you looking to renovate in the image?")
            else:
                response_parts.append("- What type of home improvement project are you planning?")
                response_parts.append("  (e.g., bathroom, kitchen, basement, deck, etc.)")
        
        return "\n".join(response_parts)