"""CSV export functionality for accommodation data."""

from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

from .models import Place


def export_to_csv(
    places: list[Place],
    output_path: Optional[str] = None,
    include_timestamp: bool = True,
) -> Path:
    """Export places to CSV file.
    
    Args:
        places: List of Place objects to export
        output_path: Output file path. If None, generates timestamped filename.
        include_timestamp: If True and output_path is None, adds timestamp to filename.
        
    Returns:
        Path to the created CSV file
    """
    if not places:
        raise ValueError("No places to export")
    
    # Generate output path if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if include_timestamp else ""
        filename = f"accommodations_{timestamp}.csv" if timestamp else "accommodations.csv"
        output_path = filename
    
    # Convert places to dictionaries
    data = [place.to_dict() for place in places]
    
    # Create DataFrame and export
    df = pd.DataFrame(data)
    
    # Reorder columns for better readability
    column_order = [
        "name",
        "address",
        "lat",
        "lng",
        "rating",
        "reviews_count",
        "price_level",
        "phone",
        "website",
        "google_maps_url",
        "type",
        "top_review",
    ]
    
    # Only include columns that exist
    columns = [col for col in column_order if col in df.columns]
    df = df[columns]
    
    # Export to CSV with utf-8-sig encoding (BOM) for Windows Excel compatibility
    output_file = Path(output_path)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    return output_file


def get_summary_stats(places: list[Place]) -> dict:
    """Get summary statistics for a list of places.
    
    Args:
        places: List of Place objects
        
    Returns:
        Dictionary with summary statistics
    """
    if not places:
        return {"total": 0}
    
    ratings = [p.rating for p in places if p.rating is not None]
    review_counts = [p.user_rating_count for p in places if p.user_rating_count is not None]
    
    # Count by type
    types = {}
    for place in places:
        place_type = place.primary_type or "unknown"
        types[place_type] = types.get(place_type, 0) + 1
    
    # Count by price level
    price_levels = {}
    for place in places:
        level = place.price_level.to_display() if place.price_level else "N/A"
        price_levels[level] = price_levels.get(level, 0) + 1
    
    return {
        "total": len(places),
        "avg_rating": sum(ratings) / len(ratings) if ratings else None,
        "min_rating": min(ratings) if ratings else None,
        "max_rating": max(ratings) if ratings else None,
        "total_reviews": sum(review_counts) if review_counts else 0,
        "types": types,
        "price_levels": price_levels,
    }
