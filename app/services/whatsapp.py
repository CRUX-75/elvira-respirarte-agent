from collections.abc import Sequence

import httpx

from app.config import settings


def _whatsapp_request_config() -> tuple[str, dict[str, str]]:
    if not settings.whatsapp_phone_number_id or not settings.whatsapp_token:
        raise ValueError("WhatsApp credentials not configured")

    url = f"{settings.whatsapp_api_url}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    return url, headers


async def send_whatsapp_message(telefono: str, mensaje: str) -> dict:
    url, headers = _whatsapp_request_config()

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


async def send_whatsapp_template_message(
    *,
    telefono: str,
    template_name: str,
    language_code: str,
    body_parameters: Sequence[str],
) -> dict:
    """Send one approved WhatsApp template with ordered text parameters."""
    name = str(template_name or "").strip()
    language = str(language_code or "").strip()
    parameters = [str(value or "").strip() for value in body_parameters]

    if not name:
        raise ValueError("WhatsApp template name is required")

    if not language:
        raise ValueError("WhatsApp template language code is required")

    if not parameters or any(not value for value in parameters):
        raise ValueError("WhatsApp template parameters must be non-empty")

    url, headers = _whatsapp_request_config()

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono,
        "type": "template",
        "template": {
            "name": name,
            "language": {
                "code": language,
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": value,
                        }
                        for value in parameters
                    ],
                }
            ],
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def mark_whatsapp_message_read_and_show_typing(
    whatsapp_message_id: str,
) -> dict:
    """Mark an inbound WhatsApp message as read and show typing indicator."""
    if not whatsapp_message_id:
        raise ValueError("WhatsApp message ID is required")

    url, headers = _whatsapp_request_config()

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
