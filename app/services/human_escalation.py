from __future__ import annotations

import hashlib
import re
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.models.human_escalation_event import HumanEscalationEvent


COLOMBIA_TIMEZONE = ZoneInfo("America/Bogota")

APPROVED_ESCALATION_ACTIONS = frozenset(
    {
        "escalate_reactivation_interest",
        "escalate_reactivation_complaint",
        "escalate_urgent_case",
        "escalate_unknown_service",
        "escalate_dynamic_oximetry_missing_order",
        "escalate_dynamic_oximetry_long_oxygen_support",
        "answer_unavailable_service",
    }
)

SAFE_REASON_BY_ACTION = {
    "escalate_reactivation_interest": (
        "Paciente interesado en retomar contacto"
    ),
    "escalate_reactivation_complaint": (
        "Queja recibida durante reactivación"
    ),
    "escalate_urgent_case": "Posible caso respiratorio urgente",
    "escalate_unknown_service": (
        "Información clínica o de servicio insuficiente"
    ),
    "escalate_dynamic_oximetry_missing_order": (
        "Oximetría dinámica solicitada sin orden médica"
    ),
    "escalate_dynamic_oximetry_long_oxygen_support": (
        "Oximetría dinámica con soporte de oxígeno prolongado"
    ),
    "answer_unavailable_service": (
        "Paciente traqueostomizado requiere valoración del especialista"
    ),
}

DEFAULT_SERVICE_BY_ACTION = {
    "escalate_reactivation_interest": "Reactivación histórica",
    "escalate_reactivation_complaint": "Reactivación histórica",
    "escalate_urgent_case": "Caso respiratorio por revisar",
    "escalate_unknown_service": "Servicio por confirmar",
    "escalate_dynamic_oximetry_missing_order": "Oximetría dinámica",
    "escalate_dynamic_oximetry_long_oxygen_support": "Oximetría dinámica",
    "answer_unavailable_service": (
        "Valoración de paciente traqueostomizado"
    ),
}

DEFAULT_SUMMARY_BY_ACTION = {
    "escalate_reactivation_interest": (
        "El contacto respondió positivamente a la campaña "
        "y solicita retomar el contacto."
    ),
    "escalate_reactivation_complaint": (
        "El contacto manifestó una queja durante la "
        "reactivación histórica."
    ),
    "escalate_urgent_case": (
        "El núcleo determinista detectó un posible caso urgente "
        "respiratorio."
    ),
    "escalate_unknown_service": (
        "La información disponible no permite dar una respuesta "
        "clínica confirmada."
    ),
    "escalate_dynamic_oximetry_missing_order": (
        "El paciente solicita oximetría dinámica y no cuenta "
        "con orden médica."
    ),
    "escalate_dynamic_oximetry_long_oxygen_support": (
        "El paciente reporta soporte de oxígeno durante quince días "
        "o más."
    ),
    "answer_unavailable_service": (
        "Consulta relacionada con atención de un paciente "
        "traqueostomizado."
    ),
}

DEFAULT_FACT_BY_ACTION = {
    "escalate_reactivation_interest": (
        "Respuesta positiva clasificada de forma determinista."
    ),
    "escalate_reactivation_complaint": (
        "Queja clasificada de forma determinista."
    ),
    "escalate_urgent_case": (
        "Clasificación determinista de posible urgencia respiratoria."
    ),
    "escalate_unknown_service": (
        "Información insuficiente para orientación confirmada."
    ),
    "escalate_dynamic_oximetry_missing_order": (
        "No cuenta con orden médica para oximetría dinámica."
    ),
    "escalate_dynamic_oximetry_long_oxygen_support": (
        "Soporte de oxígeno durante quince días o más."
    ),
    "answer_unavailable_service": (
        "Servicio domiciliario temporalmente inactivo; "
        "requiere valoración."
    ),
}


def should_dispatch_human_escalation(
    *,
    escalation_required: bool,
    next_action: str | None,
) -> bool:
    return bool(
        escalation_required is True
        and next_action in APPROVED_ESCALATION_ACTIONS
    )


def build_human_escalation_idempotency_key(
    *,
    inbound_whatsapp_message_id: str,
    escalation_action: str,
) -> str:
    source = (
        f"{inbound_whatsapp_message_id.strip()}::"
        f"{escalation_action.strip()}"
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def normalize_whatsapp_number(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None

    digits = re.sub(r"\D", "", value)

    if not 8 <= len(digits) <= 15:
        raise ValueError(
            "WhatsApp number must contain between 8 and 15 digits."
        )

    return digits


def _clean_text(
    value: str | None,
    *,
    fallback: str,
    max_length: int,
) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()

    if not cleaned:
        return fallback

    if len(cleaned) <= max_length:
        return cleaned

    return cleaned[: max_length - 1].rstrip() + "…"


def _medical_order_label(
    value: bool | str | None,
    *,
    escalation_action: str,
) -> str:
    if escalation_action == "escalate_dynamic_oximetry_missing_order":
        return "no"

    if isinstance(value, bool):
        return "sí" if value else "no"

    normalized = _clean_text(
        value,
        fallback="no confirmado",
        max_length=32,
    ).lower()

    if normalized in {"si", "sí", "yes", "true", "con orden"}:
        return "sí"

    if normalized in {"no", "false", "sin orden"}:
        return "no"

    if normalized in {"no aplica", "n/a"}:
        return "no aplica"

    return "no confirmado"


def build_human_escalation_event(
    *,
    patient_id: str | None,
    patient_name: str | None,
    patient_phone: str | None,
    inbound_whatsapp_message_id: str,
    escalation_required: bool,
    escalation_action: str | None,
    conversation_state: str | None,
    requested_service: str | None = None,
    medical_order_status: bool | str | None = None,
    clinical_fact: str | None = None,
    safe_summary: str | None = None,
    occurred_at: datetime | None = None,
) -> HumanEscalationEvent:
    """
    Construct a minimal escalation event.

    Raw audio, full transcripts, raw Meta payloads and full conversation
    history are intentionally absent from this contract.
    """

    if not should_dispatch_human_escalation(
        escalation_required=escalation_required,
        next_action=escalation_action,
    ):
        raise ValueError("Result is not an approved human escalation.")

    assert escalation_action is not None

    message_id = _clean_text(
        inbound_whatsapp_message_id,
        fallback="",
        max_length=256,
    )

    if not message_id:
        raise ValueError("Inbound WhatsApp message ID is required.")

    event_id = str(uuid4())

    idempotency_key = build_human_escalation_idempotency_key(
        inbound_whatsapp_message_id=message_id,
        escalation_action=escalation_action,
    )

    timestamp = occurred_at or datetime.now(tz=COLOMBIA_TIMEZONE)

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=COLOMBIA_TIMEZONE)
    else:
        timestamp = timestamp.astimezone(COLOMBIA_TIMEZONE)

    name = _clean_text(
        patient_name,
        fallback="No confirmado",
        max_length=120,
    )

    phone = _clean_text(
        patient_phone,
        fallback="No confirmado",
        max_length=32,
    )

    service = _clean_text(
        requested_service,
        fallback=DEFAULT_SERVICE_BY_ACTION[escalation_action],
        max_length=120,
    )

    summary = _clean_text(
        safe_summary,
        fallback=DEFAULT_SUMMARY_BY_ACTION[escalation_action],
        max_length=240,
    )

    fact = _clean_text(
        clinical_fact,
        fallback=DEFAULT_FACT_BY_ACTION[escalation_action],
        max_length=240,
    )

    state = _clean_text(
        conversation_state,
        fallback="No confirmado",
        max_length=80,
    )

    order_label = _medical_order_label(
        medical_order_status,
        escalation_action=escalation_action,
    )

    reason = SAFE_REASON_BY_ACTION[escalation_action]
    reference = event_id.split("-", 1)[0].upper()

    formatted_timestamp = f"{timestamp:%d/%m/%Y %H:%M} (Colombia)"

    template_parameters = [
        name,
        phone,
        service,
        reason,
        summary,
        order_label,
        fact,
        state,
        formatted_timestamp,
        reference,
    ]

    notification_text = (
        "Escalamiento de Elvira\n\n"
        f"Paciente: {name}\n"
        f"Teléfono: {phone}\n"
        f"Servicio: {service}\n"
        f"Motivo: {reason}\n"
        f"Resumen: {summary}\n"
        f"Orden médica: {order_label}\n"
        f"Dato relevante: {fact}\n"
        f"Estado: {state}\n"
        f"Fecha: {timestamp:%Y-%m-%d %H:%M} (Colombia)\n"
        f"Referencia: {reference}\n\n"
        "Requiere revisión humana."
    )

    return HumanEscalationEvent(
        id=event_id,
        idempotency_key=idempotency_key,
        patient_id=patient_id,
        inbound_whatsapp_message_id=message_id,
        escalation_action=escalation_action,
        reason_code=escalation_action,
        notification_text=notification_text,
        template_parameters=template_parameters,
        created_at=timestamp,
    )
