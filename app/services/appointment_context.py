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
