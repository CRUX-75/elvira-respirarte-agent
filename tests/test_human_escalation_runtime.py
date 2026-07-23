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
    process_human_escalation_status_updates_best_effort,
)


class FakeEventService:
    def __init__(self):
        self.event = None
        self.accepted_provider_message_id = None
        self.status_calls = []

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

    def record_accepted(
        self,
        *,
        claim,
        provider_message_id,
    ):
        self.accepted_provider_message_id = provider_message_id

        return claim.event.model_copy(
            update={
                "status": HumanEscalationStatus.ACCEPTED,
                "retryable": False,
                "provider_message_id": provider_message_id,
            }
        )

    def record_provider_status(
        self,
        *,
        provider_message_id,
        provider_status,
        occurred_at,
        error_category,
    ):
        self.status_calls.append(
            {
                "provider_message_id": provider_message_id,
                "provider_status": provider_status,
                "occurred_at": occurred_at,
                "error_category": error_category,
            }
        )
        return SimpleNamespace(id="event-status")

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
        template_name,
        language_code,
        body_parameters,
    ):
        send_calls.append(
            {
                "to": to,
                "template_name": template_name,
                "language_code": language_code,
                "body_parameters": body_parameters,
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
            send_template=fake_sender,
        )
    )

    assert result.outcome == "accepted"
    assert result.provider_message_id == "wamid.doctor"
    assert len(send_calls) == 1

    assert send_calls[0]["to"] == "573000000001"
    assert send_calls[0]["template_name"] == "revision_humana"
    assert send_calls[0]["language_code"] == "es_CO"
    parameters = send_calls[0]["body_parameters"]
    assert len(parameters) == 10
    assert parameters[0] == "Paciente"
    assert parameters[1] == "573000000002"
    assert parameters[7] == "ST_GENERAL"


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
        *,
        telefono,
        template_name,
        language_code,
        body_parameters,
    ):
        captured.update(
            telefono=telefono,
            template_name=template_name,
            language_code=language_code,
            body_parameters=body_parameters,
        )

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
            "send_whatsapp_template_message"
        ),
        fake_whatsapp_send,
    )

    response = asyncio.run(
        send_human_escalation_whatsapp(
            to="573000000001",
            template_name="revision_humana",
            language_code="es_CO",
            body_parameters=[f"valor-{index}" for index in range(1, 11)],
        )
    )

    assert captured == {
        "telefono": "573000000001",
        "template_name": "revision_humana",
        "language_code": "es_CO",
        "body_parameters": [f"valor-{index}" for index in range(1, 11)],
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


def test_status_updates_are_applied_without_feature_flag():
    service = FakeEventService()

    result = asyncio.run(
        process_human_escalation_status_updates_best_effort(
            [
                {
                    "provider_message_id": "wamid.doctor",
                    "status": "delivered",
                    "timestamp": "1790000001",
                    "error_code": None,
                }
            ],
            event_service=service,
        )
    )

    assert result == {
        "status": "status_updates_processed",
        "updates_received": 1,
        "updates_matched": 1,
        "updates_ignored": 0,
        "updates_failed": 0,
    }
    assert service.status_calls[0]["provider_status"] == "delivered"
    assert service.status_calls[0]["provider_message_id"] == "wamid.doctor"


def test_failed_status_persists_only_safe_error_code():
    service = FakeEventService()

    asyncio.run(
        process_human_escalation_status_updates_best_effort(
            [
                {
                    "provider_message_id": "wamid.doctor",
                    "status": "failed",
                    "timestamp": "1790000002",
                    "error_code": "131026",
                }
            ],
            event_service=service,
        )
    )

    assert service.status_calls[0]["error_category"] == (
        "provider_status_failed_131026"
    )
