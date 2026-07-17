import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openai import AsyncOpenAI

from app.config import settings


STT_CONTEXT_PROMPT = (
    "Conversación en español colombiano sobre Respirarte, terapia "
    "respiratoria domiciliaria, Dra. D'Aleman, Bogotá, Sabana de "
    "Occidente, EPS, traqueostomía, rehabilitación pulmonar y solicitud "
    "de citas. Conserve literalmente nombres, fechas, horas, números "
    "y direcciones."
)


@dataclass(frozen=True)
class SpeechTranscriptionResult:
    text: str | None
    model: str
    language: str
    status: str
    latency_ms: int
    error_reason: str | None = None


async def transcribe_spanish_voice_note(
    audio_path: Path,
    *,
    client: Any | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> SpeechTranscriptionResult:
    started_at = clock()
    model = settings.voice_stt_model
    language = settings.voice_stt_language
    owns_client = client is None

    def result(
        *,
        text: str | None,
        status: str,
        error_reason: str | None = None,
    ) -> SpeechTranscriptionResult:
        latency_ms = max(0, round((clock() - started_at) * 1000))

        return SpeechTranscriptionResult(
            text=text,
            model=model,
            language=language,
            status=status,
            latency_ms=latency_ms,
            error_reason=error_reason,
        )

    if not audio_path.exists():
        return result(
            text=None,
            status="error",
            error_reason="audio_file_missing",
        )

    if audio_path.stat().st_size == 0:
        return result(
            text=None,
            status="error",
            error_reason="audio_file_empty",
        )

    if owns_client:
        if not settings.openai_api_key:
            return result(
                text=None,
                status="error",
                error_reason="openai_api_key_missing",
            )

        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=45.0,
            max_retries=1,
        )

    try:
        with audio_path.open("rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                response_format="text",
                prompt=STT_CONTEXT_PROMPT,
            )

        transcript = (
            response
            if isinstance(response, str)
            else getattr(response, "text", "")
        )
        transcript = transcript.strip()

        if not transcript:
            return result(
                text=None,
                status="error",
                error_reason="empty_transcription",
            )

        return result(
            text=transcript,
            status="success",
        )

    except Exception as exc:
        return result(
            text=None,
            status="error",
            error_reason=f"provider_error:{type(exc).__name__}",
        )

    finally:
        if owns_client and client is not None:
            await client.close()
