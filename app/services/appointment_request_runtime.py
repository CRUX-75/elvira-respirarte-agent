from __future__ import annotations

from dataclasses import dataclass

from app.graph.state import ElviraState


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
    franja_solicitada = slots[0] if slots else None
    hora_solicitada_texto = state.mensaje_original or None

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
