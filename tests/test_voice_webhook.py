import asyncio
import pytest
from types import SimpleNamespace

import app.main as main


@pytest.fixture(autouse=True)
def stub_voice_processing_claim(monkeypatch):
    monkeypatch.setattr(
        main,
        "try_claim_voice_processing",
        lambda **kwargs: SimpleNamespace(
            whatsapp_message_id=kwargs["whatsapp_message_id"],
            claim_token="test-claim-token",
            lease_expires_at=None,
        ),
    )


class FakeVoicePayload:
    def extract_message(self):
        return {
            "telefono": "573009450001",
            "mensaje": None,
            "nombre": "Paciente Voz",
            "msg_type": "audio",
            "whatsapp_message_id": "wamid.voice.webhook.001",
            "whatsapp_timestamp": "1790000200",
            "media_id": "media-voice-001",
            "mime_type": "audio/ogg",
            "sha256": "expected-sha",
            "voice": True,
        }


def test_voice_webhook_is_ignored_when_feature_flag_is_disabled(monkeypatch):
    monkeypatch.setattr(main.settings, "voice_input_enabled", False)
    monkeypatch.setattr(main, "is_message_processed", lambda value: False)
    monkeypatch.setattr(main, "log_ignored", lambda **kwargs: None)

    response = asyncio.run(main.receive_webhook(FakeVoicePayload()))

    assert response["status"] == "ignored"
    assert response["reason"] == "voice_input_disabled"
    assert response["processed_marked"] is False


def test_voice_transcript_enters_existing_deterministic_core(monkeypatch):
    captured = {}

    async def fake_voice_processing(extracted):
        return SimpleNamespace(
            text="Quiero pedir una cita",
            status="success",
            error_reason=None,
            latency_ms=110,
        )

    def fake_traced_process(function, message):
        captured["mensaje"] = message.mensaje
        return SimpleNamespace(
            respuesta="Con gusto le ayudo.",
            intent="solicitud_cita",
            nuevo_estado="ST_INIT",
        )

    monkeypatch.setattr(main.settings, "voice_input_enabled", True)
    monkeypatch.setattr(main.settings, "whatsapp_sending_enabled", False)
    monkeypatch.setattr(main, "is_message_processed", lambda value: False)
    monkeypatch.setattr(
        main,
        "process_inbound_voice_note",
        fake_voice_processing,
    )
    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda **kwargs: {
            "id": "patient-voice-001",
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )
    monkeypatch.setattr(main, "traced_process_message", fake_traced_process)
    monkeypatch.setattr(
        main,
        "_apply_appointment_request_runtime",
        lambda **kwargs: (
            kwargs["result"],
            SimpleNamespace(reason="not_applicable"),
            None,
        ),
    )
    monkeypatch.setattr(main, "save_interaction", lambda **kwargs: None)
    monkeypatch.setattr(main, "update_patient_state", lambda **kwargs: None)
    monkeypatch.setattr(
        main,
        "update_patient_last_message",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(main, "mark_message_processed", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_interaction", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_ignored", lambda **kwargs: None)

    response = asyncio.run(main.receive_webhook(FakeVoicePayload()))

    assert captured["mensaje"] == "Quiero pedir una cita"
    assert response["status"] == "sending_skipped"
    assert response["intent"] == "solicitud_cita"


def test_audio_webhook_uses_voice_delivery_when_flags_allow_it(
    monkeypatch,
):
    captured = {}

    async def fake_voice_processing(extracted):
        return SimpleNamespace(
            text="Quiero pedir una cita",
            status="success",
            error_reason=None,
            latency_ms=100,
        )

    async def fake_read_and_typing(**kwargs):
        return {}

    async def fake_sleep(seconds):
        return None

    async def fake_voice_delivery(*, telefono, whatsapp_message_id, response_text):
        captured["telefono"] = telefono
        captured["whatsapp_message_id"] = whatsapp_message_id
        captured["response_text"] = response_text
        return SimpleNamespace(
            delivery_status="sent",
            reply_mode="voice",
            voice_fallback_used=False,
        )

    async def unexpected_text_send(**kwargs):
        raise AssertionError("Direct text sender must not run")

    def fake_traced_process(function, message):
        return SimpleNamespace(
            respuesta="Con gusto le ayudo.",
            intent="solicitud_cita",
            nuevo_estado="ST_INIT",
        )

    monkeypatch.setattr(main.settings, "voice_input_enabled", True)
    monkeypatch.setattr(main.settings, "voice_replies_enabled", True)
    monkeypatch.setattr(main.settings, "voice_reply_to_audio_only", True)
    monkeypatch.setattr(main.settings, "whatsapp_sending_enabled", True)
    monkeypatch.setattr(main, "is_message_processed", lambda value: False)
    monkeypatch.setattr(
        main,
        "process_inbound_voice_note",
        fake_voice_processing,
    )
    monkeypatch.setattr(
        main,
        "mark_whatsapp_message_read_and_show_typing",
        fake_read_and_typing,
    )
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(main, "deliver_voice_reply", fake_voice_delivery)
    monkeypatch.setattr(
        main,
        "send_whatsapp_message",
        unexpected_text_send,
    )
    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda **kwargs: {
            "id": "patient-voice-002",
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )
    monkeypatch.setattr(main, "traced_process_message", fake_traced_process)
    monkeypatch.setattr(
        main,
        "_apply_appointment_request_runtime",
        lambda **kwargs: (
            kwargs["result"],
            SimpleNamespace(reason="not_applicable"),
            None,
        ),
    )
    monkeypatch.setattr(main, "save_interaction", lambda **kwargs: None)
    monkeypatch.setattr(main, "update_patient_state", lambda **kwargs: None)
    monkeypatch.setattr(
        main,
        "update_patient_last_message",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(main, "mark_message_processed", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_interaction", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_ignored", lambda **kwargs: None)

    response = asyncio.run(main.receive_webhook(FakeVoicePayload()))

    assert captured == {
        "telefono": "573009450001",
        "whatsapp_message_id": "wamid.voice.webhook.001",
        "response_text": "Con gusto le ayudo.",
    }
    assert response["status"] == "sent"
    assert response["reply_mode"] == "voice"
    assert response["voice_fallback_used"] is False


def test_voice_webhook_ignores_active_processing_claim(monkeypatch):
    monkeypatch.setattr(main.settings, "voice_input_enabled", True)
    monkeypatch.setattr(main, "is_message_processed", lambda value: False)
    monkeypatch.setattr(
        main,
        "try_claim_voice_processing",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(main, "log_ignored", lambda **kwargs: None)

    async def unexpected_voice_processing(extracted):
        raise AssertionError("Media and STT must not run")

    monkeypatch.setattr(
        main,
        "process_inbound_voice_note",
        unexpected_voice_processing,
    )

    response = asyncio.run(main.receive_webhook(FakeVoicePayload()))

    assert response == {
        "status": "ignored",
        "reason": "voice_processing_in_progress",
        "whatsapp_message_id": "wamid.voice.webhook.001",
        "processed_marked": False,
    }


@pytest.fixture(autouse=True)
def stub_voice_phone_allowlist(monkeypatch):
    monkeypatch.setattr(
        main,
        "is_voice_phone_allowed",
        lambda telefono: True,
    )


def test_voice_webhook_rejects_phone_outside_allowlist(monkeypatch):
    monkeypatch.setattr(main.settings, "voice_input_enabled", True)
    monkeypatch.setattr(main, "is_message_processed", lambda value: False)
    monkeypatch.setattr(
        main,
        "is_voice_phone_allowed",
        lambda telefono: False,
    )
    monkeypatch.setattr(main, "log_ignored", lambda **kwargs: None)

    def unexpected_claim(**kwargs):
        raise AssertionError("Lease must not be acquired")

    monkeypatch.setattr(
        main,
        "try_claim_voice_processing",
        unexpected_claim,
    )

    response = asyncio.run(main.receive_webhook(FakeVoicePayload()))

    assert response == {
        "status": "ignored",
        "reason": "voice_phone_not_allowed",
        "whatsapp_message_id": "wamid.voice.webhook.001",
        "processed_marked": False,
    }
