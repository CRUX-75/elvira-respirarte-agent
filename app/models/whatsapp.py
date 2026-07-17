from typing import Any

from pydantic import BaseModel


SUPPORTED_MESSAGE_TYPES = {"text", "audio"}


class WhatsAppPayload(BaseModel):
    object: str
    entry: list[Any]

    def extract_message(self) -> dict | None:
        try:
            value = self.entry[0]["changes"][0]["value"]
            messages = value.get("messages")

            # Notificación de status, no es mensaje.
            if not messages:
                return None

            msg = messages[0]
            msg_type = msg.get("type")

            if msg_type not in SUPPORTED_MESSAGE_TYPES:
                return None

            telefono = msg.get("from")
            if not telefono:
                return None

            nombre = (
                value.get("contacts", [{}])[0]
                .get("profile", {})
                .get("name")
            )

            common_fields = {
                "telefono": telefono,
                "nombre": nombre,
                "msg_type": msg_type,
                "whatsapp_message_id": msg.get("id"),
                "whatsapp_timestamp": msg.get("timestamp"),
            }

            if msg_type == "text":
                texto = msg.get("text", {}).get("body", "").strip()
                if not texto:
                    return None

                return {
                    **common_fields,
                    "mensaje": texto,
                }

            audio = msg.get("audio", {})
            media_id = audio.get("id")
            mime_type = audio.get("mime_type")
            sha256 = audio.get("sha256")
            voice = audio.get("voice") is True

            # Inicialmente solo aceptamos notas de voz reales de WhatsApp.
            if (
                not common_fields["whatsapp_message_id"]
                or not media_id
                or not mime_type
                or not sha256
                or not voice
            ):
                return None

            return {
                **common_fields,
                "mensaje": None,
                "media_id": media_id,
                "mime_type": mime_type,
                "sha256": sha256,
                "voice": voice,
            }

        except (IndexError, KeyError, TypeError):
            return None
