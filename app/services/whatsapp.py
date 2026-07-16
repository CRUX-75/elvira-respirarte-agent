import httpx
from app.config import settings


async def send_whatsapp_message(telefono: str, mensaje: str) -> dict:
    if not settings.whatsapp_phone_number_id or not settings.whatsapp_token:
        raise ValueError("WhatsApp credentials not configured")

    url = f"{settings.whatsapp_api_url}/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": mensaje},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

async def mark_whatsapp_message_read_and_show_typing(
    whatsapp_message_id: str,
) -> dict:
    """Mark an inbound WhatsApp message as read and show typing indicator."""
    if not settings.whatsapp_phone_number_id or not settings.whatsapp_token:
        raise ValueError("WhatsApp credentials not configured")

    if not whatsapp_message_id:
        raise ValueError("WhatsApp message ID is required")

    url = f"{settings.whatsapp_api_url}/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": whatsapp_message_id,
        "typing_indicator": {
            "type": "text",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
