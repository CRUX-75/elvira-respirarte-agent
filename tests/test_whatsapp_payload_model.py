from app.models.whatsapp import WhatsAppPayload


def test_extract_message_from_meta_text_payload():
    payload = WhatsAppPayload(
        object="whatsapp_business_account",
        entry=[
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "573001112233",
                                "phone_number_id": "1234567890",
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Paciente Meta Test",
                                    },
                                    "wa_id": "573009450001",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "573009450001",
                                    "id": "wamid.p6f945.meta.001",
                                    "timestamp": "1790000000",
                                    "text": {
                                        "body": "Quiero pedir una cita",
                                    },
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    )

    extracted = payload.extract_message()

    assert extracted == {
        "telefono": "573009450001",
        "mensaje": "Quiero pedir una cita",
        "nombre": "Paciente Meta Test",
        "msg_type": "text",
        "whatsapp_message_id": "wamid.p6f945.meta.001",
        "whatsapp_timestamp": "1790000000",
    }


def test_extract_message_returns_none_for_status_notification():
    payload = WhatsAppPayload(
        object="whatsapp_business_account",
        entry=[
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": "wamid.status.001",
                                    "status": "delivered",
                                    "timestamp": "1790000001",
                                    "recipient_id": "573009450001",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    )

    assert payload.extract_message() is None


def test_extract_message_returns_none_for_unsupported_message_type():
    payload = WhatsAppPayload(
        object="whatsapp_business_account",
        entry=[
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Paciente Meta Test",
                                    },
                                    "wa_id": "573009450001",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "573009450001",
                                    "id": "wamid.p6f945.audio.001",
                                    "timestamp": "1790000002",
                                    "type": "audio",
                                    "audio": {
                                        "id": "audio-file-id",
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    )

    assert payload.extract_message() is None


def build_meta_text_payload(
    *,
    telefono: str = "573009450001",
    nombre: str = "Paciente Meta Test",
    mensaje: str = "Quiero pedir una cita",
    wamid: str = "wamid.p6f945.webhook.001",
    timestamp: str = "1790000003",
) -> WhatsAppPayload:
    return WhatsAppPayload(
        object="whatsapp_business_account",
        entry=[
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "573001112233",
                                "phone_number_id": "1234567890",
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": nombre,
                                    },
                                    "wa_id": telefono,
                                }
                            ],
                            "messages": [
                                {
                                    "from": telefono,
                                    "id": wamid,
                                    "timestamp": timestamp,
                                    "text": {
                                        "body": mensaje,
                                    },
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    )


def test_real_webhook_accepts_meta_text_payload_with_sending_disabled(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    import app.main as main

    calls = {
        "save_interaction": None,
        "update_patient_state": None,
        "update_patient_last_message": None,
        "mark_message_processed": None,
    }

    monkeypatch.setattr(main.settings, "whatsapp_sending_enabled", False, raising=False)
    monkeypatch.setattr(main, "log_interaction", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_ignored", lambda **kwargs: None)
    monkeypatch.setattr(main, "log_error", lambda **kwargs: None)
    monkeypatch.setattr(main, "is_message_processed", lambda whatsapp_message_id: False)

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre=None: {
            "id": "patient-p6f945-meta-001",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_INIT",
            "opt_out": False,
            "appointment_context": None,
        },
    )

    monkeypatch.setattr(
        main,
        "traced_process_message",
        lambda fn, message: SimpleNamespace(
            intent="cita",
            respuesta="Claro, con muchísimo gusto. ¿Para qué día le gustaría agendar su cita?",
            nuevo_estado="ST_CITA_FECHA",
            next_action="ask_preferred_date",
            state_reason="Paciente quiere agendar una cita.",
            router_version="intent-v1",
            state_machine_version="sm-v1",
            kb_used=True,
            escalation_required=False,
            opt_out=None,
        ),
    )

    monkeypatch.setattr(
        main,
        "save_interaction",
        lambda **kwargs: calls.update(save_interaction=kwargs),
    )
    monkeypatch.setattr(
        main,
        "update_patient_state",
        lambda **kwargs: calls.update(update_patient_state=kwargs),
    )
    monkeypatch.setattr(
        main,
        "update_patient_last_message",
        lambda **kwargs: calls.update(update_patient_last_message=kwargs),
    )
    monkeypatch.setattr(
        main,
        "mark_message_processed",
        lambda **kwargs: calls.update(mark_message_processed=kwargs),
    )

    payload = build_meta_text_payload(
        telefono="573009450001",
        nombre="Paciente Meta Test",
        mensaje="Quiero pedir una cita",
        wamid="wamid.p6f945.webhook.001",
        timestamp="1790000003",
    )

    response = asyncio.run(main.receive_webhook(payload))

    assert response["status"] == "sending_skipped"
    assert response["intent"] == "cita"
    assert response["estado_anterior"] == "ST_INIT"
    assert response["nuevo_estado"] == "ST_CITA_FECHA"
    assert response["whatsapp_sending_enabled"] is False
    assert response["whatsapp_message_id"] == "wamid.p6f945.webhook.001"
    assert response["whatsapp_timestamp"] == "1790000003"
    assert response["patient_id"] == "patient-p6f945-meta-001"

    assert calls["save_interaction"]["telefono"] == "573009450001"
    assert calls["save_interaction"]["nombre"] == "Paciente Meta Test"
    assert calls["save_interaction"]["mensaje_usuario"] == "Quiero pedir una cita"
    assert calls["save_interaction"]["delivery_status"] == "sending_skipped"
    assert calls["save_interaction"]["whatsapp_message_id"] == "wamid.p6f945.webhook.001"
    assert calls["save_interaction"]["whatsapp_timestamp"] == "1790000003"

    assert calls["update_patient_state"] == {
        "patient_id": "patient-p6f945-meta-001",
        "nuevo_estado": "ST_CITA_FECHA",
        "opt_out": None,
    }

    assert calls["update_patient_last_message"] == {
        "patient_id": "patient-p6f945-meta-001",
    }

    assert calls["mark_message_processed"] == {
        "whatsapp_message_id": "wamid.p6f945.webhook.001",
        "telefono": "573009450001",
    }
