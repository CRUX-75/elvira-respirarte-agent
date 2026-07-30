import importlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.human_escalation import (
    APPROVED_ESCALATION_ACTIONS,
)


OCCURRED_AT = datetime(
    2026,
    7,
    30,
    14,
    0,
    tzinfo=timezone.utc,
)


def adapter_module():
    return importlib.import_module(
        "app.services.reactivation_response_adapters"
    )


class FakePatientFinder:
    def __init__(self, patient):
        self.patient = patient
        self.calls = []

    def __call__(self, *, telefono):
        self.calls.append({"telefono": telefono})
        return self.patient


class FakePatientUpdater:
    def __init__(self):
        self.calls = []

    def __call__(
        self,
        *,
        patient_id,
        nuevo_estado,
        opt_out,
    ):
        self.calls.append(
            {
                "patient_id": patient_id,
                "nuevo_estado": nuevo_estado,
                "opt_out": opt_out,
            }
        )


class FakeEscalationService:
    def __init__(self):
        self.events = []

    def create_or_reuse(self, event):
        self.events.append(event)
        return event


def test_global_optout_writer_updates_existing_patient_only():
    module = adapter_module()
    finder = FakePatientFinder(
        {
            "id": "patient-001",
            "telefono": "573000000001",
            "opt_out": False,
        }
    )
    updater = FakePatientUpdater()

    result = module.persist_reactivation_global_opt_out(
        phone_e164=" 573000000001 ",
        inbound_whatsapp_message_id="wamid.inbound-001",
        response_event_id="response-event-001",
        safe_reason="privacy_objection",
        patient_finder=finder,
        patient_updater=updater,
    )

    assert result is True
    assert finder.calls == [
        {"telefono": "573000000001"}
    ]
    assert updater.calls == [
        {
            "patient_id": "patient-001",
            "nuevo_estado": "ST_OPTOUT",
            "opt_out": True,
        }
    ]


def test_global_optout_writer_does_not_create_missing_patient():
    module = adapter_module()
    finder = FakePatientFinder(None)
    updater = FakePatientUpdater()

    result = module.persist_reactivation_global_opt_out(
        phone_e164="573000000099",
        inbound_whatsapp_message_id="wamid.inbound-099",
        response_event_id="response-event-099",
        safe_reason="stop_contact_request",
        patient_finder=finder,
        patient_updater=updater,
    )

    assert result is False
    assert finder.calls == [
        {"telefono": "573000000099"}
    ]
    assert updater.calls == []


@pytest.mark.parametrize(
    (
        "escalation_action",
        "response_classification",
        "response_safe_reason",
        "expected_reason",
    ),
    (
        (
            "escalate_reactivation_interest",
            "positive_contact_request",
            "contact_requested",
            "Paciente interesado en retomar contacto",
        ),
        (
            "escalate_reactivation_complaint",
            "complaint",
            "complaint",
            "Queja recibida durante reactivación",
        ),
    ),
)
def test_escalation_writer_builds_privacy_minimized_event(
    escalation_action,
    response_classification,
    response_safe_reason,
    expected_reason,
):
    module = adapter_module()
    service = FakeEscalationService()

    event = module.persist_reactivation_escalation(
        contact_id="contact-001",
        phone_e164="573000000001",
        inbound_whatsapp_message_id="wamid.inbound-001",
        response_event_id="response-event-001",
        escalation_action=escalation_action,
        response_classification=response_classification,
        response_safe_reason=response_safe_reason,
        occurred_at=OCCURRED_AT,
        escalation_service=service,
    )

    assert event is service.events[0]
    assert event.patient_id is None
    assert event.inbound_whatsapp_message_id == (
        "wamid.inbound-001"
    )
    assert event.escalation_action == escalation_action
    assert event.reason_code == escalation_action
    assert expected_reason in event.notification_text
    assert "573000000001" in event.notification_text
    assert "Reactivación histórica" in event.notification_text
    assert event.created_at is not None

    serialized = event.model_dump(mode="json")

    assert "message" not in serialized
    assert "raw_message" not in serialized
    assert "message_text" not in serialized
    assert "response_text" not in serialized
    assert "contact-001" not in str(serialized)
    assert "response-event-001" not in str(serialized)


def test_reactivation_actions_are_explicitly_approved():
    adapter_module()

    assert "escalate_reactivation_interest" in (
        APPROVED_ESCALATION_ACTIONS
    )
    assert "escalate_reactivation_complaint" in (
        APPROVED_ESCALATION_ACTIONS
    )


def test_escalation_idempotency_depends_on_wamid_and_action():
    module = adapter_module()
    service = FakeEscalationService()

    common = {
        "contact_id": "contact-001",
        "phone_e164": "573000000001",
        "inbound_whatsapp_message_id": "wamid.inbound-001",
        "response_event_id": "response-event-001",
        "response_classification": "positive_contact_request",
        "response_safe_reason": "contact_requested",
        "occurred_at": OCCURRED_AT,
        "escalation_service": service,
    }

    first = module.persist_reactivation_escalation(
        escalation_action="escalate_reactivation_interest",
        **common,
    )
    second = module.persist_reactivation_escalation(
        escalation_action="escalate_reactivation_interest",
        **common,
    )
    different_action = module.persist_reactivation_escalation(
        escalation_action="escalate_reactivation_complaint",
        **common,
    )

    assert first.idempotency_key == second.idempotency_key
    assert (
        first.idempotency_key
        != different_action.idempotency_key
    )


def test_adapters_remain_disconnected_from_productive_webhook():
    module = adapter_module()

    assert hasattr(
        module,
        "persist_reactivation_global_opt_out",
    )
    assert hasattr(
        module,
        "persist_reactivation_escalation",
    )

    main_source = open(
        "app/main.py",
        encoding="utf-8",
    ).read()

    assert "reactivation_response_adapters" not in main_source
    assert (
        "process_reactivation_response_best_effort"
        not in main_source
    )
