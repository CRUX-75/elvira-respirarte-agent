from __future__ import annotations

import asyncio

from pathlib import Path
from types import SimpleNamespace

from app.models.human_escalation_event import (
    HumanEscalationStatus,
)
from app.services.human_escalation_config import (
    HumanEscalationConfig,
    load_human_escalation_config,
)
from app.services.human_escalation_event_service import (
    HumanEscalationDeliveryClaim,
)
from app.services.human_escalation_runtime import (
    dispatch_human_escalation_best_effort,
    send_human_escalation_whatsapp,
)


class FakeEventService:
    def __init__(self):
        self.event = None
        self.sent_provider_message_id = None

    def create_or_reuse(self, event):
        self.event = event
        return event

    def claim_for_delivery(
        self,
        *,
        event_id,
        lease_seconds,
    ):
        assert self.event is not None
        assert event_id == self.event.id
        assert lease_seconds > 0

        return HumanEscalationDeliveryClaim(
            event=self.event,
            token="claim-test",
        )

    def record_sent(
        self,
        *,
        claim,
        provider_message_id,
    ):
        self.sent_provider_message_id = (
            provider_message_id
        )

        return claim.event.model_copy(
            update={
                "status": HumanEscalationStatus.SENT,
                "retryable": False,
                "provider_message_id": (
                    provider_message_id
                ),
            }
        )

    def record_failed(
        self,
        *,
        claim,
        error_category,
        retryable,
    ):
        return claim.event.model_copy(
            update={
                "status": HumanEscalationStatus.FAILED,
                "last_error_category": error_category,
                "retryable": retryable,
            }
        )


def approved_result():
    return SimpleNamespace(
        escalation_required=True,
        next_action="escalate_unknown_service",
        nuevo_estado="ST_GENERAL",
    )


def test_lowercase_pydantic_settings_are_supported():
    config = load_human_escalation_config(
        settings_obj=SimpleNamespace(
            human_escalation_enabled=True,
            human_escalation_whatsapp_number=(
                "+57 300 000 0001"
            ),
        ),
        environ={},
    )

    assert config.enabled is True
    assert config.whatsapp_number == "573000000001"
    assert config.ready is True


def test_disabled_runtime_does_not_touch_repository():
    class ExplodingService:
        def create_or_reuse(self, event):
            raise AssertionError(
                "Repository must not be used."
            )

    result = asyncio.run(
        dispatch_human_escalation_best_effort(
            patient_id="patient-1",
            patient_name="Paciente",
            patient_phone="573000000002",
            inbound_whatsapp_message_id="wamid.test",
            result=approved_result(),
            conversation_state="ST_GENERAL",
            config=HumanEscalationConfig(
                enabled=False,
                whatsapp_number=None,
            ),
            event_service=ExplodingService(),
        )
    )

    assert result.outcome == "disabled"


def test_non_escalation_is_ignored():
    result = asyncio.run(
        dispatch_human_escalation_best_effort(
            patient_id="patient-1",
            patient_name="Paciente",
            patient_phone="573000000002",
            inbound_whatsapp_message_id="wamid.test",
            result=SimpleNamespace(
                escalation_required=False,
                next_action="answer_schedule",
            ),
            conversation_state="ST_GENERAL",
            config=HumanEscalationConfig(
                enabled=True,
                whatsapp_number="573000000001",
            ),
            event_service=FakeEventService(),
        )
    )

    assert result.outcome == "not_required"


def test_runtime_dispatches_using_safe_minimal_event():
    service = FakeEventService()
    send_calls = []

    async def fake_sender(
        *,
        to,
        message,
    ):
        send_calls.append(
            {
                "to": to,
                "message": message,
            }
        )

        return {
            "messages": [
                {
                    "id": "wamid.doctor",
                }
            ]
        }

    result = asyncio.run(
        dispatch_human_escalation_best_effort(
            patient_id="patient-1",
            patient_name="Paciente",
            patient_phone="573000000002",
            inbound_whatsapp_message_id=(
                "wamid.patient"
            ),
            result=approved_result(),
            conversation_state="ST_GENERAL",
            config=HumanEscalationConfig(
                enabled=True,
                whatsapp_number="573000000001",
            ),
            event_service=service,
            send_text=fake_sender,
        )
    )

    assert result.outcome == "sent"
    assert result.provider_message_id == "wamid.doctor"
    assert len(send_calls) == 1

    notification = send_calls[0]["message"]

    assert send_calls[0]["to"] == "573000000001"
    assert "Paciente: Paciente" in notification
    assert "Teléfono: 573000000002" in notification
    assert "Estado: ST_GENERAL" in notification
    assert "Requiere revisión humana." in notification


def test_invalid_source_identifier_is_contained():
    result = asyncio.run(
        dispatch_human_escalation_best_effort(
            patient_id="patient-1",
            patient_name="Paciente",
            patient_phone="573000000002",
            inbound_whatsapp_message_id="",
            result=approved_result(),
            conversation_state="ST_GENERAL",
            config=HumanEscalationConfig(
                enabled=True,
                whatsapp_number="573000000001",
            ),
            event_service=FakeEventService(),
        )
    )

    assert result.outcome == "orchestration_failed"
    assert result.retryable is False


def test_existing_whatsapp_transport_adapter(
    monkeypatch,
):
    captured = {}

    async def fake_whatsapp_send(
        telefono,
        mensaje,
    ):
        captured["telefono"] = telefono
        captured["mensaje"] = mensaje

        return {
            "messages": [
                {
                    "id": "wamid.adapter",
                }
            ]
        }

    monkeypatch.setattr(
        (
            "app.services.human_escalation_runtime."
            "send_whatsapp_message"
        ),
        fake_whatsapp_send,
    )

    response = asyncio.run(
        send_human_escalation_whatsapp(
            to="573000000001",
            message="Mensaje de prueba",
        )
    )

    assert captured == {
        "telefono": "573000000001",
        "mensaje": "Mensaje de prueba",
    }
    assert response["messages"][0]["id"] == (
        "wamid.adapter"
    )


def test_main_wiring_runs_after_patient_persistence():
    source = Path("app/main.py").read_text(
        encoding="utf-8"
    )

    dispatch_index = source.index(
        "await dispatch_human_escalation_best_effort("
    )

    state_index = source.rfind(
        "update_patient_state(",
        0,
        dispatch_index,
    )

    processed_index = source.rfind(
        "mark_message_processed(",
        0,
        dispatch_index,
    )

    assert state_index != -1
    assert processed_index != -1
    assert state_index < dispatch_index
    assert processed_index < dispatch_index
