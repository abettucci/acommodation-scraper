"""Google Places API client for Lambda functions."""

from typing import Optional, Tuple, List
from dataclasses import dataclass, field
import httpx


@dataclass
class Location:
    """Geographic coordinates."""
    latitude: float
    longitude: float


@dataclass
class Place:
    """Accommodation place from Google Places API."""
    id: str
    name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    primary_type: Optional[str] = None
    top_review: Optional[str] = None
    
    @classmethod
    def from_api(cls, data: dict) -> "Place":
        """Create Place from API response."""
        display_name = data.get("displayName", {})
        name = display_name.get("text", "") if isinstance(display_name, dict) else str(display_name)
        
        location = data.get("location", {})
        
        # Get top review
        reviews = data.get("reviews", [])
        top_review = None
        if reviews:
            review_text = reviews[0].get("text", {})
            top_review = review_text.get("text", "") if isinstance(review_text, dict) else ""
        
        # Map price level
        price_map = {
            "PRICE_LEVEL_FREE": "Gratis",
            "PRICE_LEVEL_INEXPENSIVE": "$",
            "PRICE_LEVEL_MODERATE": "$$",
            "PRICE_LEVEL_EXPENSIVE": "$$$",
            "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
        }
        price_level = price_map.get(data.get("priceLevel"), None)
        
        return cls(
            id=data.get("id", ""),
            name=name,
            address=data.get("formattedAddress", ""),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            rating=data.get("rating"),
            user_rating_count=data.get("userRatingCount"),
            price_level=price_level,
            phone=data.get("internationalPhoneNumber"),
            website=data.get("websiteUri"),
            google_maps_url=data.get("googleMapsUri"),
            primary_type=data.get("primaryType"),
            top_review=top_review[:200] if top_review else None,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "address": self.address,
            "lat": self.latitude,
            "lng": self.longitude,
            "rating": self.rating,
            "reviews_count": self.user_rating_count,
            "price_level": self.price_level,
            "phone": self.phone,
            "website": self.website,
            "google_maps_url": self.google_maps_url,
            "type": self.primary_type,
            "top_review": self.top_review,
        }


# Field masks for API requests
PRO_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.googleMapsUri",
    "places.primaryType",
]

ENTERPRISE_FIELDS = PRO_FIELDS + [
    "places.rating",
    "places.userRatingCount",
    "places.priceLevel",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.reviews",
]


class GooglePlacesClient:
    """Client for Google Places API (New)."""
    
    BASE_URL = "https://places.googleapis.com/v1/places:searchText"
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        self._client = httpx.Client(timeout=30.0)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()
    
    def close(self):
        """Close HTTP client."""
        self._client.close()
    
    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for an address."""
        response = self._client.get(
            self.GEOCODE_URL,
            params={"address": address, "key": self.api_key}
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return (loc["lat"], loc["lng"])
        return None
    
    def search(
        self,
        query: str,
        budget_mode: bool = False,
        max_results: int = 20,
        min_rating: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        language: str = "es",
    ) -> List[Place]:
        """Search for places."""
        fields = PRO_FIELDS if budget_mode else ENTERPRISE_FIELDS
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join(fields),
        }
        
        body = {
            "textQuery": query,
            "languageCode": language,
            "pageSize": min(max_results, 20),
        }
        
        # Add location bias if provided
        if latitude and longitude and radius_km:
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_km * 1000,
                }
            }
        
        response = self._client.post(self.BASE_URL, headers=headers, json=body)
        response.raise_for_status()
        
        places_data = response.json().get("places", [])
        places = [Place.from_api(p) for p in places_data]
        
        # Apply rating filter
        if min_rating:
            places = [p for p in places if p.rating and p.rating >= min_rating]
        
        return places
    
    def search_with_location(
        self,
        query: str,
        location_name: str,
        radius_km: float,
        max_results: int = 20,
        min_rating: Optional[float] = None,
        budget_mode: bool = False,
    ) -> Tuple[List[Place], Optional[Tuple[float, float]]]:
        """Search with location name (geocodes automatically)."""
        coords = self.geocode(location_name)
        
        lat, lng = coords if coords else (None, None)
        
        places = self.search(
            query=query,
            budget_mode=budget_mode,
            max_results=max_results,
            min_rating=min_rating,
            latitude=lat,
            longitude=lng,
            radius_km=radius_km if coords else None,
        )
        
        return places, coords
