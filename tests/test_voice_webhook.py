import asyncio
from types import SimpleNamespace

import app.main as main


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
