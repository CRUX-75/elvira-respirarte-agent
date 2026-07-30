from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.services.human_escalation import (
    build_human_escalation_event,
)


PatientFinder = Callable[..., Any]
PatientUpdater = Callable[..., Any]


def _patient_identifier(patient: Any) -> str | None:
    if isinstance(patient, dict):
        value = patient.get("id")
    else:
        value = getattr(patient, "id", None)

    normalized = str(value or "").strip()
    return normalized or None


def persist_reactivation_global_opt_out(
    *,
    phone_e164: str,
    inbound_whatsapp_message_id: str,
    response_event_id: str,
    safe_reason: str | None,
    patient_finder: PatientFinder | None = None,
    patient_updater: PatientUpdater | None = None,
) -> bool:
    """
    Apply a confirmed global opt-out to an existing patient only.

    The inbound and response identifiers are accepted for adapter
    traceability but are intentionally not persisted in the patient row.
    """

    normalized_phone = str(phone_e164 or "").strip()

    if not normalized_phone:
        raise ValueError("phone_e164 is required.")

    if patient_finder is None:
        from app.repositories.patients import (
            find_patient_by_phone_read_only,
        )

        patient_finder = find_patient_by_phone_read_only

    if patient_updater is None:
        from app.repositories.patients import update_patient_state

        patient_updater = update_patient_state

    patient = patient_finder(
        telefono=normalized_phone,
    )

    if patient is None:
        return False

    patient_id = _patient_identifier(patient)

    if patient_id is None:
        return False

    patient_updater(
        patient_id=patient_id,
        nuevo_estado="ST_OPTOUT",
        opt_out=True,
    )

    return True


def _default_escalation_service() -> Any:
    from app.db.session import engine
    from app.repositories.human_escalation_events import (
        HumanEscalationEventRepository,
    )
    from app.services.human_escalation_event_service import (
        HumanEscalationEventService,
    )

    repository = HumanEscalationEventRepository(engine)
    return HumanEscalationEventService(repository)


def _safe_summary(
    *,
    response_classification: str | None,
    response_safe_reason: str | None,
) -> str:
    classification = str(
        response_classification or "no confirmada"
    ).strip()
    safe_reason = str(
        response_safe_reason or "no confirmado"
    ).strip()

    return (
        f"Clasificación segura: {classification}. "
        f"Motivo seguro: {safe_reason}."
    )


def persist_reactivation_escalation(
    *,
    contact_id: str,
    phone_e164: str,
    inbound_whatsapp_message_id: str,
    response_event_id: str,
    escalation_action: str,
    response_classification: str | None,
    response_safe_reason: str | None,
    occurred_at: datetime | None,
    escalation_service: Any | None = None,
) -> Any:
    """
    Build and persist an idempotent, privacy-minimized escalation.

    Campaign contact IDs, response event IDs and raw message content are
    deliberately excluded from the human escalation event.
    """

    normalized_phone = str(phone_e164 or "").strip()
    normalized_message_id = str(
        inbound_whatsapp_message_id or ""
    ).strip()
    normalized_action = str(
        escalation_action or ""
    ).strip()

    if not normalized_phone:
        raise ValueError("phone_e164 is required.")

    if not normalized_message_id:
        raise ValueError(
            "inbound_whatsapp_message_id is required."
        )

    if not normalized_action:
        raise ValueError("escalation_action is required.")

    event = build_human_escalation_event(
        patient_id=None,
        patient_name=None,
        patient_phone=normalized_phone,
        inbound_whatsapp_message_id=(
            normalized_message_id
        ),
        escalation_required=True,
        escalation_action=normalized_action,
        conversation_state="ST_REACTIVATION_RESPONSE",
        requested_service="Reactivación histórica",
        medical_order_status="no aplica",
        clinical_fact=(
            "Respuesta de reactivación clasificada "
            "de forma determinista."
        ),
        safe_summary=_safe_summary(
            response_classification=(
                response_classification
            ),
            response_safe_reason=response_safe_reason,
        ),
        occurred_at=occurred_at,
    )

    runtime_service = (
        escalation_service
        if escalation_service is not None
        else _default_escalation_service()
    )

    return runtime_service.create_or_reuse(event)
