from app.services.log_privacy import print_safe_event
from typing import Any


ALLOWED_VOICE_METADATA = {
    "stage",
    "status",
    "duration_ms",
    "duration_seconds",
    "media_size_bytes",
    "mime_type",
    "file_suffix",
    "transcript_length",
    "stt_model",
    "tts_model",
    "tts_voice",
    "reply_mode",
    "voice_fallback_used",
    "delivery_status",
    "processed_marked",
    "state_updated",
    "error_reason",
}


def emit_voice_event(
    event: str,
    *,
    whatsapp_message_id: str | None,
    **metadata: Any,
) -> None:
    safe_metadata = {
        key: value
        for key, value in metadata.items()
        if key in ALLOWED_VOICE_METADATA
        and isinstance(value, (str, int, float, bool, type(None)))
    }

    print_safe_event(
        {
            "event": event,
            "whatsapp_message_id": (
                whatsapp_message_id or "unknown"
            ),
            **safe_metadata,
        }
    )


def safe_message_content_for_log(
    *,
    msg_type: str,
    mensaje: str | None,
) -> str | None:
    if msg_type == "audio":
        return None

    return mensaje
