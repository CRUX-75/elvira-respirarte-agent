import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import app.services.inbound_voice as inbound_voice


def test_process_inbound_voice_note_returns_transcript(
    monkeypatch,
    tmp_path,
):
    source_path = tmp_path / "voice.ogg"
    normalized_path = tmp_path / "voice.webm"
    source_path.write_bytes(b"ogg")
    normalized_path.write_bytes(b"webm")

    async def fake_download(media_id):
        assert media_id == "media-001"
        return object()

    @contextmanager
    def fake_temporary(*args, **kwargs):
        yield source_path

    @contextmanager
    def fake_normalization(path):
        assert path == source_path
        yield normalized_path

    async def fake_transcription(path):
        assert path == normalized_path
        return SimpleNamespace(
            text="Quiero pedir una cita",
            status="success",
            error_reason=None,
            latency_ms=125,
        )

    monkeypatch.setattr(
        inbound_voice,
        "download_whatsapp_media",
        fake_download,
    )
    monkeypatch.setattr(
        inbound_voice,
        "temporary_whatsapp_voice_note",
        fake_temporary,
    )
    monkeypatch.setattr(
        inbound_voice,
        "prepare_audio_for_stt",
        fake_normalization,
    )
    monkeypatch.setattr(
        inbound_voice,
        "transcribe_spanish_voice_note",
        fake_transcription,
    )

    result = asyncio.run(
        inbound_voice.process_inbound_voice_note(
            {
                "media_id": "media-001",
                "mime_type": "audio/ogg",
                "sha256": "expected-sha",
            }
        )
    )

    assert result.status == "success"
    assert result.text == "Quiero pedir una cita"
    assert result.latency_ms == 125


def test_process_inbound_voice_note_returns_safe_error(monkeypatch):
    async def failing_download(media_id):
        raise ValueError("private provider detail")

    monkeypatch.setattr(
        inbound_voice,
        "download_whatsapp_media",
        failing_download,
    )

    result = asyncio.run(
        inbound_voice.process_inbound_voice_note(
            {
                "media_id": "media-002",
                "mime_type": "audio/ogg",
                "sha256": "expected-sha",
            }
        )
    )

    assert result.status == "error"
    assert result.text is None
    assert result.error_reason == "voice_pipeline_error:ValueError"


def test_deliver_voice_failure_sends_fallback_and_marks_processed(
    monkeypatch,
):
    sent = {}
    marked = {}

    async def fake_send(*, telefono, mensaje):
        sent["telefono"] = telefono
        sent["mensaje"] = mensaje

    def fake_mark(*, whatsapp_message_id, telefono):
        marked["whatsapp_message_id"] = whatsapp_message_id
        marked["telefono"] = telefono

    monkeypatch.setattr(
        inbound_voice.settings,
        "whatsapp_sending_enabled",
        True,
    )
    monkeypatch.setattr(inbound_voice, "send_whatsapp_message", fake_send)
    monkeypatch.setattr(inbound_voice, "mark_message_processed", fake_mark)
    monkeypatch.setattr(inbound_voice, "log_error", lambda **kwargs: None)

    response = asyncio.run(
        inbound_voice.deliver_voice_failure(
            telefono="573009450001",
            whatsapp_message_id="wamid.voice.failure.001",
            whatsapp_timestamp="1790000100",
            result=inbound_voice.InboundVoiceResult(
                text=None,
                status="error",
                error_reason="empty_transcription",
                latency_ms=300,
            ),
        )
    )

    assert response["status"] == "sent"
    assert response["processed_marked"] is True
    assert "No pude procesar" in sent["mensaje"]
    assert marked["whatsapp_message_id"] == "wamid.voice.failure.001"
