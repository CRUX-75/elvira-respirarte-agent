import json
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from app.config import settings


CommandRunner = Callable[..., subprocess.CompletedProcess]


def normalize_whatsapp_phone(telefono: str | None) -> str:
    return "".join(
        character
        for character in (telefono or "")
        if character.isdigit()
    )


def configured_voice_phone_numbers() -> set[str]:
    configured = settings.voice_allowed_phone_numbers or ""

    return {
        normalized
        for raw_phone in configured.split(",")
        if (normalized := normalize_whatsapp_phone(raw_phone))
    }


def is_voice_phone_allowed(telefono: str | None) -> bool:
    normalized_phone = normalize_whatsapp_phone(telefono)

    if not normalized_phone:
        return False

    allowed_numbers = configured_voice_phone_numbers()

    # Fail closed: an empty allowlist authorizes nobody.
    if not allowed_numbers:
        return False

    return normalized_phone in allowed_numbers


def validate_voice_note_duration(
    audio_path: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> float:
    if not audio_path.exists():
        raise ValueError("Voice-note file does not exist")

    if audio_path.stat().st_size == 0:
        raise ValueError("Voice-note file is empty")

    command: Sequence[str] = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(audio_path),
    ]

    try:
        completed = runner(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is not available") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Voice-note duration probe timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("Unable to inspect voice-note duration") from exc

    try:
        payload = json.loads(completed.stdout)
        duration_seconds = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid voice-note duration metadata") from exc

    if duration_seconds <= 0:
        raise ValueError("Voice-note duration must be positive")

    if duration_seconds > settings.voice_max_duration_seconds:
        raise ValueError("WhatsApp voice note exceeds duration limit")

    return duration_seconds
