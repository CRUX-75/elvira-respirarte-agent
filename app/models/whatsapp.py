from typing import Any

from pydantic import BaseModel


SUPPORTED_MESSAGE_TYPES = {"text", "audio"}
SUPPORTED_STATUS_TYPES = {"sent", "delivered", "read", "failed"}


class WhatsAppPayload(BaseModel):
    object: str
    entry: list[Any]

    def _iter_values(self):
        for entry in self.entry:
            if not isinstance(entry, dict):
                continue

            for change in entry.get("changes", []):
                if not isinstance(change, dict):
                    continue

                value = change.get("value")

                if isinstance(value, dict):
                    yield value

    def extract_status_updates(self) -> list[dict]:
        """Extract privacy-minimized outbound message status updates."""
        updates: list[dict] = []

        for value in self._iter_values():
            statuses = value.get("statuses")

            if not isinstance(statuses, list):
                continue

            for item in statuses:
                if not isinstance(item, dict):
                    continue

                provider_message_id = item.get("id")
                provider_status = item.get("status")

                if (
                    not isinstance(provider_message_id, str)
                    or not provider_message_id.strip()
                    or provider_status not in SUPPORTED_STATUS_TYPES
                ):
                    continue

                error_code = None
                errors = item.get("errors")

                if isinstance(errors, list) and errors:
                    first_error = errors[0]

                    if isinstance(first_error, dict):
                        raw_code = first_error.get("code")

                        if isinstance(raw_code, (str, int)):
                            error_code = str(raw_code)

                updates.append(
                    {
                        "provider_message_id": provider_message_id.strip(),
                        "status": provider_status,
                        "timestamp": item.get("timestamp"),
                        "error_code": error_code,
                    }
                )

        return updates

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
