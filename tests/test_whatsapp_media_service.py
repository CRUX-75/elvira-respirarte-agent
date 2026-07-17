import asyncio

import httpx
import pytest

from app.services.whatsapp_media import download_whatsapp_media


def test_download_whatsapp_media_success(monkeypatch):
    import app.services.whatsapp_media as media_service

    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_api_url",
        "https://graph.facebook.com/v25.0",
    )
    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_token",
        "test-token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"

        if request.url.host == "graph.facebook.com":
            return httpx.Response(
                200,
                json={
                    "url": "https://lookaside.fbsbx.com/media/audio-001",
                    "mime_type": "audio/ogg; codecs=opus",
                    "sha256": "sha256-test",
                },
            )

        return httpx.Response(
            200,
            content=b"ogg-opus-audio",
            headers={"content-type": "audio/ogg; codecs=opus"},
        )

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await download_whatsapp_media(
                "audio-media-id-001",
                client=client,
            )

    downloaded = asyncio.run(run())

    assert downloaded.media_id == "audio-media-id-001"
    assert downloaded.content == b"ogg-opus-audio"
    assert downloaded.mime_type == "audio/ogg; codecs=opus"
    assert downloaded.sha256 == "sha256-test"
    assert downloaded.file_size == len(b"ogg-opus-audio")


def test_download_whatsapp_media_refreshes_expired_url_once(monkeypatch):
    import app.services.whatsapp_media as media_service

    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_api_url",
        "https://graph.facebook.com/v25.0",
    )
    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_token",
        "test-token",
    )

    metadata_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal metadata_calls

        if request.url.host == "graph.facebook.com":
            metadata_calls += 1
            suffix = "expired" if metadata_calls == 1 else "fresh"

            return httpx.Response(
                200,
                json={
                    "url": f"https://lookaside.fbsbx.com/media/{suffix}",
                    "mime_type": "audio/ogg; codecs=opus",
                    "sha256": "sha256-test",
                },
            )

        if request.url.path.endswith("/expired"):
            return httpx.Response(404)

        return httpx.Response(
            200,
            content=b"fresh-audio",
            headers={"content-type": "audio/ogg; codecs=opus"},
        )

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await download_whatsapp_media(
                "audio-media-id-002",
                client=client,
            )

    downloaded = asyncio.run(run())

    assert metadata_calls == 2
    assert downloaded.content == b"fresh-audio"


def test_download_whatsapp_media_requires_token(monkeypatch):
    import app.services.whatsapp_media as media_service

    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_token",
        None,
    )

    async def run():
        async with httpx.AsyncClient() as client:
            return await download_whatsapp_media(
                "audio-media-id-003",
                client=client,
            )

    with pytest.raises(ValueError, match="token not configured"):
        asyncio.run(run())


def test_download_whatsapp_media_rejects_invalid_url(monkeypatch):
    import app.services.whatsapp_media as media_service

    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_api_url",
        "https://graph.facebook.com/v25.0",
    )
    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_token",
        "test-token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "url": "http://insecure.example/audio",
                "mime_type": "audio/ogg; codecs=opus",
            },
        )

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await download_whatsapp_media(
                "audio-media-id-004",
                client=client,
            )

    with pytest.raises(ValueError, match="Invalid WhatsApp media URL"):
        asyncio.run(run())
