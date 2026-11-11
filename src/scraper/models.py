"""Data models for Google Places API responses."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PriceLevel(str, Enum):
    """Price level enumeration from Google Places API."""
    UNSPECIFIED = "PRICE_LEVEL_UNSPECIFIED"
    FREE = "PRICE_LEVEL_FREE"
    INEXPENSIVE = "PRICE_LEVEL_INEXPENSIVE"
    MODERATE = "PRICE_LEVEL_MODERATE"
    EXPENSIVE = "PRICE_LEVEL_EXPENSIVE"
    VERY_EXPENSIVE = "PRICE_LEVEL_VERY_EXPENSIVE"
    
    @classmethod
    def from_api(cls, value: Optional[str]) -> Optional["PriceLevel"]:
        """Convert API string to PriceLevel enum."""
        if not value:
            return None
        try:
            return cls(value)
        except ValueError:
            return None
    
    def to_display(self) -> str:
        """Convert to human-readable format."""
        mapping = {
            self.UNSPECIFIED: "N/A",
            self.FREE: "Free",
            self.INEXPENSIVE: "$",
            self.MODERATE: "$$",
            self.EXPENSIVE: "$$$",
            self.VERY_EXPENSIVE: "$$$$",
        }
        return mapping.get(self, "N/A")


@dataclass
class Review:
    """A single review for a place."""
    author_name: str
    rating: float
    text: str
    relative_time: str
    
    @classmethod
    def from_api(cls, data: dict) -> "Review":
        """Create Review from API response."""
        return cls(
            author_name=data.get("authorAttribution", {}).get("displayName", "Anonymous"),
            rating=data.get("rating", 0),
            text=data.get("text", {}).get("text", ""),
            relative_time=data.get("relativePublishTimeDescription", ""),
        )


@dataclass
class Location:
    """Geographic coordinates."""
    latitude: float
    longitude: float
    
    @classmethod
    def from_api(cls, data: dict) -> Optional["Location"]:
        """Create Location from API response."""
        if not data:
            return None
        return cls(
            latitude=data.get("latitude", 0),
            longitude=data.get("longitude", 0),
        )


@dataclass
class Place:
    """Represents an accommodation place from Google Places API."""
    id: str
    name: str
    address: str
    location: Optional[Location] = None
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[PriceLevel] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    primary_type: Optional[str] = None
    reviews: list[Review] = field(default_factory=list)
    
    @classmethod
    def from_api(cls, data: dict) -> "Place":
        """Create Place from API response."""
        # Extract display name
        display_name = data.get("displayName", {})
        name = display_name.get("text", "") if isinstance(display_name, dict) else str(display_name)
        
        # Extract reviews
        reviews_data = data.get("reviews", [])
        reviews = [Review.from_api(r) for r in reviews_data[:5]]  # Limit to top 5
        
        return cls(
            id=data.get("id", ""),
            name=name,
            address=data.get("formattedAddress", ""),
            location=Location.from_api(data.get("location")),
            rating=data.get("rating"),
            user_rating_count=data.get("userRatingCount"),
            price_level=PriceLevel.from_api(data.get("priceLevel")),
            phone=data.get("internationalPhoneNumber"),
            website=data.get("websiteUri"),
            google_maps_url=data.get("googleMapsUri"),
            primary_type=data.get("primaryType"),
            reviews=reviews,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        top_review = self.reviews[0].text if self.reviews else ""
        return {
            "name": self.name,
            "address": self.address,
            "lat": self.location.latitude if self.location else None,
            "lng": self.location.longitude if self.location else None,
            "rating": self.rating,
            "reviews_count": self.user_rating_count,
            "price_level": self.price_level.to_display() if self.price_level else None,
            "phone": self.phone,
            "website": self.website,
            "google_maps_url": self.google_maps_url,
            "type": self.primary_type,
            "top_review": top_review[:500] if top_review else "",  # Truncate long reviews
        }


@dataclass
class SearchResult:
    """Result of a places search."""
    places: list[Place]
    next_page_token: Optional[str] = None
    
    @classmethod
    def from_api(cls, data: dict) -> "SearchResult":
        """Create SearchResult from API response."""
        places_data = data.get("places", [])
        places = [Place.from_api(p) for p in places_data]
        return cls(
            places=places,
            next_page_token=data.get("nextPageToken"),
        )


# Field masks for different pricing tiers
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
