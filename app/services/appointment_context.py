from __future__ import annotations

from typing import Any


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

    if getattr(state, "nuevo_estado", None) != "ST_CITA_PENDIENTE":
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

    if getattr(decision, "reason", None) != "requires_exact_hour_franja_confirmation":
        return None

    if getattr(state, "nuevo_estado", None) != "ST_CITA_FRANJA":
        return None

    franja_solicitada = getattr(decision, "franja_solicitada", None)
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
    """Apply pending exact-hour franja context after an affirmative reply."""

    if not context:
        return state

    if not context.get("pending_exact_hour_requires_confirmation"):
        return state

    pending_franja = context.get("pending_exact_hour_franja")
    if not pending_franja:
        return state

    if getattr(state, "nuevo_estado", None) not in {
        "ST_CITA_FRANJA",
        "ST_CITA_PENDIENTE",
    }:
        return state

    if not _is_affirmative_confirmation(getattr(state, "mensaje_original", None)):
        return state

    if not context.get("fecha_solicitada"):
        return state

    for field in APPOINTMENT_CONTEXT_FIELDS:
        if field in context:
            setattr(state, field, context.get(field))

    state.intent = "hora_cita"
    state.nuevo_estado = "ST_CITA_PENDIENTE"
    state.next_action = "confirm_appointment_request"
    state.franja_solicitada = pending_franja
    state.state_reason = "confirmed_pending_exact_hour_franja"

    return state
