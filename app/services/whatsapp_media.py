from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.config import settings


MEDIA_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


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
