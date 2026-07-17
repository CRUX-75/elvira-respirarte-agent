import base64
import hashlib
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator
from urllib.parse import urlparse

import httpx

from app.config import settings


MEDIA_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
SUPPORTED_VOICE_NOTE_MIME_TYPE = "audio/ogg"


@dataclass(frozen=True)
class DownloadedWhatsAppMedia:
    media_id: str
    content: bytes
    mime_type: str | None
    sha256: str | None
    file_size: int


def _authorization_headers() -> dict[str, str]:
    if not settings.whatsapp_token:
        raise ValueError("WhatsApp token not configured")

    return {
        "Authorization": f"Bearer {settings.whatsapp_token}",
    }


def _validate_media_url(media_url: str) -> None:
    parsed = urlparse(media_url)

    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Invalid WhatsApp media URL")


def _base_mime_type(mime_type: str | None) -> str:
    return (mime_type or "").split(";", 1)[0].strip().lower()


def _validate_sha256(content: bytes, expected_sha256: str | None) -> None:
    if not expected_sha256:
        return

    digest = hashlib.sha256(content).digest()
    digest_base64 = base64.b64encode(digest).decode("ascii")
    digest_hex = digest.hex()

    if expected_sha256 not in {digest_base64, digest_hex}:
        raise ValueError("WhatsApp media SHA-256 mismatch")


async def _retrieve_media_metadata(
    media_id: str,
    client: httpx.AsyncClient,
) -> dict:
    if not media_id:
        raise ValueError("WhatsApp media ID is required")

    url = f"{settings.whatsapp_api_url}/{media_id}"
    response = await client.get(
        url,
        headers=_authorization_headers(),
    )
    response.raise_for_status()

    metadata = response.json()
    media_url = metadata.get("url")

    if not media_url:
        raise ValueError("WhatsApp media URL missing from response")

    _validate_media_url(media_url)
    return metadata


async def download_whatsapp_media(
    media_id: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> DownloadedWhatsAppMedia:
    owns_client = client is None

    if client is None:
        client = httpx.AsyncClient(timeout=MEDIA_TIMEOUT)

    try:
        for attempt in range(2):
            metadata = await _retrieve_media_metadata(media_id, client)

            try:
                response = await client.get(
                    metadata["url"],
                    headers=_authorization_headers(),
                )
                response.raise_for_status()

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404 and attempt == 0:
                    continue
                raise

            content = response.content
            if not content:
                raise ValueError("Downloaded WhatsApp media is empty")

            mime_type = (
                metadata.get("mime_type")
                or response.headers.get("content-type")
            )

            return DownloadedWhatsAppMedia(
                media_id=media_id,
                content=content,
                mime_type=mime_type,
                sha256=metadata.get("sha256"),
                file_size=len(content),
            )

        raise RuntimeError("WhatsApp media download retry exhausted")

    finally:
        if owns_client:
            await client.aclose()


@contextmanager
def temporary_whatsapp_voice_note(
    downloaded: DownloadedWhatsAppMedia,
    *,
    expected_mime_type: str | None = None,
    expected_sha256: str | None = None,
) -> Iterator[Path]:
    actual_mime_type = _base_mime_type(downloaded.mime_type)

    if actual_mime_type != SUPPORTED_VOICE_NOTE_MIME_TYPE:
        raise ValueError("Unsupported WhatsApp voice-note MIME type")

    if (
        expected_mime_type
        and _base_mime_type(expected_mime_type) != actual_mime_type
    ):
        raise ValueError("WhatsApp media MIME type mismatch")

    if downloaded.file_size != len(downloaded.content):
        raise ValueError("WhatsApp media size mismatch")

    if downloaded.file_size > settings.voice_max_media_bytes:
        raise ValueError("WhatsApp voice note exceeds size limit")

    _validate_sha256(
        downloaded.content,
        expected_sha256 or downloaded.sha256,
    )

    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            prefix="elvira-voice-",
            suffix=".ogg",
            delete=False,
        ) as temporary_file:
            temporary_file.write(downloaded.content)
            temporary_path = Path(temporary_file.name)

        os.chmod(temporary_path, 0o600)
        yield temporary_path

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
