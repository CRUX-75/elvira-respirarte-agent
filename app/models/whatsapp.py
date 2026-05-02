from pydantic import BaseModel
from typing import Any


class WhatsAppPayload(BaseModel):
    object: str
    entry: list[Any]

    def extract_message(self) -> dict | None:
        try:
            value = self.entry[0]["changes"][0]["value"]
            messages = value.get("messages")
            if not messages:
                return None
            msg = messages[0]
            return {
                "telefono": msg["from"],
                "mensaje": msg["text"]["body"],
                "nombre": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            }
        except (IndexError, KeyError):
            return None