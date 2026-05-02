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