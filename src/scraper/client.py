"""Google Places API client for accommodation searches."""

import os
from pathlib import Path
from typing import Optional, Tuple

import httpx
from dotenv import load_dotenv

from .models import SearchResult, PRO_FIELDS, ENTERPRISE_FIELDS


class GooglePlacesClient:
    """Client for Google Places API (New) Text Search."""
    
    BASE_URL = "https://places.googleapis.com/v1/places:searchText"
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client with API key.
        
        Args:
            api_key: Google Places API key. If not provided, reads from 
                     GOOGLE_PLACES_API_KEY environment variable.
        """
        # Load .env from current directory or parent directories (Windows compatible)
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()  # Try default locations
        
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set GOOGLE_PLACES_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self._client = httpx.Client(timeout=30.0)
    
    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for an address or city name.
        
        Args:
            address: Address or city name (e.g., "Buenos Aires, Argentina")
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        response = self._client.get(
            self.GEOCODE_URL,
            params={
                "address": address,
                "key": self.api_key,
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return (location["lat"], location["lng"])
        
        return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def search(
        self,
        query: str,
        budget_mode: bool = False,
        max_results: int = 20,
        min_rating: Optional[float] = None,
        page_token: Optional[str] = None,
        language: str = "es",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> SearchResult:
        """Search for accommodations using Text Search API.
        
        Args:
            query: Search query (e.g., "hotels in Buenos Aires")
            budget_mode: If True, only request Pro-tier fields (cheaper)
            max_results: Maximum number of results per page (max 20)
            min_rating: Minimum rating filter (applied client-side)
            page_token: Token for pagination
            language: Language code for results
            latitude: Center latitude for location restriction
            longitude: Center longitude for location restriction
            radius_km: Radius in kilometers for location restriction
            
        Returns:
            SearchResult with list of places and optional next page token
        """
        # Select field mask based on budget mode
        fields = PRO_FIELDS if budget_mode else ENTERPRISE_FIELDS
        field_mask = ",".join(fields)
        
        # Build request headers
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }
        
        # Build request body
        body = {
            "textQuery": query,
            "languageCode": language,
            "pageSize": min(max_results, 20),  # API max is 20
        }
        
        # Add location restriction if coordinates and radius provided
        if latitude is not None and longitude is not None and radius_km is not None:
            body["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius_km * 1000,  # Convert km to meters
                }
            }
        
        # Add page token for pagination
        if page_token:
            body["pageToken"] = page_token
        
        # Make request
        response = self._client.post(
            self.BASE_URL,
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        
        # Parse response
        result = SearchResult.from_api(response.json())
        
        # Apply client-side rating filter if specified
        if min_rating is not None:
            result.places = [
                p for p in result.places 
                if p.rating is not None and p.rating >= min_rating
            ]
        
        return result
    
    def search_all(
        self,
        query: str,
        budget_mode: bool = False,
        max_results: int = 60,
        min_rating: Optional[float] = None,
        language: str = "es",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        location_name: Optional[str] = None,
    ) -> list:
        """Search and paginate through all results.
        
        Args:
            query: Search query
            budget_mode: If True, only request Pro-tier fields
            max_results: Maximum total results to fetch (max ~60 from API)
            min_rating: Minimum rating filter
            language: Language code for results
            latitude: Center latitude for location restriction
            longitude: Center longitude for location restriction
            radius_km: Radius in kilometers for location restriction
            location_name: City/address name to geocode (alternative to lat/lng)
            
        Returns:
            List of all Place objects found
        """
        # If location_name provided, geocode it to get coordinates
        if location_name and (latitude is None or longitude is None):
            coords = self.geocode(location_name)
            if coords:
                latitude, longitude = coords
        
        all_places = []
        page_token = None
        
        while len(all_places) < max_results:
            result = self.search(
                query=query,
                budget_mode=budget_mode,
                max_results=min(20, max_results - len(all_places)),
                min_rating=min_rating,
                page_token=page_token,
                language=language,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
            )
            
            all_places.extend(result.places)
            
            # Check if there are more pages
            if not result.next_page_token:
                break
            
            page_token = result.next_page_token
        
        return all_places[:max_results]


class GooglePlacesError(Exception):
    """Custom exception for Google Places API errors."""
    pass
