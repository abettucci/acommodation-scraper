"""Telegram Bot webhook handler for accommodation scraper."""

import json
import re
import io
import csv
from typing import Optional, Tuple

from shared.config import get_config
from shared.telegram import (
    TelegramClient, 
    TelegramMessage, 
    create_inline_keyboard,
    format_place_message,
    format_places_summary,
)
from shared.places_client import GooglePlacesClient


# Command patterns
SEARCH_PATTERN = re.compile(
    r'^/buscar\s+(.+?)\s+en\s+(.+?)(?:\s+(\d+(?:\.\d+)?)\s*km)?$',
    re.IGNORECASE
)
HELP_TEXT = """
🏨 <b>Accommodation Scraper Bot</b>

Busca hoteles, hostels y alojamientos usando Google Places.

<b>Comandos:</b>

/buscar [tipo] en [ciudad] [radio]km
  Busca alojamientos en una zona
  
  Ejemplos:
  • <code>/buscar hoteles en Mendoza 10km</code>
  • <code>/buscar hostels en Palermo, Buenos Aires 3km</code>
  • <code>/buscar alojamientos en Bariloche 5km</code>

/ayuda - Muestra este mensaje

<b>Tips:</b>
• El radio es opcional (default: 10km)
• Máximo 20 resultados por búsqueda
• Los resultados incluyen rating, precio y links
"""


def lambda_handler(event: dict, context) -> dict:
    """Handle incoming Telegram webhook."""
    print(f"Event: {json.dumps(event)}")
    
    # Parse body
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)
    
    # Get config
    config = get_config()
    
    # Initialize clients
    telegram = TelegramClient(config.telegram_token)
    
    try:
        # Parse message
        message = TelegramMessage.from_update(body)
        if not message:
            return response(200, {"ok": True})
        
        chat_id = message.chat_id
        text = message.text.strip()
        
        # Handle commands
        if text.startswith("/start") or text.startswith("/ayuda") or text.startswith("/help"):
            telegram.send_message(chat_id, HELP_TEXT)
        
        elif text.startswith("/buscar"):
            handle_search(telegram, config, chat_id, text)
        
        else:
            # Unknown command
            telegram.send_message(
                chat_id,
                "❓ Comando no reconocido. Usa /ayuda para ver los comandos disponibles."
            )
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            telegram.send_message(
                message.chat_id if message else 0,
                f"❌ Error: {str(e)}"
            )
        except:
            pass
    
    finally:
        telegram.close()
    
    return response(200, {"ok": True})


def handle_search(telegram: TelegramClient, config, chat_id: int, text: str):
    """Handle /buscar command."""
    
    # Parse command
    match = SEARCH_PATTERN.match(text)
    if not match:
        telegram.send_message(
            chat_id,
            "❌ Formato incorrecto.\n\n"
            "Uso: <code>/buscar [tipo] en [ciudad] [radio]km</code>\n\n"
            "Ejemplo: <code>/buscar hoteles en Mendoza 10km</code>"
        )
        return
    
    query_type = match.group(1).strip()
    location = match.group(2).strip()
    radius_str = match.group(3)
    radius = float(radius_str) if radius_str else 10.0
    
    # Limit radius
    radius = min(radius, 50.0)
    
    # Send "searching" message
    telegram.send_message(
        chat_id,
        f"🔍 Buscando <b>{query_type}</b> en <b>{location}</b> (radio: {radius} km)...",
    )
    
    # Search places
    places_client = GooglePlacesClient(config.google_api_key)
    
    try:
        places, coords = places_client.search_with_location(
            query=query_type,
            location_name=location,
            radius_km=radius,
            max_results=20,
        )
        
        if not places:
            telegram.send_message(
                chat_id,
                f"❌ No se encontraron {query_type} en {location}"
            )
            return
        
        # Send summary
        places_dicts = [p.to_dict() for p in places]
        summary = format_places_summary(places_dicts, location, radius)
        telegram.send_message(chat_id, summary)
        
        # Send each place (max 10 to avoid spam)
        for place in places[:10]:
            place_dict = place.to_dict()
            msg = format_place_message(place_dict)
            telegram.send_message(chat_id, msg, disable_web_page_preview=True)
        
        if len(places) > 10:
            telegram.send_message(
                chat_id,
                f"📋 Mostrando 10 de {len(places)} resultados.\n"
                "Usa el botón de abajo para descargar todos como CSV.",
                reply_markup=create_inline_keyboard([
                    [{"text": "📥 Descargar CSV", "callback_data": f"csv:{location}:{radius}:{query_type}"}]
                ])
            )
        
        # Generate and send CSV
        csv_data = generate_csv(places_dicts)
        filename = f"alojamientos_{location.replace(' ', '_').replace(',', '')}_{int(radius)}km.csv"
        
        telegram.send_document(
            chat_id,
            csv_data.encode('utf-8-sig'),
            filename,
            caption=f"📊 {len(places)} alojamientos encontrados"
        )
        
    finally:
        places_client.close()


def generate_csv(places: list) -> str:
    """Generate CSV string from places."""
    if not places:
        return ""
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=places[0].keys())
    writer.writeheader()
    writer.writerows(places)
    
    return output.getvalue()


def response(status_code: int, body: dict) -> dict:
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }
