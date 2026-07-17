import base64
import hashlib

import pytest

from app.services.whatsapp_media import (
    DownloadedWhatsAppMedia,
    temporary_whatsapp_voice_note,
)


def build_downloaded_media(
    content: bytes = b"valid-ogg-opus",
    mime_type: str = "audio/ogg; codecs=opus",
) -> DownloadedWhatsAppMedia:
    sha256 = base64.b64encode(
        hashlib.sha256(content).digest()
    ).decode("ascii")

    return DownloadedWhatsAppMedia(
        media_id="audio-media-id-temp",
        content=content,
        mime_type=mime_type,
        sha256=sha256,
        file_size=len(content),
    )


def test_temporary_voice_note_is_created_and_deleted():
    downloaded = build_downloaded_media()

    with temporary_whatsapp_voice_note(downloaded) as audio_path:
        saved_path = audio_path

        assert audio_path.exists()
        assert audio_path.suffix == ".ogg"
        assert audio_path.read_bytes() == downloaded.content
        assert audio_path.stat().st_mode & 0o777 == 0o600

    assert not saved_path.exists()


def test_temporary_voice_note_rejects_unsupported_mime_type():
    downloaded = build_downloaded_media(mime_type="audio/mpeg")

    with pytest.raises(
        ValueError,
        match="Unsupported WhatsApp voice-note MIME type",
    ):
        with temporary_whatsapp_voice_note(downloaded):
            pass


def test_temporary_voice_note_rejects_oversized_media(monkeypatch):
    import app.services.whatsapp_media as media_service

    monkeypatch.setattr(
        media_service.settings,
        "voice_max_media_bytes",
        4,
    )

    downloaded = build_downloaded_media(content=b"too-large")

    with pytest.raises(ValueError, match="exceeds size limit"):
        with temporary_whatsapp_voice_note(downloaded):
            pass


def test_temporary_voice_note_rejects_sha256_mismatch():
    downloaded = build_downloaded_media()

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        with temporary_whatsapp_voice_note(
            downloaded,
            expected_sha256="invalid-sha256",
        ):
            pass
