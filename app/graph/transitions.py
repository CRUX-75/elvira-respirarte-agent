from app.graph.state import ElviraState


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
        state.nuevo_estado = "ST_CITA_FECHA"
        state.next_action = "ask_preferred_date"
        state.state_reason = "Paciente quiere agendar una cita."
        return state

    # FECHA CITA — paciente dio fecha o franja
    if intent == "fecha_cita":
        state.nuevo_estado = "ST_CITA_FRANJA"
        state.next_action = "ask_preferred_time"
        state.state_reason = "Paciente indicó fecha o franja horaria."
        return state

    # HORA CITA — paciente dio hora
    if intent == "hora_cita":
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
