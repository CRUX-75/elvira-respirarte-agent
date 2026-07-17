import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import app.services.outbound_voice as outbound_voice


def enable_voice_replies(monkeypatch):
    monkeypatch.setattr(
        outbound_voice.settings,
        "voice_replies_enabled",
        True,
    )
    monkeypatch.setattr(
        outbound_voice.settings,
        "voice_reply_to_audio_only",
        True,
    )


def test_should_send_voice_reply_respects_flags(monkeypatch):
    monkeypatch.setattr(
        outbound_voice.settings,
        "voice_replies_enabled",
        False,
    )

    assert outbound_voice.should_send_voice_reply("audio") is False

    enable_voice_replies(monkeypatch)

    assert outbound_voice.should_send_voice_reply("audio") is True
    assert outbound_voice.should_send_voice_reply("text") is False


def test_deliver_voice_reply_synthesizes_uploads_and_sends(
    monkeypatch,
    tmp_path,
):
    enable_voice_replies(monkeypatch)
    calls = []
    audio_path = tmp_path / "reply.ogg"
    audio_path.write_bytes(b"OggSvoice-data")

    async def fake_synthesis(response_text):
        calls.append(("tts", response_text))
        return SimpleNamespace(
            audio_content=b"OggSvoice-data",
            model="gpt-4o-mini-tts",
            voice="marin",
            response_format="opus",
            status="success",
            latency_ms=120,
            error_reason=None,
        )

    @contextmanager
    def fake_temporary(audio_content):
        calls.append(("temporary", audio_content))
        yield audio_path

    async def fake_upload(path):
        calls.append(("upload", path))
        return SimpleNamespace(media_id="media-reply-001")

    async def fake_voice_send(*, telefono, media_id):
        calls.append(("voice", telefono, media_id))

    async def unexpected_text_send(**kwargs):
        raise AssertionError("Text fallback must not run")

    monkeypatch.setattr(
        outbound_voice,
        "synthesize_voice_reply",
        fake_synthesis,
    )
    monkeypatch.setattr(
        outbound_voice,
        "temporary_synthesized_voice_note",
        fake_temporary,
    )
    monkeypatch.setattr(
        outbound_voice,
        "upload_whatsapp_voice_media",
        fake_upload,
    )
    monkeypatch.setattr(
        outbound_voice,
        "send_whatsapp_voice_note",
        fake_voice_send,
    )
    monkeypatch.setattr(
        outbound_voice,
        "send_whatsapp_message",
        unexpected_text_send,
    )

    result = asyncio.run(
        outbound_voice.deliver_voice_reply(
            telefono="573009450001",
            response_text="Respuesta determinística.",
        )
    )

    assert result.delivery_status == "sent"
    assert result.reply_mode == "voice"
    assert result.voice_fallback_used is False
    assert calls == [
        ("tts", "Respuesta determinística."),
        ("temporary", b"OggSvoice-data"),
        ("upload", audio_path),
        ("voice", "573009450001", "media-reply-001"),
    ]


def test_tts_failure_falls_back_to_existing_text(monkeypatch):
    enable_voice_replies(monkeypatch)
    sent = {}

    async def failed_synthesis(response_text):
        return SimpleNamespace(
            audio_content=None,
            model="gpt-4o-mini-tts",
            voice="marin",
            response_format="opus",
            status="error",
            latency_ms=90,
            error_reason="provider_error:RuntimeError",
        )

    async def fake_text_send(*, telefono, mensaje):
        sent["telefono"] = telefono
        sent["mensaje"] = mensaje

    monkeypatch.setattr(
        outbound_voice,
        "synthesize_voice_reply",
        failed_synthesis,
    )
    monkeypatch.setattr(
        outbound_voice,
        "send_whatsapp_message",
        fake_text_send,
    )

    result = asyncio.run(
        outbound_voice.deliver_voice_reply(
            telefono="573009450001",
            response_text="Respuesta determinística.",
        )
    )

    assert result.reply_mode == "text"
    assert result.voice_fallback_used is True
    assert result.voice_error_reason == "provider_error:RuntimeError"
    assert sent["mensaje"] == "Respuesta determinística."


def test_voice_send_failure_falls_back_without_new_tts(
    monkeypatch,
    tmp_path,
):
    enable_voice_replies(monkeypatch)
    calls = {"tts": 0, "text": 0}
    audio_path = tmp_path / "reply.ogg"
    audio_path.write_bytes(b"OggSvoice-data")

    async def fake_synthesis(response_text):
        calls["tts"] += 1
        return SimpleNamespace(
            audio_content=b"OggSvoice-data",
            model="gpt-4o-mini-tts",
            voice="marin",
            response_format="opus",
            status="success",
            latency_ms=100,
            error_reason=None,
        )

    @contextmanager
    def fake_temporary(audio_content):
        yield audio_path

    async def fake_upload(path):
        return SimpleNamespace(media_id="media-reply-002")

    async def failed_voice_send(**kwargs):
        raise RuntimeError("Meta failure")

    async def fake_text_send(*, telefono, mensaje):
        calls["text"] += 1
        assert mensaje == "Respuesta determinística."

    monkeypatch.setattr(
        outbound_voice,
        "synthesize_voice_reply",
        fake_synthesis,
    )
    monkeypatch.setattr(
        outbound_voice,
        "temporary_synthesized_voice_note",
        fake_temporary,
    )
    monkeypatch.setattr(
        outbound_voice,
        "upload_whatsapp_voice_media",
        fake_upload,
    )
    monkeypatch.setattr(
        outbound_voice,
        "send_whatsapp_voice_note",
        failed_voice_send,
    )
    monkeypatch.setattr(
        outbound_voice,
        "send_whatsapp_message",
        fake_text_send,
    )

    result = asyncio.run(
        outbound_voice.deliver_voice_reply(
            telefono="573009450001",
            response_text="Respuesta determinística.",
        )
    )

    assert calls == {"tts": 1, "text": 1}
    assert result.reply_mode == "text"
    assert result.voice_fallback_used is True
    assert result.voice_error_reason == (
        "voice_delivery_error:RuntimeError"
    )


def test_voice_and_text_delivery_failure_raises(monkeypatch):
    enable_voice_replies(monkeypatch)

    async def failed_synthesis(response_text):
        return SimpleNamespace(
            audio_content=None,
            model="gpt-4o-mini-tts",
            voice="marin",
            response_format="opus",
            status="error",
            latency_ms=80,
            error_reason="empty_synthesized_audio",
        )

    async def failed_text_send(**kwargs):
        raise RuntimeError("Text send failed")

    monkeypatch.setattr(
        outbound_voice,
        "synthesize_voice_reply",
        failed_synthesis,
    )
    monkeypatch.setattr(
        outbound_voice,
        "send_whatsapp_message",
        failed_text_send,
    )

    try:
        asyncio.run(
            outbound_voice.deliver_voice_reply(
                telefono="573009450001",
                response_text="Respuesta determinística.",
            )
        )
    except outbound_voice.VoiceDeliveryError as exc:
        assert str(exc) == "Voice and text delivery both failed"
    else:
        raise AssertionError("Expected VoiceDeliveryError")
