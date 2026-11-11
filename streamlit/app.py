"""Streamlit app for Accommodation Scraper."""

import os
import io
import streamlit as st
import pandas as pd
from typing import Optional, Tuple, List
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Accommodation Scraper",
    page_icon="🏨",
    layout="wide",
)


# ============================================
# Google Places Client (simplified for Streamlit)
# ============================================

@dataclass
class Place:
    """Accommodation place."""
    name: str
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    price_level: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    place_type: Optional[str] = None
    top_review: Optional[str] = None


def search_places(
    api_key: str,
    query: str,
    location: Optional[str] = None,
    radius_km: float = 10.0,
    max_results: int = 20,
    min_rating: Optional[float] = None,
) -> Tuple[List[Place], Optional[Tuple[float, float]]]:
    """Search for places using Google Places API."""
    
    client = httpx.Client(timeout=30.0)
    coords = None
    
    try:
        # Geocode location if provided
        if location:
            geo_response = client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": location, "key": api_key}
            )
            geo_data = geo_response.json()
            
            if geo_data.get("status") == "OK" and geo_data.get("results"):
                loc = geo_data["results"][0]["geometry"]["location"]
                coords = (loc["lat"], loc["lng"])
        
        # Search places
        fields = [
            "places.id", "places.displayName", "places.formattedAddress",
            "places.location", "places.googleMapsUri", "places.primaryType",
            "places.rating", "places.userRatingCount", "places.priceLevel",
            "places.internationalPhoneNumber", "places.websiteUri", "places.reviews",
        ]
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": ",".join(fields),
        }
        
        body = {
            "textQuery": query,
            "languageCode": "es",
            "pageSize": min(max_results, 20),
        }
        
        if coords:
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": coords[0], "longitude": coords[1]},
                    "radius": radius_km * 1000,
                }
            }
        
        response = client.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        
        # Parse results
        places = []
        price_map = {
            "PRICE_LEVEL_FREE": "Gratis",
            "PRICE_LEVEL_INEXPENSIVE": "$",
            "PRICE_LEVEL_MODERATE": "$$",
            "PRICE_LEVEL_EXPENSIVE": "$$$",
            "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
        }
        
        for p in response.json().get("places", []):
            display_name = p.get("displayName", {})
            name = display_name.get("text", "") if isinstance(display_name, dict) else str(display_name)
            
            location_data = p.get("location", {})
            
            reviews = p.get("reviews", [])
            top_review = None
            if reviews:
                review_text = reviews[0].get("text", {})
                top_review = review_text.get("text", "") if isinstance(review_text, dict) else ""
            
            rating = p.get("rating")
            
            # Apply rating filter
            if min_rating and (not rating or rating < min_rating):
                continue
            
            place = Place(
                name=name,
                address=p.get("formattedAddress", ""),
                lat=location_data.get("latitude"),
                lng=location_data.get("longitude"),
                rating=rating,
                reviews_count=p.get("userRatingCount"),
                price_level=price_map.get(p.get("priceLevel")),
                phone=p.get("internationalPhoneNumber"),
                website=p.get("websiteUri"),
                google_maps_url=p.get("googleMapsUri"),
                place_type=p.get("primaryType", "").replace("_", " ").title(),
                top_review=top_review[:200] if top_review else None,
            )
            places.append(place)
        
        return places, coords
        
    finally:
        client.close()


def places_to_dataframe(places: List[Place]) -> pd.DataFrame:
    """Convert places to DataFrame."""
    data = []
    for p in places:
        data.append({
            "Nombre": p.name,
            "Dirección": p.address,
            "Rating": p.rating,
            "Reviews": p.reviews_count,
            "Precio": p.price_level,
            "Teléfono": p.phone,
            "Website": p.website,
            "Google Maps": p.google_maps_url,
            "Tipo": p.place_type,
            "Lat": p.lat,
            "Lng": p.lng,
        })
    return pd.DataFrame(data)


# ============================================
# Streamlit UI
# ============================================

def main():
    st.title("🏨 Accommodation Scraper")
    st.markdown("Busca hoteles, hostels y alojamientos usando Google Places API")
    
    # Sidebar for API key
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        api_key = st.text_input(
            "Google Places API Key",
            type="password",
            value=os.getenv("GOOGLE_PLACES_API_KEY", ""),
            help="Obtené tu API key en Google Cloud Console"
        )
        
        if not api_key:
            st.warning("⚠️ Ingresá tu API key para buscar")
        
        st.markdown("---")
        st.markdown("""
        **Cómo obtener API Key:**
        1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
        2. Crear proyecto
        3. Habilitar Places API (New)
        4. Crear API Key
        """)
    
    # Main search form
    col1, col2 = st.columns([2, 1])
    
    with col1:
        query = st.text_input(
            "🔍 Tipo de alojamiento",
            placeholder="hoteles, hostels, apartamentos...",
            value="hoteles"
        )
    
    with col2:
        location = st.text_input(
            "📍 Ubicación",
            placeholder="Ciudad o dirección",
            value="Buenos Aires, Argentina"
        )
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        radius = st.slider(
            "📏 Radio (km)",
            min_value=1,
            max_value=50,
            value=10,
            help="Radio de búsqueda alrededor de la ubicación"
        )
    
    with col4:
        max_results = st.slider(
            "📊 Máx. resultados",
            min_value=5,
            max_value=20,
            value=20,
        )
    
    with col5:
        min_rating = st.slider(
            "⭐ Rating mínimo",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.5,
        )
        min_rating = min_rating if min_rating > 0 else None
    
    # Search button
    search_clicked = st.button("🔍 Buscar", type="primary", use_container_width=True)
    
    if search_clicked:
        if not api_key:
            st.error("❌ Por favor ingresá tu Google Places API Key en la barra lateral")
            return
        
        if not query:
            st.error("❌ Por favor ingresá un tipo de alojamiento")
            return
        
        with st.spinner(f"Buscando {query} en {location}..."):
            try:
                places, coords = search_places(
                    api_key=api_key,
                    query=query,
                    location=location,
                    radius_km=radius,
                    max_results=max_results,
                    min_rating=min_rating,
                )
                
                if not places:
                    st.warning(f"No se encontraron resultados para '{query}' en {location}")
                    return
                
                # Store results in session state
                st.session_state.places = places
                st.session_state.coords = coords
                st.session_state.search_params = {
                    "query": query,
                    "location": location,
                    "radius": radius,
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    st.error("❌ Error 403: API key inválida o sin permisos. Verificá que Places API (New) esté habilitada.")
                else:
                    st.error(f"❌ Error de API: {e}")
                return
            except Exception as e:
                st.error(f"❌ Error: {e}")
                return
    
    # Display results
    if "places" in st.session_state and st.session_state.places:
        places = st.session_state.places
        coords = st.session_state.coords
        params = st.session_state.search_params
        
        st.markdown("---")
        
        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Resultados", len(places))
        with col2:
            ratings = [p.rating for p in places if p.rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            st.metric("Rating promedio", f"{avg_rating:.1f} ⭐")
        with col3:
            if coords:
                st.metric("Coordenadas", f"{coords[0]:.4f}, {coords[1]:.4f}")
        
        # Map
        if coords and any(p.lat and p.lng for p in places):
            st.subheader("🗺️ Mapa")
            map_data = pd.DataFrame([
                {"lat": p.lat, "lon": p.lng}
                for p in places if p.lat and p.lng
            ])
            st.map(map_data)
        
        # Results table
        st.subheader("📋 Resultados")
        df = places_to_dataframe(places)
        
        # Make links clickable
        st.dataframe(
            df,
            column_config={
                "Website": st.column_config.LinkColumn("Website"),
                "Google Maps": st.column_config.LinkColumn("Google Maps"),
                "Rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
            },
            hide_index=True,
            use_container_width=True,
        )
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8-sig')
        filename = f"alojamientos_{params['location'].replace(' ', '_').replace(',', '')}_{params['radius']}km.csv"
        
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
        )
        
        # Individual cards
        st.subheader("🏨 Detalle")
        
        for i, place in enumerate(places):
            with st.expander(f"{place.name} {'⭐' * int(place.rating or 0)}", expanded=i < 3):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**📍 Dirección:** {place.address}")
                    if place.phone:
                        st.markdown(f"**📞 Teléfono:** {place.phone}")
                    if place.place_type:
                        st.markdown(f"**🏷️ Tipo:** {place.place_type}")
                    if place.top_review:
                        st.markdown(f"**💬 Review:** _{place.top_review}_")
                
                with col2:
                    if place.rating:
                        st.metric("Rating", f"{place.rating} ⭐")
                    if place.reviews_count:
                        st.metric("Reviews", place.reviews_count)
                    if place.price_level:
                        st.metric("Precio", place.price_level)
                
                # Links
                links = []
                if place.google_maps_url:
                    links.append(f"[Google Maps]({place.google_maps_url})")
                if place.website:
                    links.append(f"[Sitio Web]({place.website})")
                
                if links:
                    st.markdown(" | ".join(links))


if __name__ == "__main__":
    main()
