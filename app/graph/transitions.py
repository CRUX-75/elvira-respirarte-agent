from app.services.slot_confirmation_guard import is_simple_affirmative_slot_confirmation
from app.graph.state import ElviraState
from app.services.appointment_request_runtime import (
    is_exact_hour_without_explicit_franja_confirmation,
    resolve_requested_slot_from_message,
)


_AMBIGUOUS_SLOT_SELECTION_MESSAGES = {
    "en la tarde",
    "por la tarde",
    "tarde",
}


def _has_missing_or_unavailable_appointment_context(state: ElviraState) -> bool:
    if not state.fecha_solicitada:
        return True

    return _has_unavailable_appointment_context(state)


def _has_unavailable_appointment_context(state: ElviraState) -> bool:
    if not state.fecha_solicitada:
        return False

    if state.is_weekend is True:
        return True

    if state.is_colombia_holiday is True:
        return True

    if state.es_dia_disponible is False:
        return True

    if not state.slots_candidatos:
        return True

    return False


def _is_ambiguous_slot_selection(message: str | None) -> bool:
    normalized = (message or "").strip().lower()
    return normalized in _AMBIGUOUS_SLOT_SELECTION_MESSAGES


def apply_state_transition(state: ElviraState) -> ElviraState:
    """
    State machine pura y determinística.
    El LLM no decide estados. Solo esta función decide transiciones.
    """
    previous_state = state.estado_actual
    intent = state.intent
    state.estado_anterior = previous_state

    # OPTOUT — prioridad máxima
    if state.opt_out or intent == "optout":
        state.nuevo_estado = "ST_OPTOUT"
        state.next_action = "confirm_optout"
        state.opt_out = True
        state.state_reason = "Paciente solicitó no recibir más mensajes."
        return state

    # URGENCIA
    if intent == "urgencia":
        state.nuevo_estado = "ST_URGENCIA"
        state.next_action = "escalate_urgent_case"
        state.escalation_required = True
        state.state_reason = "Mensaje sugiere posible caso urgente respiratorio."
        return state

    # CITA — inicio del flujo
    if intent == "cita":
        if _has_unavailable_appointment_context(state):
            state.nuevo_estado = "ST_CITA_FECHA"
            state.next_action = "ask_preferred_date"
            state.state_reason = "unavailable_date_guard"
            return state

        if (
            state.fecha_solicitada
            and state.es_dia_disponible is True
            and state.slots_candidatos
        ):
            state.nuevo_estado = "ST_CITA_FRANJA"
            state.next_action = "ask_preferred_time"
            state.state_reason = "appointment_intent_with_embedded_date"
            return state

        state.nuevo_estado = "ST_CITA_FECHA"
        state.next_action = "ask_preferred_date"
        state.state_reason = "Paciente quiere agendar una cita."
        return state

    # FECHA CITA — paciente dio fecha o franja
    if intent == "fecha_cita":
        if _has_missing_or_unavailable_appointment_context(state):
            state.nuevo_estado = "ST_CITA_FECHA"
            state.next_action = "ask_preferred_date"
            state.state_reason = "unavailable_date_guard"
            return state

        state.nuevo_estado = "ST_CITA_FRANJA"
        state.next_action = "ask_preferred_time"
        state.state_reason = "Paciente indicó fecha o franja horaria."
        return state

    # HORA CITA — paciente dio hora o selección de franja
    if intent == "hora_cita":
        if previous_state == "ST_CITA_FECHA":
            state.nuevo_estado = "ST_CITA_FECHA"
            state.next_action = "ask_date_for_slot_preference"
            state.state_reason = "slot_preference_before_date_guard"
            return state

        if previous_state == "ST_CITA_FRANJA" and _has_unavailable_appointment_context(state):
            state.nuevo_estado = "ST_CITA_FECHA"
            state.next_action = "ask_preferred_date"
            state.state_reason = "unavailable_date_guard"
            return state

        if (
            previous_state == "ST_CITA_FRANJA"
            and _is_ambiguous_slot_selection(state.mensaje_original)
        ):
            state.nuevo_estado = "ST_CITA_FRANJA"
            state.next_action = "ask_specific_time_slot"
            state.state_reason = "ambiguous_slot_selection_guard"
            return state

        if (
            previous_state == "ST_CITA_FRANJA"
            and len(state.slots_candidatos or []) == 1
            and is_simple_affirmative_slot_confirmation(state.mensaje_original)
        ):
            state.nuevo_estado = "ST_CITA_PENDIENTE"
            state.next_action = "confirm_appointment_request"
            state.franja_solicitada = state.slots_candidatos[0]
            state.state_reason = "affirmative_slot_confirmation_guard"
            return state

        matched_slot = resolve_requested_slot_from_message(
            state.mensaje_original,
            list(state.slots_candidatos or []),
        )

        if (
            previous_state == "ST_CITA_FRANJA"
            and matched_slot
            and is_exact_hour_without_explicit_franja_confirmation(
                state.mensaje_original
            )
        ):
            state.nuevo_estado = "ST_CITA_PENDIENTE"
            state.next_action = "confirm_appointment_request"
            state.franja_solicitada = matched_slot
            state.state_reason = "exact_hour_inside_available_slot"
            return state

        if (
            previous_state == "ST_CITA_FRANJA"
            and is_exact_hour_without_explicit_franja_confirmation(
                state.mensaje_original
            )
        ):
            state.nuevo_estado = "ST_CITA_FRANJA"
            state.next_action = "ask_confirm_exact_hour_as_slot"
            state.state_reason = "requires_exact_hour_franja_confirmation"
            return state

        state.nuevo_estado = "ST_CITA_PENDIENTE"
        state.next_action = "confirm_appointment_request"
        state.state_reason = "Paciente indicó hora de preferencia."
        return state

    # PAGO
    if intent == "pago":
        state.nuevo_estado = previous_state
        state.next_action = "answer_payment_general"
        state.state_reason = "Paciente preguntó por precios o pagos."
        return state

    # SERVICIOS
    if intent == "servicios":
        state.nuevo_estado = previous_state
        state.next_action = "answer_services"
        state.kb_used = True
        state.state_reason = "Paciente preguntó por servicios de Respirarte."
        return state

    # HORARIOS
    if intent == "horarios":
        state.nuevo_estado = previous_state
        state.next_action = "answer_schedule"
        state.kb_used = True
        state.state_reason = "Paciente preguntó por horarios de atención."
        return state

    # REGLAS
    if intent == "reglas":
        state.nuevo_estado = previous_state
        state.next_action = "answer_rules"
        state.kb_used = True
        state.state_reason = "Paciente preguntó por reglas o políticas."
        return state

    # GENERAL
    state.nuevo_estado = "ST_GENERAL" if previous_state == "ST_INIT" else previous_state
    state.next_action = "answer_general"
    state.state_reason = "Mensaje general sin intención específica."
    return state
