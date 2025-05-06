"""Fetch contractors via Google Places NearbySearch."""
from __future__ import annotations
import os
import requests
import logging
from typing import List, Dict, Any

_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "") # Default to empty string
_ENDPOINT = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

log = logging.getLogger(__name__)

def nearby_contractors(lat: float, lng: float, radius_m: int = 40000, 
                         keywords: str = "general contractor|plumber|roofer|electrician|hvac") -> List[Dict[str, Any]]:
    """Fetches nearby contractors using Google Places API.

    Args:
        lat: Latitude of the search center.
        lng: Longitude of the search center.
        radius_m: Search radius in meters (default: 40000m ~ 25 miles).
        keywords: Pipe-separated keywords for contractor types (default includes common trades).

    Returns:
        A list of contractor results (dictionaries) from the API, or an empty list if API key is missing or an error occurs.
    """
    if not _API_KEY:
        log.warning("GOOGLE_PLACES_API_KEY not set. Skipping NearbySearch.")
        return [] # Return empty list if API key is missing (e.g., in tests/CI)
    
    # Ensure keywords are URL-friendly (though requests handles basic encoding)
    # '|' is generally safe in query params but explicit encoding can be safer if needed.
    params = {
        "location": f"{lat},{lng}",
        "radius": str(radius_m), # API expects string for radius
        "keyword": keywords, # Use the provided/default keywords
        "key": _API_KEY,
        "rankby": "prominence" # Use prominence ranking within the radius
        # Consider adding 'type': 'point_of_interest' or specific business types if needed
    }
    
    log.info(f"Querying Google Places NearbySearch: lat={lat}, lng={lng}, radius={radius_m}m")
    
    try:
        resp = requests.get(_ENDPOINT, params=params, timeout=10) # 10-second timeout
        resp.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        data = resp.json()
        results = data.get("results", [])
        status = data.get("status")

        if status != "OK" and status != "ZERO_RESULTS":
             log.error(f"Google Places API error. Status: {status}. Error message: {data.get('error_message')}")
             # Optionally return empty or raise a custom exception based on status
             # For now, returning empty list on non-OK status other than ZERO_RESULTS
             return []
             
        log.info(f"Google Places NearbySearch returned {len(results)} results with status: {status}")
        return results

    except requests.exceptions.RequestException as e:
        log.error(f"Error during Google Places API request: {e}")
        return [] # Return empty list on request errors
    except Exception as e:
        log.error(f"An unexpected error occurred processing Google Places response: {e}")
        return [] # Return empty list on other unexpected errors
