from pydantic import BaseModel
from typing import Any


SUPPORTED_MESSAGE_TYPES = {"text"}


class WhatsAppPayload(BaseModel):
    object: str
    entry: list[Any]

    def extract_message(self) -> dict | None:
        try:
            value = self.entry[0]["changes"][0]["value"]
            messages = value.get("messages")

            # Notificación de status, no es mensaje
            if not messages:
                return None

            msg = messages[0]
            msg_type = msg.get("type")

            # Solo procesamos texto por ahora
            if msg_type not in SUPPORTED_MESSAGE_TYPES:
                return None

            telefono = msg.get("from")
            if not telefono:
                return None

            texto = msg.get("text", {}).get("body", "").strip()
            if not texto:
                return None

            nombre = (
                value.get("contacts", [{}])[0]
                .get("profile", {})
                .get("name")
            )

            return {
                "telefono": telefono,
                "mensaje": texto,
                "nombre": nombre,
                "msg_type": msg_type,
                "whatsapp_message_id": msg.get("id"),
                "whatsapp_timestamp": msg.get("timestamp"),
            }

        except (IndexError, KeyError, TypeError):
            return None