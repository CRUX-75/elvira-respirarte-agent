from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.main as main


class FakeWhatsAppPayload:
    object = "whatsapp_business_account"

    def __init__(
        self,
        *,
        telefono: str = "4917655660163",
        mensaje: str = "Hola buenos días",
        nombre: str | None = "Nabit Mikan",
        whatsapp_message_id: str | None = "wamid-test-webhook-001",
        whatsapp_timestamp: str | None = "1710000000",
    ):
        self._extracted = {
            "telefono": telefono,
            "mensaje": mensaje,
            "nombre": nombre,
            "whatsapp_message_id": whatsapp_message_id,
            "whatsapp_timestamp": whatsapp_timestamp,
        }

    def extract_message(self):
        return self._extracted


def _patch_common(monkeypatch):
    monkeypatch.setattr(main, "log_interaction", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_ignored", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_error", lambda **kwargs: None)
    monkeypatch.setattr(main.settings, "whatsapp_sending_enabled", False, raising=False)


def test_webhook_ignores_duplicate_before_llm(monkeypatch):
    _patch_common(monkeypatch)

    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: True)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM/LangGraph must not be called for duplicate messages")

    monkeypatch.setattr(main, "traced_process_message", fail_if_called)

    payload = FakeWhatsAppPayload(whatsapp_message_id="wamid-duplicate-001")

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "ignored"
    assert response["reason"] == "duplicate_message"
    assert response["whatsapp_message_id"] == "wamid-duplicate-001"


def test_webhook_processes_new_message_and_persists(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "save_interaction": None,
        "update_patient_state": None,
        "update_patient_last_message": None,
        "mark_message_processed": None,
    }

    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: False)

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre=None: {
            "id": "patient-001",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )

    monkeypatch.setattr(
        main,
        "traced_process_message",
        lambda fn, message: SimpleNamespace(
            intent="general",
            respuesta="Hola, buenos días. ¿En qué le podemos ayudar?",
            nuevo_estado="ST_GENERAL",
            next_action="answer_general",
            state_reason="Mensaje general sin intención específica.",
            router_version="intent-v1",
            state_machine_version="sm-v1",
            kb_used=False,
            escalation_required=False,
        ),
    )

    def fake_save_interaction(**kwargs):
        calls["save_interaction"] = kwargs

    def fake_update_patient_state(**kwargs):
        calls["update_patient_state"] = kwargs

    def fake_update_patient_last_message(**kwargs):
        calls["update_patient_last_message"] = kwargs

    def fake_mark_message_processed(**kwargs):
        calls["mark_message_processed"] = kwargs

    monkeypatch.setattr(main, "save_interaction", fake_save_interaction)
    monkeypatch.setattr(main, "update_patient_state", fake_update_patient_state)
    monkeypatch.setattr(main, "update_patient_last_message", fake_update_patient_last_message)
    monkeypatch.setattr(main, "mark_message_processed", fake_mark_message_processed)

    payload = FakeWhatsAppPayload(
        mensaje="Hola buenos días",
        whatsapp_message_id="wamid-new-001",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "sending_skipped"
    assert response["intent"] == "general"
    assert response["estado_anterior"] == "ST_INIT"
    assert response["nuevo_estado"] == "ST_GENERAL"
    assert response["patient_id"] == "patient-001"

    assert calls["save_interaction"]["patient_id"] == "patient-001"
    assert calls["save_interaction"]["mensaje_usuario"] == "Hola buenos días"
    assert calls["save_interaction"]["delivery_status"] == "sending_skipped"
    assert calls["save_interaction"]["whatsapp_message_id"] == "wamid-new-001"

    assert calls["update_patient_state"] == {
        "patient_id": "patient-001",
        "nuevo_estado": "ST_GENERAL",
    }

    assert calls["update_patient_last_message"] == {
        "patient_id": "patient-001",
    }

    assert calls["mark_message_processed"] == {
        "whatsapp_message_id": "wamid-new-001",
        "telefono": "4917655660163",
    }


def test_webhook_uses_persisted_patient_state_from_db(monkeypatch):
    _patch_common(monkeypatch)

    captured = {}

    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: False)

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre=None: {
            "id": "patient-002",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_CITA_FECHA",
            "opt_out": False,
        },
    )

    def fake_traced_process_message(fn, message):
        captured["estado_actual"] = message.estado_actual
        captured["telefono"] = message.telefono
        captured["mensaje"] = message.mensaje

        return SimpleNamespace(
            intent="cita",
            respuesta="Perfecto. ¿Para qué fecha desea la cita?",
            nuevo_estado="ST_CITA_FRANJA",
            next_action="ask_appointment_time_slot",
            state_reason="Paciente ya estaba en flujo de cita.",
            router_version="intent-v1",
            state_machine_version="sm-v1",
            kb_used=False,
            escalation_required=False,
        )

    monkeypatch.setattr(main, "traced_process_message", fake_traced_process_message)
    monkeypatch.setattr(main, "save_interaction", lambda **kwargs: None)
    monkeypatch.setattr(main, "update_patient_state", lambda **kwargs: None)
    monkeypatch.setattr(main, "update_patient_last_message", lambda **kwargs: None)
    monkeypatch.setattr(main, "mark_message_processed", lambda **kwargs: None)

    payload = FakeWhatsAppPayload(
        mensaje="Mañana en la tarde",
        whatsapp_message_id="wamid-state-001",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert captured["estado_actual"] == "ST_CITA_FECHA"
    assert captured["mensaje"] == "Mañana en la tarde"

    assert response["estado_anterior"] == "ST_CITA_FECHA"
    assert response["nuevo_estado"] == "ST_CITA_FRANJA"


def test_webhook_processing_error_returns_safe_response(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "update_patient_state": False,
        "mark_message_processed": False,
        "send_whatsapp_message": False,
    }

    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: False)

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre=None: {
            "id": "patient-error-001",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )

    def fail_processing(fn, message):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(main, "traced_process_message", fail_processing)

    def fake_update_patient_state(**kwargs):
        calls["update_patient_state"] = True

    def fake_mark_message_processed(**kwargs):
        calls["mark_message_processed"] = True

    async def fake_send_whatsapp_message(*args, **kwargs):
        calls["send_whatsapp_message"] = True

    monkeypatch.setattr(main, "update_patient_state", fake_update_patient_state)
    monkeypatch.setattr(main, "mark_message_processed", fake_mark_message_processed)
    monkeypatch.setattr(main, "send_whatsapp_message", fake_send_whatsapp_message)

    payload = FakeWhatsAppPayload(
        mensaje="Hola",
        whatsapp_message_id="wamid-error-001",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "error"
    assert response["reason"] == "processing_failed"
    assert response["delivery_status"] == "not_sent"
    assert response["whatsapp_message_id"] == "wamid-error-001"
    assert response["processed_marked"] is False

    assert calls["update_patient_state"] is False
    assert calls["mark_message_processed"] is False
    assert calls["send_whatsapp_message"] is False


def test_webhook_processing_error_returns_safe_response(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "update_patient_state": False,
        "mark_message_processed": False,
        "send_whatsapp_message": False,
    }

    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: False)

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre=None: {
            "id": "patient-error-001",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )

    def fail_processing(fn, message):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(main, "traced_process_message", fail_processing)

    def fake_update_patient_state(**kwargs):
        calls["update_patient_state"] = True

    def fake_mark_message_processed(**kwargs):
        calls["mark_message_processed"] = True

    async def fake_send_whatsapp_message(*args, **kwargs):
        calls["send_whatsapp_message"] = True

    monkeypatch.setattr(main, "update_patient_state", fake_update_patient_state)
    monkeypatch.setattr(main, "mark_message_processed", fake_mark_message_processed)
    monkeypatch.setattr(main, "send_whatsapp_message", fake_send_whatsapp_message)

    payload = FakeWhatsAppPayload(
        mensaje="Hola",
        whatsapp_message_id="wamid-error-001",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "error"
    assert response["reason"] == "processing_failed"
    assert response["delivery_status"] == "not_sent"
    assert response["whatsapp_message_id"] == "wamid-error-001"
    assert response["processed_marked"] is False

    assert calls["update_patient_state"] is False
    assert calls["mark_message_processed"] is False
    assert calls["send_whatsapp_message"] is False


def test_webhook_whatsapp_send_error_does_not_update_state_or_mark_processed(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "save_interaction": None,
        "update_patient_state": False,
        "update_patient_last_message": False,
        "mark_message_processed": False,
    }

    monkeypatch.setattr(main.settings, "whatsapp_sending_enabled", True, raising=False)
    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: False)

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre=None: {
            "id": "patient-send-error-001",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )

    monkeypatch.setattr(
        main,
        "traced_process_message",
        lambda fn, message: SimpleNamespace(
            intent="general",
            respuesta="Hola, con gusto le ayudamos.",
            nuevo_estado="ST_GENERAL",
            next_action="answer_general",
            state_reason="Mensaje general.",
            router_version="intent-v1",
            state_machine_version="sm-v1",
            kb_used=False,
            escalation_required=False,
        ),
    )

    async def fail_send_whatsapp_message(*args, **kwargs):
        raise RuntimeError("WhatsApp API unavailable")

    def fake_save_interaction(**kwargs):
        calls["save_interaction"] = kwargs

    def fake_update_patient_state(**kwargs):
        calls["update_patient_state"] = True

    def fake_update_patient_last_message(**kwargs):
        calls["update_patient_last_message"] = True

    def fake_mark_message_processed(**kwargs):
        calls["mark_message_processed"] = True

    monkeypatch.setattr(main, "send_whatsapp_message", fail_send_whatsapp_message)
    monkeypatch.setattr(main, "save_interaction", fake_save_interaction)
    monkeypatch.setattr(main, "update_patient_state", fake_update_patient_state)
    monkeypatch.setattr(main, "update_patient_last_message", fake_update_patient_last_message)
    monkeypatch.setattr(main, "mark_message_processed", fake_mark_message_processed)

    payload = FakeWhatsAppPayload(
        mensaje="Hola",
        whatsapp_message_id="wamid-send-error-001",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "error"
    assert response["reason"] == "whatsapp_send_failed"
    assert response["delivery_status"] == "send_failed"
    assert response["processed_marked"] is False
    assert response["state_updated"] is False

    assert calls["save_interaction"]["delivery_status"] == "send_failed"
    assert calls["save_interaction"]["nuevo_estado"] == "ST_INIT"
    assert calls["save_interaction"]["respuesta_elvira"].startswith("[WHATSAPP_SEND_FAILED]")

    assert calls["update_patient_state"] is False
    assert calls["update_patient_last_message"] is False
    assert calls["mark_message_processed"] is False


def test_webhook_deduplication_error_returns_safe_response_before_llm(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "traced_process_message": False,
        "send_whatsapp_message": False,
        "mark_message_processed": False,
    }

    def fail_is_message_processed(whatsapp_message_id):
        raise RuntimeError("Database unavailable during deduplication")

    def fake_traced_process_message(*args, **kwargs):
        calls["traced_process_message"] = True
        raise AssertionError("LangGraph/LLM must not be called if deduplication fails")

    async def fake_send_whatsapp_message(*args, **kwargs):
        calls["send_whatsapp_message"] = True

    def fake_mark_message_processed(*args, **kwargs):
        calls["mark_message_processed"] = True

    monkeypatch.setattr(main, "is_message_processed", fail_is_message_processed)
    monkeypatch.setattr(main, "traced_process_message", fake_traced_process_message)
    monkeypatch.setattr(main, "send_whatsapp_message", fake_send_whatsapp_message)
    monkeypatch.setattr(main, "mark_message_processed", fake_mark_message_processed)

    payload = FakeWhatsAppPayload(
        mensaje="Hola",
        whatsapp_message_id="wamid-dedup-error-001",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "error"
    assert response["reason"] == "deduplication_check_failed"
    assert response["delivery_status"] == "not_sent"
    assert response["processed_marked"] is False
    assert response["whatsapp_message_id"] == "wamid-dedup-error-001"

    assert calls["traced_process_message"] is False
    assert calls["send_whatsapp_message"] is False
    assert calls["mark_message_processed"] is False


def test_webhook_payload_extraction_error_returns_safe_response(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "is_message_processed": False,
        "traced_process_message": False,
        "send_whatsapp_message": False,
    }

    class BrokenPayload:
        object = "whatsapp_business_account"

        def extract_message(self):
            raise RuntimeError("Malformed Meta payload")

    def fake_is_message_processed(*args, **kwargs):
        calls["is_message_processed"] = True
        return False

    def fake_traced_process_message(*args, **kwargs):
        calls["traced_process_message"] = True
        raise AssertionError("LLM must not be called if payload extraction fails")

    async def fake_send_whatsapp_message(*args, **kwargs):
        calls["send_whatsapp_message"] = True

    monkeypatch.setattr(main, "is_message_processed", fake_is_message_processed)
    monkeypatch.setattr(main, "traced_process_message", fake_traced_process_message)
    monkeypatch.setattr(main, "send_whatsapp_message", fake_send_whatsapp_message)

    response = asyncio.run(main.receive_webhook(BrokenPayload()))

    assert response["status"] == "error"
    assert response["reason"] == "payload_extraction_failed"
    assert response["delivery_status"] == "not_sent"
    assert response["processed_marked"] is False

    assert calls["is_message_processed"] is False
    assert calls["traced_process_message"] is False
    assert calls["send_whatsapp_message"] is False


def test_webhook_missing_required_fields_returns_safe_ignored_response(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "is_message_processed": False,
        "traced_process_message": False,
        "send_whatsapp_message": False,
    }

    class MissingFieldsPayload:
        object = "whatsapp_business_account"

        def extract_message(self):
            return {
                "nombre": "Paciente Test",
                "whatsapp_message_id": "wamid-missing-fields-001",
                "whatsapp_timestamp": "1710000000",
            }

    def fake_is_message_processed(*args, **kwargs):
        calls["is_message_processed"] = True
        return False

    def fake_traced_process_message(*args, **kwargs):
        calls["traced_process_message"] = True
        raise AssertionError("LLM must not be called if required fields are missing")

    async def fake_send_whatsapp_message(*args, **kwargs):
        calls["send_whatsapp_message"] = True

    monkeypatch.setattr(main, "is_message_processed", fake_is_message_processed)
    monkeypatch.setattr(main, "traced_process_message", fake_traced_process_message)
    monkeypatch.setattr(main, "send_whatsapp_message", fake_send_whatsapp_message)

    response = asyncio.run(main.receive_webhook(MissingFieldsPayload()))

    assert response["status"] == "ignored"
    assert response["reason"] == "missing_required_message_fields"
    assert response["delivery_status"] == "not_sent"
    assert response["whatsapp_message_id"] == "wamid-missing-fields-001"
    assert response["processed_marked"] is False

    assert calls["is_message_processed"] is False
    assert calls["traced_process_message"] is False
    assert calls["send_whatsapp_message"] is False


def test_webhook_persistence_error_returns_safe_response_without_marking_processed(monkeypatch):
    _patch_common(monkeypatch)

    calls = {
        "update_patient_state": False,
        "update_patient_last_message": False,
        "mark_message_processed": False,
    }

    monkeypatch.setattr(main.settings, "whatsapp_sending_enabled", False, raising=False)
    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: False)

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre=None: {
            "id": "patient-persistence-error-001",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )

    monkeypatch.setattr(
        main,
        "traced_process_message",
        lambda fn, message: SimpleNamespace(
            intent="general",
            respuesta="Hola, con gusto le ayudamos.",
            nuevo_estado="ST_GENERAL",
            next_action="answer_general",
            state_reason="Mensaje general.",
            router_version="intent-v1",
            state_machine_version="sm-v1",
            kb_used=False,
            escalation_required=False,
        ),
    )

    def fail_save_interaction(**kwargs):
        raise RuntimeError("Database unavailable during interaction save")

    def fake_update_patient_state(**kwargs):
        calls["update_patient_state"] = True

    def fake_update_patient_last_message(**kwargs):
        calls["update_patient_last_message"] = True

    def fake_mark_message_processed(**kwargs):
        calls["mark_message_processed"] = True

    monkeypatch.setattr(main, "save_interaction", fail_save_interaction)
    monkeypatch.setattr(main, "update_patient_state", fake_update_patient_state)
    monkeypatch.setattr(main, "update_patient_last_message", fake_update_patient_last_message)
    monkeypatch.setattr(main, "mark_message_processed", fake_mark_message_processed)

    payload = FakeWhatsAppPayload(
        mensaje="Hola",
        whatsapp_message_id="wamid-persistence-error-001",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "error"
    assert response["reason"] == "processing_failed"
    assert response["delivery_status"] == "not_sent"
    assert response["processed_marked"] is False

    assert calls["update_patient_state"] is False
    assert calls["update_patient_last_message"] is False
    assert calls["mark_message_processed"] is False
