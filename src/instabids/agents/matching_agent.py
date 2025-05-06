"""Deterministic rule-based MatchingAgent – Sprint 6.

Listens for 'bidcard.created' events and attempts to match contractors,
writing results to 'match_scores' and potentially seeding prospects
from Google Places.
"""
from __future__ import annotations
import logging
import math
import asyncio
from typing import List, Dict, Any, Tuple

# Assuming these imports are valid relative to the project structure
try:
    from instabids.data.supabase_client import create_client
    _sb = create_client()
except ImportError:
    logging.error("Failed to import or initialize Supabase client.")
    # Provide a dummy/mock client or raise if essential
    _sb = None # type: ignore

try:
    from instabids.tools import twilio_sms, sendgrid_mail # Not used directly in this agent yet, but maybe later
except ImportError:
    logging.warning("Twilio/SendGrid tools not found.")

try:
    from instabids.services import google_places
except ImportError:
    logging.error("Google Places service not found.")
    # Dummy service if needed
    class DummyGooglePlaces:
        def nearby_contractors(self, *args, **kwargs): return []
    google_places = DummyGooglePlaces() # type: ignore

try:
    from instabids.a2a_comm import on_envelope, send_envelope
except ImportError:
    logging.error("A2A communication module not found.")
    # Dummy decorators/functions if needed
    def on_envelope(event_name):
        def decorator(func):
            return func
        return decorator
    def send_envelope(event_name, payload): 
        logging.info(f"STUB: Sending A2A envelope: {event_name} with payload: {payload}")

log = logging.getLogger(__name__)
if not log.handlers:
     logging.basicConfig(level=logging.INFO) # Basic config if none exists

# ------------------ helpers -----------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates the great-circle distance between two points on Earth (in km)."""
    if None in [lat1, lng1, lat2, lng2]:
        log.warning("Cannot calculate distance with missing coordinates.")
        return float('inf') # Return infinity or a large number if coords are missing
        
    R = 6371 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    return distance

def _distance_score(km: float) -> float:
    """Calculates a score based on distance, linearly decreasing to 0 at 75km."""
    return max(0.0, 1 - km / 75)

def _geo_from_location(location: str | None) -> Tuple[float | None, float | None]:
    """Extracts lat, lng from a 'lat,lng' string. Returns (None, None) on failure."""
    if not location or "," not in location:
        return None, None
    try:
        lat, lng = map(float, location.strip().split(",", 1))
        # Basic validation for lat/lng ranges
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng
        else:
            log.warning(f"Invalid lat/lng values extracted: {lat}, {lng}")
            return None, None
    except ValueError:
        log.warning(f"Could not parse lat,lng from location string: '{location}'")
        return None, None

# ------------------ main handler ------------------------

@on_envelope("bidcard.created")
async def handle_new_bidcard(evt: Dict[str, Any]) -> None:
    """Handles the 'bidcard.created' event to find matching contractors."""
    if not _sb:
        log.error("Supabase client not available. Cannot handle bidcard event.")
        return

    bid_id = evt.get("bid_card_id")
    if not bid_id:
        log.error("Missing 'bid_card_id' in event payload.")
        return

    log.info(f"Handling 'bidcard.created' event for bid_card_id: {bid_id}")

    try:
        # 1. Fetch BidCard details
        bid_resp = _sb.table("bid_cards").select("id, category, location, title").eq("id", bid_id).maybe_single().execute()
        if bid_resp.error or not bid_resp.data:
            log.error(f"Failed to fetch bid card {bid_id}: {bid_resp.error or 'Not found'}")
            return
        bid_row = bid_resp.data
        category = bid_row.get("category")
        location_str = bid_row.get("location")
        title = bid_row.get("title", "[Untitled Project]") # Get title for logging/outreach
        lat, lng = _geo_from_location(location_str)
        
        if not category:
             log.error(f"Bid card {bid_id} is missing a category. Cannot match.")
             return

        # 2. Call matching function (RPC)
        log.info(f"Calling RPC 'match_contractors_rule' for category '{category}' at location {lat},{lng}")
        match_resp = _sb.rpc(
            "match_contractors_rule", 
            {"p_category": category, "p_lat": lat, "p_lng": lng}
        ).execute()
        
        if match_resp.error:
            log.error(f"Error calling match_contractors_rule RPC: {match_resp.error}")
            contractors = []
        else:
            contractors = match_resp.data or []
            log.info(f"Found {len(contractors)} potential contractors via RPC.")

        # 3. Write results to match_scores table
        match_score_rows = []
        contractor_ids = []
        for row in contractors:
            contractor_id = row.get("id")
            score = row.get("score")
            if contractor_id and score is not None:
                 match_score_rows.append({
                     "bid_card_id": bid_id,
                     "contractor_id": contractor_id,
                     "score": score,
                     "status": "pending", # Initial status
                 })
                 contractor_ids.append(contractor_id)
        
        if match_score_rows:
            log.info(f"Inserting {len(match_score_rows)} rows into match_scores for bid {bid_id}")
            insert_resp = _sb.table("match_scores").insert(match_score_rows).execute()
            if insert_resp.error:
                 log.error(f"Failed to insert match scores: {insert_resp.error}")
                 # Decide how to proceed: maybe skip sending envelope? 
                 # For now, log error and continue.

        # 4. Send A2A envelope about the matches
        if contractor_ids:
            log.info(f"Sending 'matching.invited' envelope for bid {bid_id} with {len(contractor_ids)} contractors.")
            send_envelope("matching.invited", {"bid_card_id": bid_id, "contractor_ids": contractor_ids})
        else:
            log.info(f"No matching contractors found or saved for bid {bid_id}. Skipping 'matching.invited' envelope.")

        # ----------- Prospect Seeding --------------
        # Seed if coordinates exist and fewer than 6 DB matches found
        if lat is not None and lng is not None and len(contractors) < 6:
            log.info(f"Fewer than 6 DB matches ({len(contractors)}). Attempting Google Places prospect seeding.")
            try:
                prospects = google_places.nearby_contractors(lat, lng)
                log.info(f"Google Places returned {len(prospects)} prospects near {lat},{lng}.")
                
                prospects_to_insert = []
                outbox_items = []
                # Limit processing to first 10 prospects
                for p in prospects[:10]: 
                    place_id = p.get("place_id")
                    name = p.get("name")
                    phone = p.get("formatted_phone_number")
                    
                    if not place_id or not name:
                        log.warning(f"Skipping prospect due to missing place_id or name: {p}")
                        continue
                    
                    # Prepare for upsert into prospect_contractors
                    prospects_to_insert.append({
                        "place_id": place_id,
                        "name": name,
                        "phone": phone,
                        "raw_json": p, # Store the raw JSON response
                    })
                    
                    # Prepare for insert into prospect_outbox
                    outbox_items.append({
                        "prospect_id": place_id,
                        "bid_card_id": bid_id,
                        "channel": "sms", # Default channel
                        "payload": {"body": f"InstaBids invite for {title}"}, # Use bid title
                        "status": "pending", # Initial status
                    })
                
                if prospects_to_insert:
                    log.info(f"Upserting {len(prospects_to_insert)} prospects into prospect_contractors.")
                    upsert_resp = _sb.table("prospect_contractors").upsert(
                        prospects_to_insert, 
                        on_conflict="place_id"
                     ).execute()
                    if upsert_resp.error:
                        log.error(f"Failed to upsert prospects: {upsert_resp.error}")

                if outbox_items:
                    log.info(f"Inserting {len(outbox_items)} items into prospect_outbox.")
                    outbox_resp = _sb.table("prospect_outbox").insert(outbox_items).execute()
                    if outbox_resp.error:
                         log.error(f"Failed to insert prospect outbox items: {outbox_resp.error}")
                         
                log.info(f"Completed prospect seeding. Added {len(prospects_to_insert)} prospects and {len(outbox_items)} outbox items.")
                
            except Exception as e:
                log.exception("Error during Google Places prospect seeding:", exc_info=e)
        else:
            log.info(f"Skipping prospect seeding (Lat/Lng missing or >= 6 DB matches found). Lat: {lat}, Lng: {lng}, Matches: {len(contractors)}")

    except Exception as e:
        log.exception(f"Unhandled error handling 'bidcard.created' for {bid_id}:", exc_info=e)
        # Consider sending an error event or logging to an error tracking service

# Example of how this might be registered if using an event bus system
# event_bus.subscribe("bidcard.created", handle_new_bidcard)
