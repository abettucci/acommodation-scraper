"""Telegram Bot client for Lambda functions."""

import json
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class TelegramUser:
    """Telegram user info."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None


@dataclass
class TelegramMessage:
    """Telegram message."""
    message_id: int
    chat_id: int
    text: str
    user: TelegramUser
    
    @classmethod
    def from_update(cls, update: dict) -> Optional["TelegramMessage"]:
        """Parse message from Telegram update."""
        message = update.get("message") or update.get("callback_query", {}).get("message")
        if not message:
            return None
        
        user_data = message.get("from", {})
        user = TelegramUser(
            id=user_data.get("id", 0),
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name"),
            username=user_data.get("username"),
        )
        
        return cls(
            message_id=message.get("message_id", 0),
            chat_id=message.get("chat", {}).get("id", 0),
            text=message.get("text", ""),
            user=user,
        )


class TelegramClient:
    """Client for Telegram Bot API."""
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(self, token: str):
        """Initialize with bot token."""
        self.token = token
        self.base_url = self.BASE_URL.format(token=token)
        self._client = httpx.Client(timeout=30.0)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()
    
    def close(self):
        """Close HTTP client."""
        self._client.close()
    
    def _request(self, method: str, **params) -> dict:
        """Make request to Telegram API."""
        url = f"{self.base_url}/{method}"
        response = self._client.post(url, json=params)
        response.raise_for_status()
        return response.json()
    
    def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None,
        disable_web_page_preview: bool = False,
    ) -> dict:
        """Send text message."""
        params = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            params["reply_markup"] = reply_markup
        
        return self._request("sendMessage", **params)
    
    def send_document(
        self,
        chat_id: int,
        document: bytes,
        filename: str,
        caption: Optional[str] = None,
    ) -> dict:
        """Send document (file)."""
        url = f"{self.base_url}/sendDocument"
        files = {"document": (filename, document)}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        
        response = self._client.post(url, data=data, files=files)
        response.raise_for_status()
        return response.json()
    
    def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> dict:
        """Answer callback query from inline keyboard."""
        params = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text:
            params["text"] = text
        
        return self._request("answerCallbackQuery", **params)
    
    def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None,
    ) -> dict:
        """Edit existing message."""
        params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            params["reply_markup"] = reply_markup
        
        return self._request("editMessageText", **params)
    
    def set_webhook(self, url: str) -> dict:
        """Set webhook URL."""
        return self._request("setWebhook", url=url)
    
    def delete_webhook(self) -> dict:
        """Delete webhook."""
        return self._request("deleteWebhook")
    
    def get_webhook_info(self) -> dict:
        """Get webhook info."""
        return self._request("getWebhookInfo")


def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> dict:
    """Create inline keyboard markup.
    
    Example:
        buttons = [
            [{"text": "Option 1", "callback_data": "opt1"}],
            [{"text": "Option 2", "callback_data": "opt2"}],
        ]
    """
    return {"inline_keyboard": buttons}


def format_place_message(place: dict) -> str:
    """Format a place as HTML message."""
    lines = []
    
    # Name and type
    name = place.get("name", "Sin nombre")
    place_type = place.get("type", "").replace("_", " ").title()
    lines.append(f"<b>{name}</b>")
    if place_type:
        lines.append(f"📍 {place_type}")
    
    # Rating
    rating = place.get("rating")
    reviews = place.get("reviews_count")
    if rating:
        stars = "⭐" * int(rating)
        rating_text = f"{stars} {rating}"
        if reviews:
            rating_text += f" ({reviews} reviews)"
        lines.append(rating_text)
    
    # Price
    price = place.get("price_level")
    if price:
        lines.append(f"💰 {price}")
    
    # Address
    address = place.get("address")
    if address:
        lines.append(f"📫 {address}")
    
    # Links
    maps_url = place.get("google_maps_url")
    website = place.get("website")
    
    links = []
    if maps_url:
        links.append(f'<a href="{maps_url}">Google Maps</a>')
    if website:
        links.append(f'<a href="{website}">Sitio web</a>')
    
    if links:
        lines.append(" | ".join(links))
    
    return "\n".join(lines)


def format_places_summary(places: List[dict], location: str, radius: float) -> str:
    """Format search results summary."""
    if not places:
        return f"❌ No se encontraron alojamientos en {location} (radio: {radius} km)"
    
    lines = [
        f"🏨 <b>Encontrados {len(places)} alojamientos</b>",
        f"📍 {location} (radio: {radius} km)",
        "",
    ]
    
    # Stats
    ratings = [p.get("rating") for p in places if p.get("rating")]
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        lines.append(f"⭐ Rating promedio: {avg_rating:.1f}")
    
    lines.append("")
    lines.append("Enviando resultados...")
    
    return "\n".join(lines)
