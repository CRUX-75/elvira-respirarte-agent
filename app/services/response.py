from app.graph.state import ElviraState
from app.services.dynamic_oximetry_policy import apply_dynamic_oximetry_policy
from app.services.approved_service_catalog import (
    get_active_portfolio_response,
    get_unavailable_service_response,
    unavailable_service_requires_escalation,
)


def generate_response(state: ElviraState) -> ElviraState:
    # P6-F.9.97 deterministic continuity and grounding guards.
    pending_appointment_context = "ST_CITA_PENDIENTE" in {
        state.estado_anterior,
        state.estado_actual,
        state.nuevo_estado,
    }

    if (
        state.next_action == "answer_general"
        and state.estado_anterior != "ST_INIT"
        and not pending_appointment_context
    ):
        state.respuesta = (
            "Claro. Cuénteme un poco más para poder continuar ayudándole."
        )
        return state

    dynamic_oximetry_state = apply_dynamic_oximetry_policy(
        state
    )
    if dynamic_oximetry_state is not None:
        return dynamic_oximetry_state

    normalized_message = (state.mensaje_original or "").strip().lower()
    generic_service_question = any(
        marker in normalized_message
        for marker in (
            "qué servicios",
            "que servicios",
            "cuáles servicios",
            "cuales servicios",
            "todos los servicios",
            "servicios ofrecen",
            "servicios tiene",
        )
    )

    if (
        state.next_action == "answer_services"
        and not generic_service_question
        and (
            state.service_grounding_status == "partial"
            or not state.kb_used
            or "kb_services" not in (state.kb_sources or [])
            or not state.kb_context
        )
    ):
        state.next_action = "escalate_unknown_service"
        state.escalation_required = True
        state.respuesta = (
            "No tengo información confirmada suficiente sobre ese procedimiento. "
            "Voy a remitir su consulta a la Dra. D’Aleman para que pueda "
            "orientarle correctamente."
        )
        return state

    """
    Generador de respuestas basado en reglas para Sprint P1.
    Sin LLM. Sin memoria. Sin tools.
    """

    action = state.next_action

    if action == "confirm_optout":
        state.respuesta = (
            "Entendido. No le enviaremos más mensajes por este medio. Muchas gracias."
        )
        return state

    if action == "escalate_urgent_case":
        state.respuesta = (
            "Por lo que me comenta, es importante que busque atención médica urgente "
            "o se comunique directamente con un profesional de salud. "
            "Respirarte no gestiona urgencias por este medio."
        )
        return state

    if action == "ask_preferred_date":
        state.respuesta = (
            "Claro, con gusto le ayudamos a coordinar la cita. "
            "¿Para qué día le gustaría agendarla?"
        )
        return state

    if action == "ask_preferred_time":
        state.respuesta = (
            "Perfecto. ¿En qué horario le quedaría mejor?"
        )
        return state

    if action == "confirm_appointment_request":
        state.respuesta = (
            "Gracias. Voy a dejar registrada su solicitud para que "
            "la Dra. D'Aleman pueda revisarla y confirmar disponibilidad."
        )
        return state

    if action == "answer_payment_general":
        state.respuesta = (
            "El valor puede variar según el tipo de atención que necesite cada paciente. "
            "Eso lo define la Dra. D'Aleman después de la valoración y diagnóstico. "
            "Si desea, le podemos ayudar a coordinar una valoración."
        )
        return state

    if action == "answer_unavailable_service":
        state.escalation_required = (
            unavailable_service_requires_escalation(
                state.mensaje_original
            )
        )
        state.respuesta = get_unavailable_service_response(
            state.mensaje_original
        )
        return state

    if action == "answer_services":
        state.respuesta = get_active_portfolio_response()
        return state

    if action == "answer_schedule":
        state.respuesta = (
            "Atendemos de lunes a viernes de 3:00 PM a 9:00 PM en modalidad domiciliaria, "
            "y los sábados de 8:00 AM a 12:00 PM con consulta presencial en consultorio. "
            "Los domingos y festivos no hay atención."
        )
        return state

    if action == "answer_rules":
        state.respuesta = (
            "Las citas se coordinan directamente con Elvira. "
            "Cancelaciones con menos de 2 horas de anticipación pueden perder el turno. "
            "Para casos urgentes, por favor comuníquese con un centro médico directamente."
        )
        return state

    if (
        action == "answer_general"
        and state.nuevo_estado == "ST_CITA_PENDIENTE"
        and state.intent == "general"
    ):
        state.respuesta = (
            "Con gusto. Su solicitud quedó registrada y la Dra. D'Aleman "
            "le confirmará posteriormente. Si necesita algo más, aquí estoy."
        )
        return state

    # General por defecto
    state.respuesta = (
        "Hola, qué gusto saludarle. Cuénteme, ¿en qué le podemos ayudar hoy en Respirarte?"
    )
    return state
