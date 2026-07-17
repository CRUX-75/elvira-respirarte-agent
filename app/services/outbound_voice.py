from dataclasses import dataclass

from app.config import settings
from app.services.text_to_speech import (
    synthesize_voice_reply,
    temporary_synthesized_voice_note,
)
from app.services.whatsapp import send_whatsapp_message
from app.services.whatsapp_media import (
    send_whatsapp_voice_note,
    upload_whatsapp_voice_media,
)


@dataclass(frozen=True)
class VoiceDeliveryResult:
    delivery_status: str
    reply_mode: str
    voice_fallback_used: bool
    voice_error_reason: str | None
    tts_latency_ms: int | None


class VoiceDeliveryError(RuntimeError):
    pass


def should_send_voice_reply(inbound_message_type: str) -> bool:
    if not settings.voice_replies_enabled:
        return False

    if (
        settings.voice_reply_to_audio_only
        and inbound_message_type != "audio"
    ):
        return False

    return True


async def _send_text_fallback(
    *,
    telefono: str,
    response_text: str,
    voice_error_reason: str,
    tts_latency_ms: int | None,
) -> VoiceDeliveryResult:
    try:
        await send_whatsapp_message(
            telefono=telefono,
            mensaje=response_text,
        )
    except Exception as exc:
        raise VoiceDeliveryError(
            "Voice and text delivery both failed"
        ) from exc

    print(
        {
            "event": "whatsapp_voice_text_fallback_sent",
            "telefono": telefono,
            "voice_error_reason": voice_error_reason,
            "tts_latency_ms": tts_latency_ms,
            "delivery_status": "sent",
            "reply_mode": "text",
            "voice_fallback_used": True,
        }
    )

    return VoiceDeliveryResult(
        delivery_status="sent",
        reply_mode="text",
        voice_fallback_used=True,
        voice_error_reason=voice_error_reason,
        tts_latency_ms=tts_latency_ms,
    )


async def deliver_voice_reply(
    *,
    telefono: str,
    response_text: str,
) -> VoiceDeliveryResult:
    synthesis = await synthesize_voice_reply(response_text)

    if synthesis.status != "success" or not synthesis.audio_content:
        return await _send_text_fallback(
            telefono=telefono,
            response_text=response_text,
            voice_error_reason=(
                synthesis.error_reason or "tts_failed"
            ),
            tts_latency_ms=synthesis.latency_ms,
        )

    try:
        with temporary_synthesized_voice_note(
            synthesis.audio_content,
        ) as audio_path:
            uploaded = await upload_whatsapp_voice_media(audio_path)

            await send_whatsapp_voice_note(
                telefono=telefono,
                media_id=uploaded.media_id,
            )

    except Exception as exc:
        return await _send_text_fallback(
            telefono=telefono,
            response_text=response_text,
            voice_error_reason=(
                f"voice_delivery_error:{type(exc).__name__}"
            ),
            tts_latency_ms=synthesis.latency_ms,
        )

    print(
        {
            "event": "whatsapp_voice_reply_sent",
            "telefono": telefono,
            "tts_model": synthesis.model,
            "tts_voice": synthesis.voice,
            "tts_latency_ms": synthesis.latency_ms,
            "delivery_status": "sent",
            "reply_mode": "voice",
            "voice_fallback_used": False,
        }
    )

    return VoiceDeliveryResult(
        delivery_status="sent",
        reply_mode="voice",
        voice_fallback_used=False,
        voice_error_reason=None,
        tts_latency_ms=synthesis.latency_ms,
    )
