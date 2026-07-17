from dataclasses import dataclass

from app.config import settings
from app.repositories.logs import log_error
from app.repositories.processed_messages import mark_message_processed
from app.services.audio_normalization import prepare_audio_for_stt
from app.services.speech_to_text import transcribe_spanish_voice_note
from app.services.whatsapp import send_whatsapp_message
from app.services.whatsapp_media import (
    download_whatsapp_media,
    temporary_whatsapp_voice_note,
)


VOICE_FAILURE_MESSAGE = (
    "No pude procesar correctamente su nota de voz. "
    "Por favor envíeme una nota más corta o escríbame el mensaje "
    "para poder ayudarle."
)


@dataclass(frozen=True)
class InboundVoiceResult:
    text: str | None
    status: str
    error_reason: str | None
    latency_ms: int | None = None


async def process_inbound_voice_note(
    extracted: dict,
) -> InboundVoiceResult:
    try:
        downloaded = await download_whatsapp_media(extracted["media_id"])

        with temporary_whatsapp_voice_note(
            downloaded,
            expected_mime_type=extracted.get("mime_type"),
            expected_sha256=extracted.get("sha256"),
        ) as source_path:
            with prepare_audio_for_stt(source_path) as normalized_path:
                transcription = await transcribe_spanish_voice_note(
                    normalized_path,
                )

    except Exception as exc:
        return InboundVoiceResult(
            text=None,
            status="error",
            error_reason=f"voice_pipeline_error:{type(exc).__name__}",
        )

    if transcription.status != "success" or not transcription.text:
        return InboundVoiceResult(
            text=None,
            status="error",
            error_reason=transcription.error_reason or "transcription_failed",
            latency_ms=transcription.latency_ms,
        )

    return InboundVoiceResult(
        text=transcription.text.strip(),
        status="success",
        error_reason=None,
        latency_ms=transcription.latency_ms,
    )


async def deliver_voice_failure(
    *,
    telefono: str,
    whatsapp_message_id: str,
    whatsapp_timestamp: str | None,
    result: InboundVoiceResult,
) -> dict:
    log_error(
        telefono=telefono,
        error=f"Inbound voice processing failed: {result.error_reason}",
    )

    if settings.whatsapp_sending_enabled:
        try:
            await send_whatsapp_message(
                telefono=telefono,
                mensaje=VOICE_FAILURE_MESSAGE,
            )
            delivery_status = "sent"

        except Exception as exc:
            print(
                {
                    "event": "whatsapp_voice_fallback_send_failed",
                    "telefono": telefono,
                    "whatsapp_message_id": whatsapp_message_id,
                    "error_type": type(exc).__name__,
                    "delivery_status": "send_failed",
                    "processed_marked": False,
                }
            )

            return {
                "status": "error",
                "reason": "voice_fallback_send_failed",
                "delivery_status": "send_failed",
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
                "processed_marked": False,
                "state_updated": False,
            }
    else:
        delivery_status = "sending_skipped"

    try:
        mark_message_processed(
            whatsapp_message_id=whatsapp_message_id,
            telefono=telefono,
        )
        processed_marked = True
    except Exception as exc:
        log_error(
            telefono=telefono,
            error=(
                "Voice fallback processed marker failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )
        processed_marked = False

    print(
        {
            "event": "whatsapp_voice_processing_failed",
            "telefono": telefono,
            "whatsapp_message_id": whatsapp_message_id,
            "error_reason": result.error_reason,
            "stt_latency_ms": result.latency_ms,
            "delivery_status": delivery_status,
            "processed_marked": processed_marked,
            "state_updated": False,
        }
    )

    return {
        "status": delivery_status,
        "reason": "voice_processing_failed",
        "delivery_status": delivery_status,
        "whatsapp_message_id": whatsapp_message_id,
        "whatsapp_timestamp": whatsapp_timestamp,
        "processed_marked": processed_marked,
        "state_updated": False,
    }
