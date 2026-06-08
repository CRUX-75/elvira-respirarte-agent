from __future__ import annotations

from typing import Any

from app.services.appointment_request_runtime import resolve_requested_slot_from_message


APPOINTMENT_CONTEXT_FIELDS = (
    "fecha_solicitada",
    "fecha_solicitada_texto",
    "slots_candidatos",
    "es_dia_disponible",
    "is_weekend",
    "is_colombia_holiday",
    "colombia_holiday_name",
)


def capture_appointment_context_from_state(state: Any) -> dict[str, Any] | None:
    """Capture active appointment date context after a fecha_cita turn."""

    if getattr(state, "intent", None) != "fecha_cita":
        return None

    if getattr(state, "nuevo_estado", None) != "ST_CITA_FRANJA":
        return None

    fecha_solicitada = getattr(state, "fecha_solicitada", None)
    if not fecha_solicitada:
        return None

    return {
        field: getattr(state, field, None)
        for field in APPOINTMENT_CONTEXT_FIELDS
    }


def apply_appointment_context_to_state(state: Any, context: dict[str, Any] | None) -> Any:
    """Restore stored appointment context when the current turn lacks date context."""

    if not context:
        return state

    if getattr(state, "intent", None) != "hora_cita":
        return state

    if getattr(state, "nuevo_estado", None) not in {
        "ST_CITA_FRANJA",
        "ST_CITA_PENDIENTE",
    }:
        return state

    if getattr(state, "fecha_solicitada", None):
        return state

    if not context.get("fecha_solicitada"):
        return state

    for field in APPOINTMENT_CONTEXT_FIELDS:
        if field in context:
            setattr(state, field, context.get(field))

    return state


def should_clear_appointment_context(state: Any, persisted: bool) -> bool:
    """Decide whether the stored appointment context should be cleared."""

    if persisted:
        return True

    return bool(getattr(state, "opt_out", False))


AFFIRMATIVE_CONFIRMATION_MESSAGES = {
    "si",
    "sí",
    "claro",
    "de acuerdo",
    "listo",
    "esta bien",
    "está bien",
    "correcto",
    "ok",
    "okay",
    "vale",
}


def _normalize_confirmation_message(message: str | None) -> str:
    """Normalize short patient confirmation messages."""

    if not message:
        return ""

    return message.strip().lower()


def _is_affirmative_confirmation(message: str | None) -> bool:
    """Return True when the patient confirms a pending franja.

    Patients often confirm naturally with phrases such as:
    "Sí, registre esa franja" or "Sí claro".
    The confirmation must not depend only on exact one-word matches.
    """

    normalized = _normalize_confirmation_message(message)

    if not normalized:
        return False

    if normalized in AFFIRMATIVE_CONFIRMATION_MESSAGES:
        return True

    affirmative_prefixes = (
        "si ",
        "sí ",
        "si,",
        "sí,",
        "claro ",
        "claro,",
        "correcto ",
        "correcto,",
        "listo ",
        "listo,",
        "ok ",
        "ok,",
        "okay ",
        "okay,",
        "vale ",
        "vale,",
        "de acuerdo ",
        "de acuerdo,",
        "esta bien ",
        "está bien ",
    )

    if normalized.startswith(affirmative_prefixes):
        return True

    affirmative_phrases = (
        "registre esa franja",
        "registrar esa franja",
        "regístrela",
        "registrela",
        "esa franja esta bien",
        "esa franja está bien",
        "me sirve esa franja",
        "confirmo esa franja",
    )

    return any(phrase in normalized for phrase in affirmative_phrases)


def capture_pending_exact_hour_confirmation_context(
    state: Any,
    decision: Any,
) -> dict[str, Any] | None:
    """Capture pending exact-hour franja confirmation context.

    This is used when the patient asks for a loose exact hour inside a visible
    KB-backed franja. Elvira must ask for explicit franja confirmation and
    persist the pending franja so the next affirmative reply can be handled
    deterministically.
    """

    is_decision_exact_hour_confirmation = (
        getattr(decision, "reason", None)
        == "requires_exact_hour_franja_confirmation"
    )
    is_state_exact_hour_confirmation = (
        getattr(state, "state_reason", None)
        == "requires_exact_hour_franja_confirmation"
        and getattr(state, "next_action", None) == "ask_confirm_exact_hour_as_slot"
    )

    if not (is_decision_exact_hour_confirmation or is_state_exact_hour_confirmation):
        return None

    if getattr(state, "nuevo_estado", None) != "ST_CITA_FRANJA":
        return None

    franja_solicitada = getattr(decision, "franja_solicitada", None)

    if not franja_solicitada:
        franja_solicitada = getattr(state, "franja_solicitada", None)

    if not franja_solicitada:
        franja_solicitada = resolve_requested_slot_from_message(
            getattr(state, "mensaje_original", None),
            getattr(state, "slots_candidatos", None) or [],
        )

    if not franja_solicitada:
        return None

    fecha_solicitada = getattr(state, "fecha_solicitada", None)
    if not fecha_solicitada:
        return None

    context = {
        field: getattr(state, field, None)
        for field in APPOINTMENT_CONTEXT_FIELDS
    }

    context.update(
        {
            "pending_exact_hour_franja": franja_solicitada,
            "pending_exact_hour_text": getattr(state, "mensaje_original", None),
            "pending_exact_hour_requires_confirmation": True,
        }
    )

    return context


def apply_pending_exact_hour_confirmation_to_state(
    state: Any,
    context: dict[str, Any] | None,
) -> Any:
    """Do not convert vague exact-hour follow-ups into appointment requests.

    MVP rule P6-F.9.34:
    Exact-hour messages such as ""no se podría a las 4?"" are clarification
    guards only. Follow-ups like ""sí"", ""esa franja"" or
    ""registre esa franja"" must not create AppointmentRequest.
    The patient must explicitly choose an available slot, for example
    ""la primera"" or ""la segunda"".
    """

    return state

