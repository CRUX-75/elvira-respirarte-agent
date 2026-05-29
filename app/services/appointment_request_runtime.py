from __future__ import annotations

import re
from dataclasses import dataclass

from app.graph.state import ElviraState



def _normalize_slot_message(message: str | None) -> str:
    if not message:
        return ""

    normalized = message.lower().strip()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "¿": " ",
        "?": " ",
        ".": " ",
        ",": " ",
        ";": " ",
        ":": " ",
    }

    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def is_exact_hour_without_explicit_franja_confirmation(message: str | None) -> bool:
    """Return True when patient mentions a loose exact hour, not a full KB franja.

    P6-F.9.14.27:
    A loose exact hour inside a KB slot must not create an AppointmentRequest yet.
    The assistant must clarify that care is handled by franjas and ask for confirmation.
    """

    normalized = _normalize_slot_message(message)

    if not normalized:
        return False

    explicit_franja_markers = (
        "franja",
        "bloque",
        "de 3 a 5",
        "3 a 5",
        "de 5 a 7",
        "5 a 7",
        "primera",
        "segunda",
        "primer horario",
        "segundo horario",
        "primer turno",
        "segundo turno",
    )

    if any(marker in normalized for marker in explicit_franja_markers):
        return False

    exact_hour_patterns = (
        r"\ba las\s+\d{1,2}\b",
        r"\ba la\s+\d{1,2}\b",
        r"\b\d{1,2}\s*(am|pm)\b",
        r"\b\d{1,2}\s*(a m|p m)\b",
        r"\ba las\s+(tres|cinco)\b",
        r"\ba la\s+(una)\b",
    )

    return any(re.search(pattern, normalized) for pattern in exact_hour_patterns)


def resolve_requested_slot_from_message(
    message: str | None,
    slots: list[str],
) -> str | None:
    """Resolve a patient message to one of the visible offered appointment slots.

    The business flow registers offered franjas, not arbitrary exact loose hours
    inside a franja.
    """

    if not slots:
        return None

    normalized = _normalize_slot_message(message)

    if not normalized:
        return None

    first_slot = slots[0] if len(slots) >= 1 else None
    second_slot = slots[1] if len(slots) >= 2 else None

    first_patterns = (
        r"\b(a las )?3\b",
        r"\b(a las )?tres\b",
        r"\bde 3 a 5\b",
        r"\b3 a 5\b",
        r"\bprimera\b",
        r"\bprimer horario\b",
        r"\bprimer turno\b",
        r"\bprimera franja\b",
    )

    second_patterns = (
        r"\b(a las )?5\b",
        r"\b(a las )?cinco\b",
        r"\bde 5 a 7\b",
        r"\b5 a 7\b",
        r"\bsegunda\b",
        r"\bsegundo horario\b",
        r"\bsegundo turno\b",
        r"\bsegunda franja\b",
    )

    if first_slot and any(re.search(pattern, normalized) for pattern in first_patterns):
        return first_slot

    if second_slot and any(re.search(pattern, normalized) for pattern in second_patterns):
        return second_slot

    return None


@dataclass(frozen=True)
class AppointmentPersistenceDecision:
    should_persist: bool
    reason: str
    telefono: str | None = None
    nombre_paciente: str | None = None
    intent_origen: str | None = None
    canal_origen: str = "whatsapp"
    estado_solicitud: str | None = None
    fecha_solicitada: str | None = None
    franja_solicitada: str | None = None
    hora_solicitada_texto: str | None = None
    servicio_solicitado: str | None = None
    direccion_domicilio: str | None = None
    source_interaction_id: str | None = None


_NON_APPOINTMENT_INTENTS = {
    "general",
    "servicios",
    "horarios",
    "pago",
    "reglas",
    "urgencia",
    "optout",
}


def decide_appointment_request_persistence(
    *,
    state: ElviraState,
    telefono: str,
    nombre: str | None,
    source_interaction_id: str | None,
) -> AppointmentPersistenceDecision:
    normalized_phone = (telefono or "").strip()

    if not normalized_phone:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_missing_telefono",
            telefono=None,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            source_interaction_id=source_interaction_id,
        )

    if state.intent in _NON_APPOINTMENT_INTENTS:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_non_appointment_intent",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            source_interaction_id=source_interaction_id,
        )

    if state.intent == "cita":
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_initial_cita_intent",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            source_interaction_id=source_interaction_id,
        )

    if state.intent == "fecha_cita":
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_fecha_cita_waiting_for_time",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            source_interaction_id=source_interaction_id,
        )

    if state.intent != "hora_cita":
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_non_appointment_intent",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            source_interaction_id=source_interaction_id,
        )

    if (
        state.nuevo_estado != "ST_CITA_PENDIENTE"
        or state.next_action != "confirm_appointment_request"
    ):
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_wrong_state_or_action",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            source_interaction_id=source_interaction_id,
        )

    if not state.fecha_solicitada:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_missing_fecha_solicitada",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            source_interaction_id=source_interaction_id,
        )

    if state.is_weekend is True:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_weekend",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            fecha_solicitada=state.fecha_solicitada,
            source_interaction_id=source_interaction_id,
        )

    if state.is_colombia_holiday is True:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_colombia_holiday",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            fecha_solicitada=state.fecha_solicitada,
            source_interaction_id=source_interaction_id,
        )

    if state.es_dia_disponible is False:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_unavailable_date",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            fecha_solicitada=state.fecha_solicitada,
            source_interaction_id=source_interaction_id,
        )

    slots = list(state.slots_candidatos or [])
    franja_solicitada = resolve_requested_slot_from_message(
        state.mensaje_original,
        slots,
    )
    hora_solicitada_texto = state.mensaje_original or None

    if (
        franja_solicitada is not None
        and is_exact_hour_without_explicit_franja_confirmation(state.mensaje_original)
    ):
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="requires_exact_hour_franja_confirmation",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            fecha_solicitada=state.fecha_solicitada,
            franja_solicitada=franja_solicitada,
            hora_solicitada_texto=hora_solicitada_texto,
            source_interaction_id=source_interaction_id,
        )

    if franja_solicitada is None:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_unsupported_slot_selection",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            fecha_solicitada=state.fecha_solicitada,
            hora_solicitada_texto=hora_solicitada_texto,
            source_interaction_id=source_interaction_id,
        )

    if not franja_solicitada and not hora_solicitada_texto:
        return AppointmentPersistenceDecision(
            should_persist=False,
            reason="skipped_missing_time_preference",
            telefono=normalized_phone,
            nombre_paciente=nombre,
            intent_origen=state.intent,
            fecha_solicitada=state.fecha_solicitada,
            source_interaction_id=source_interaction_id,
        )

    return AppointmentPersistenceDecision(
        should_persist=True,
        reason="allowed_hora_cita_ready_for_human_review",
        telefono=normalized_phone,
        nombre_paciente=nombre,
        intent_origen=state.intent,
        canal_origen="whatsapp",
        estado_solicitud="pendiente_confirmacion",
        fecha_solicitada=state.fecha_solicitada,
        franja_solicitada=franja_solicitada,
        hora_solicitada_texto=hora_solicitada_texto,
        servicio_solicitado=None,
        direccion_domicilio=None,
        source_interaction_id=source_interaction_id,
    )
