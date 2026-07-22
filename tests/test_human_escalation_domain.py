from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.models.human_escalation_event import HumanEscalationStatus
from app.services.human_escalation import (
    build_human_escalation_event,
    build_human_escalation_idempotency_key,
    normalize_whatsapp_number,
    should_dispatch_human_escalation,
)
from app.services.human_escalation_config import (
    load_human_escalation_config,
)


def test_requires_flag_and_approved_action():
    assert should_dispatch_human_escalation(
        escalation_required=True,
        next_action="escalate_dynamic_oximetry_missing_order",
    )

    assert not should_dispatch_human_escalation(
        escalation_required=False,
        next_action="escalate_dynamic_oximetry_missing_order",
    )

    assert not should_dispatch_human_escalation(
        escalation_required=True,
        next_action="ask_preferred_date",
    )


def test_unavailable_service_requires_final_escalation_flag():
    assert should_dispatch_human_escalation(
        escalation_required=True,
        next_action="answer_unavailable_service",
    )

    assert not should_dispatch_human_escalation(
        escalation_required=False,
        next_action="answer_unavailable_service",
    )


def test_idempotency_key_is_stable_and_action_sensitive():
    first = build_human_escalation_idempotency_key(
        inbound_whatsapp_message_id="wamid.test-1",
        escalation_action="escalate_unknown_service",
    )
    second = build_human_escalation_idempotency_key(
        inbound_whatsapp_message_id="wamid.test-1",
        escalation_action="escalate_unknown_service",
    )
    different = build_human_escalation_idempotency_key(
        inbound_whatsapp_message_id="wamid.test-1",
        escalation_action="escalate_urgent_case",
    )

    assert first == second
    assert first != different
    assert len(first) == 64


def test_builds_missing_order_notification():
    event = build_human_escalation_event(
        patient_id="patient-test-1",
        patient_name="Paciente de prueba",
        patient_phone="573000000001",
        inbound_whatsapp_message_id="wamid.test-2",
        escalation_required=True,
        escalation_action=(
            "escalate_dynamic_oximetry_missing_order"
        ),
        conversation_state="ST_GENERAL",
        occurred_at=datetime(
            2026,
            7,
            22,
            10,
            30,
            tzinfo=ZoneInfo("America/Bogota"),
        ),
    )

    assert event.status == HumanEscalationStatus.PENDING
    assert event.attempt_count == 0
    assert "Servicio: Oximetría dinámica" in event.notification_text
    assert "Orden médica: no" in event.notification_text
    assert "2026-07-22 10:30 (Colombia)" in event.notification_text
    assert "Requiere revisión humana." in event.notification_text


def test_builder_rejects_unapproved_action():
    with pytest.raises(
        ValueError,
        match="approved human escalation",
    ):
        build_human_escalation_event(
            patient_id="patient-test-1",
            patient_name="Paciente de prueba",
            patient_phone="573000000001",
            inbound_whatsapp_message_id="wamid.test-3",
            escalation_required=True,
            escalation_action="answer_schedule",
            conversation_state="ST_GENERAL",
        )


def test_builder_requires_inbound_message_id():
    with pytest.raises(
        ValueError,
        match="message ID is required",
    ):
        build_human_escalation_event(
            patient_id=None,
            patient_name=None,
            patient_phone=None,
            inbound_whatsapp_message_id="",
            escalation_required=True,
            escalation_action="escalate_unknown_service",
            conversation_state=None,
        )


def test_safe_summary_is_collapsed_and_truncated():
    event = build_human_escalation_event(
        patient_id=None,
        patient_name="  Paciente   de prueba  ",
        patient_phone="573000000001",
        inbound_whatsapp_message_id="wamid.test-4",
        escalation_required=True,
        escalation_action="escalate_unknown_service",
        conversation_state="ST_GENERAL",
        safe_summary=("detalle " * 100),
    )

    summary_line = next(
        line
        for line in event.notification_text.splitlines()
        if line.startswith("Resumen:")
    )

    assert "Paciente: Paciente de prueba" in event.notification_text
    assert summary_line.endswith("…")
    assert len(summary_line) <= len("Resumen: ") + 240


def test_disabled_config_is_not_ready():
    config = load_human_escalation_config(environ={})

    assert config.enabled is False
    assert config.whatsapp_number is None
    assert config.ready is False


def test_enabled_config_normalizes_number():
    config = load_human_escalation_config(
        environ={
            "HUMAN_ESCALATION_ENABLED": "true",
            "HUMAN_ESCALATION_WHATSAPP_NUMBER": (
                "+57 300 000 0001"
            ),
        }
    )

    assert config.enabled is True
    assert config.whatsapp_number == "573000000001"
    assert config.ready is True


def test_invalid_operational_number_is_rejected():
    with pytest.raises(
        ValueError,
        match="between 8 and 15 digits",
    ):
        load_human_escalation_config(
            environ={
                "HUMAN_ESCALATION_ENABLED": "true",
                "HUMAN_ESCALATION_WHATSAPP_NUMBER": "123",
            }
        )


def test_number_normalizer_does_not_invent_country_code():
    assert (
        normalize_whatsapp_number("+57 300 000 0001")
        == "573000000001"
    )
    assert normalize_whatsapp_number(None) is None


def test_migration_defines_idempotency_and_delivery_states():
    sql = Path(
        "scripts/sql/006_create_human_escalation_events.sql"
    ).read_text(encoding="utf-8")

    assert "status IN ('pending', 'sent', 'failed')" in sql
    assert "idempotency_key TEXT NOT NULL UNIQUE" in sql
    assert "inbound_whatsapp_message_id" in sql
    assert "escalation_action" in sql
    assert "claim_token TEXT" in sql
    assert "claim_expires_at TIMESTAMPTZ" in sql
