from dataclasses import dataclass

from app.config import settings
from app.repositories.logs import log_error
from app.repositories.processed_messages import mark_message_processed
from app.services.audio_normalization import prepare_audio_for_stt
from app.services.speech_to_text import transcribe_spanish_voice_note
from app.services.voice_observability import emit_voice_event
from app.services.voice_safety import validate_voice_note_duration
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
    whatsapp_message_id = extracted.get("whatsapp_message_id")
    stage = "media_download"
    temporary_materialized = False

    emit_voice_event(
        "voice_input_received",
        whatsapp_message_id=whatsapp_message_id,
        stage="input",
        status="received",
        mime_type=extracted.get("mime_type"),
    )

    try:
        downloaded = await download_whatsapp_media(extracted["media_id"])

        emit_voice_event(
            "voice_media_downloaded",
            whatsapp_message_id=whatsapp_message_id,
            stage="media_download",
            status="success",
            mime_type=getattr(downloaded, "mime_type", extracted.get("mime_type")),
            media_size_bytes=getattr(downloaded, "file_size", None),
        )

        stage = "media_validation"

        with temporary_whatsapp_voice_note(
            downloaded,
            expected_mime_type=extracted.get("mime_type"),
            expected_sha256=extracted.get("sha256"),
        ) as source_path:
            temporary_materialized = True
            duration_seconds = validate_voice_note_duration(source_path)

            emit_voice_event(
                "voice_media_validated",
                whatsapp_message_id=whatsapp_message_id,
                stage="media_validation",
                status="success",
                duration_seconds=round(duration_seconds, 3),
                media_size_bytes=getattr(downloaded, "file_size", None),
            )

            stage = "audio_normalization"

            with prepare_audio_for_stt(source_path) as normalized_path:
                emit_voice_event(
                    "voice_audio_normalized",
                    whatsapp_message_id=whatsapp_message_id,
                    stage="audio_normalization",
                    status="success",
                    file_suffix=normalized_path.suffix,
                )

                stage = "stt"
                transcription = await transcribe_spanish_voice_note(
                    normalized_path,
                )

    except Exception as exc:
        error_reason = f"voice_pipeline_error:{type(exc).__name__}"

        emit_voice_event(
            "voice_processing_failed",
            whatsapp_message_id=whatsapp_message_id,
            stage=stage,
            status="error",
            error_reason=error_reason,
        )

        return InboundVoiceResult(
            text=None,
            status="error",
            error_reason=error_reason,
        )

    finally:
        if temporary_materialized:
            emit_voice_event(
                "voice_cleanup_completed",
                whatsapp_message_id=whatsapp_message_id,
                stage="cleanup",
                status="success",
            )

    if transcription.status != "success" or not transcription.text:
        emit_voice_event(
            "voice_stt_failed",
            whatsapp_message_id=whatsapp_message_id,
            stage="stt",
            status="error",
            duration_ms=transcription.latency_ms,
            stt_model=getattr(transcription, "model", settings.voice_stt_model),
            error_reason=(
                transcription.error_reason or "transcription_failed"
            ),
        )

        return InboundVoiceResult(
            text=None,
            status="error",
            error_reason=(
                transcription.error_reason or "transcription_failed"
            ),
            latency_ms=transcription.latency_ms,
        )

    transcript = transcription.text.strip()

    emit_voice_event(
        "voice_stt_succeeded",
        whatsapp_message_id=whatsapp_message_id,
        stage="stt",
        status="success",
        duration_ms=transcription.latency_ms,
        stt_model=getattr(transcription, "model", settings.voice_stt_model),
        transcript_length=len(transcript),
    )

    return InboundVoiceResult(
        text=transcript,
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
            emit_voice_event(
                "voice_text_fallback_failed",
                whatsapp_message_id=whatsapp_message_id,
                stage="fallback_delivery",
                status="error",
                error_reason=f"send_error:{type(exc).__name__}",
                delivery_status="send_failed",
                processed_marked=False,
                state_updated=False,
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

    emit_voice_event(
        "voice_processing_failed",
        whatsapp_message_id=whatsapp_message_id,
        stage="fallback_delivery",
        status="handled",
        duration_ms=result.latency_ms,
        error_reason=result.error_reason,
        delivery_status=delivery_status,
        processed_marked=processed_marked,
        state_updated=False,
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
