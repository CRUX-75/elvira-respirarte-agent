from dataclasses import dataclass

from app.config import settings

from app.services.text_to_speech import (
    synthesize_voice_reply,
    temporary_synthesized_voice_note,
)
from app.services.voice_observability import emit_voice_event
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


def should_send_voice_reply(inbound_message_type: str) -> bool:
    if not settings.voice_replies_enabled:
        return False

    if (
        settings.voice_reply_to_audio_only
        and inbound_message_type != "audio"
    ):
        return False

    return True


def should_include_voice_disclosure(patient_state: str) -> bool:
    return patient_state == "ST_INIT"


class VoiceDeliveryError(RuntimeError):
    pass


async def _send_text_fallback(
    *,
    telefono: str,
    whatsapp_message_id: str,
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
        emit_voice_event(
            "voice_text_fallback_failed",
            whatsapp_message_id=whatsapp_message_id,
            stage="fallback_delivery",
            status="error",
            error_reason=f"send_error:{type(exc).__name__}",
            delivery_status="send_failed",
            voice_fallback_used=True,
        )

        raise VoiceDeliveryError(
            "Voice and text delivery both failed"
        ) from exc

    emit_voice_event(
        "voice_text_fallback_sent",
        whatsapp_message_id=whatsapp_message_id,
        stage="fallback_delivery",
        status="success",
        error_reason=voice_error_reason,
        duration_ms=tts_latency_ms,
        delivery_status="sent",
        reply_mode="text",
        voice_fallback_used=True,
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
    whatsapp_message_id: str,
    response_text: str,
    include_disclosure: bool,
) -> VoiceDeliveryResult:
    synthesis = await synthesize_voice_reply(
        response_text,
        include_disclosure=include_disclosure,
    )

    if synthesis.status != "success" or not synthesis.audio_content:
        error_reason = synthesis.error_reason or "tts_failed"

        emit_voice_event(
            "voice_tts_failed",
            whatsapp_message_id=whatsapp_message_id,
            stage="tts",
            status="error",
            duration_ms=synthesis.latency_ms,
            tts_model=synthesis.model,
            tts_voice=synthesis.voice,
            error_reason=error_reason,
        )

        return await _send_text_fallback(
            telefono=telefono,
            whatsapp_message_id=whatsapp_message_id,
            response_text=response_text,
            voice_error_reason=error_reason,
            tts_latency_ms=synthesis.latency_ms,
        )

    emit_voice_event(
        "voice_tts_succeeded",
        whatsapp_message_id=whatsapp_message_id,
        stage="tts",
        status="success",
        duration_ms=synthesis.latency_ms,
        tts_model=synthesis.model,
        tts_voice=synthesis.voice,
        media_size_bytes=len(synthesis.audio_content),
    )

    try:
        with temporary_synthesized_voice_note(
            synthesis.audio_content,
        ) as audio_path:
            uploaded = await upload_whatsapp_voice_media(audio_path)

            emit_voice_event(
                "voice_media_uploaded",
                whatsapp_message_id=whatsapp_message_id,
                stage="media_upload",
                status="success",
                file_suffix=audio_path.suffix,
            )

            await send_whatsapp_voice_note(
                telefono=telefono,
                media_id=uploaded.media_id,
            )

    except Exception as exc:
        error_reason = (
            f"voice_delivery_error:{type(exc).__name__}"
        )

        emit_voice_event(
            "voice_reply_failed",
            whatsapp_message_id=whatsapp_message_id,
            stage="voice_delivery",
            status="error",
            error_reason=error_reason,
        )

        return await _send_text_fallback(
            telefono=telefono,
            whatsapp_message_id=whatsapp_message_id,
            response_text=response_text,
            voice_error_reason=error_reason,
            tts_latency_ms=synthesis.latency_ms,
        )

    emit_voice_event(
        "voice_reply_sent",
        whatsapp_message_id=whatsapp_message_id,
        stage="voice_delivery",
        status="success",
        duration_ms=synthesis.latency_ms,
        tts_model=synthesis.model,
        tts_voice=synthesis.voice,
        delivery_status="sent",
        reply_mode="voice",
        voice_fallback_used=False,
    )

    return VoiceDeliveryResult(
        delivery_status="sent",
        reply_mode="voice",
        voice_fallback_used=False,
        voice_error_reason=None,
        tts_latency_ms=synthesis.latency_ms,
    )
