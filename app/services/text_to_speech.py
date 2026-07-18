import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Iterator

from openai import AsyncOpenAI

from app.config import settings


AI_VOICE_DISCLOSURE = (
    "Soy Elvira, la asistente virtual de Respirarte."
)

TTS_INSTRUCTIONS = (
    "Hable en español colombiano neutro, con tono profesional, cálido "
    "y sereno. Articule nombres, fechas, horas y números con claridad. "
    "No agregue, cambie ni omita contenido."
)

MAX_TTS_INPUT_CHARACTERS = 4096
OGG_MAGIC = b"OggS"


@dataclass(frozen=True)
class SpeechSynthesisResult:
    audio_content: bytes | None
    model: str
    voice: str
    response_format: str
    status: str
    latency_ms: int
    error_reason: str | None = None


def build_voice_reply_text(
    response_text: str,
    *,
    include_disclosure: bool = True,
) -> str:
    normalized = response_text.strip()

    if not normalized:
        raise ValueError("Deterministic response text is empty")

    if (
        include_disclosure
        and not normalized.startswith(AI_VOICE_DISCLOSURE)
    ):
        tts_input = f"{AI_VOICE_DISCLOSURE} {normalized}"
    else:
        tts_input = normalized

    if len(tts_input) > MAX_TTS_INPUT_CHARACTERS:
        raise ValueError("TTS input exceeds character limit")

    return tts_input


async def synthesize_voice_reply(
    response_text: str,
    *,
    include_disclosure: bool = True,
    client: Any | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> SpeechSynthesisResult:
    started_at = clock()
    model = settings.voice_tts_model
    voice = settings.voice_tts_voice
    response_format = settings.voice_tts_response_format
    owns_client = client is None

    def result(
        *,
        audio_content: bytes | None,
        status: str,
        error_reason: str | None = None,
    ) -> SpeechSynthesisResult:
        return SpeechSynthesisResult(
            audio_content=audio_content,
            model=model,
            voice=voice,
            response_format=response_format,
            status=status,
            latency_ms=max(0, round((clock() - started_at) * 1000)),
            error_reason=error_reason,
        )

    try:
        tts_input = build_voice_reply_text(
            response_text,
            include_disclosure=include_disclosure,
        )
    except ValueError as exc:
        return result(
            audio_content=None,
            status="error",
            error_reason=str(exc),
        )

    if response_format != "opus":
        return result(
            audio_content=None,
            status="error",
            error_reason="unsupported_tts_response_format",
        )

    if owns_client:
        if not settings.openai_api_key:
            return result(
                audio_content=None,
                status="error",
                error_reason="openai_api_key_missing",
            )

        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=45.0,
            max_retries=1,
        )

    try:
        response = await client.audio.speech.create(
            model=model,
            voice=voice,
            input=tts_input,
            instructions=TTS_INSTRUCTIONS,
            response_format=response_format,
        )

        audio_content = getattr(response, "content", None)

        if not isinstance(audio_content, bytes) or not audio_content:
            return result(
                audio_content=None,
                status="error",
                error_reason="empty_synthesized_audio",
            )

        return result(
            audio_content=audio_content,
            status="success",
        )

    except Exception as exc:
        return result(
            audio_content=None,
            status="error",
            error_reason=f"provider_error:{type(exc).__name__}",
        )

    finally:
        if owns_client and client is not None:
            await client.close()


@contextmanager
def temporary_synthesized_voice_note(
    audio_content: bytes,
) -> Iterator[Path]:
    if not audio_content:
        raise ValueError("Synthesized voice audio is empty")

    if len(audio_content) > settings.voice_max_media_bytes:
        raise ValueError("Synthesized voice audio exceeds size limit")

    if not audio_content.startswith(OGG_MAGIC):
        raise ValueError("Synthesized voice audio is not OGG/Opus")

    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            prefix="elvira-tts-",
            suffix=".ogg",
            delete=False,
        ) as temporary_file:
            temporary_file.write(audio_content)
            temporary_path = Path(temporary_file.name)

        os.chmod(temporary_path, 0o600)
        yield temporary_path

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
