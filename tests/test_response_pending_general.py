from app.graph.state import ElviraState
from app.services.response import generate_response


def test_pending_appointment_ok_does_not_resalute():
    state = ElviraState(
        telefono="573018880647",
        mensaje_original="Ok",
        sanitized_input="Ok",
        estado_actual="ST_CITA_PENDIENTE",
        estado_anterior="ST_CITA_PENDIENTE",
        nuevo_estado="ST_CITA_PENDIENTE",
        intent="general",
        next_action="answer_general",
    )

    result = generate_response(state)

    assert result.nuevo_estado == "ST_CITA_PENDIENTE"
    assert result.respuesta is not None
    assert "Hola" not in result.respuesta
    assert "qué gusto saludarle" not in result.respuesta
    assert "Respirarte ofrecemos" not in result.respuesta
    assert (
        "solicitud" in result.respuesta.lower()
        or "quedamos atentos" in result.respuesta.lower()
    )


def test_pending_appointment_thanks_does_not_restart_conversation():
    state = ElviraState(
        telefono="573018880647",
        mensaje_original="Muchas gracias",
        sanitized_input="Muchas gracias",
        estado_actual="ST_CITA_PENDIENTE",
        estado_anterior="ST_CITA_PENDIENTE",
        nuevo_estado="ST_CITA_PENDIENTE",
        intent="general",
        next_action="answer_general",
    )

    result = generate_response(state)

    assert result.nuevo_estado == "ST_CITA_PENDIENTE"
    assert result.respuesta is not None
    assert "Hola" not in result.respuesta
    assert "qué gusto saludarle" not in result.respuesta
    assert "¿en qué le podemos ayudar hoy" not in result.respuesta
    assert (
        "solicitud" in result.respuesta.lower()
        or "quedamos atentos" in result.respuesta.lower()
    )

def test_answer_services_excludes_retired_tracheostomy_service():
    state = ElviraState(
        telefono="573000000000",
        mensaje_original="¿Qué servicios ofrecen?",
        sanitized_input="que servicios ofrecen",
        estado_actual="ST_GENERAL",
        estado_anterior="ST_GENERAL",
        nuevo_estado="ST_GENERAL",
        intent="servicios",
        next_action="answer_services",
    )

    result = generate_response(state)

    assert result.respuesta is not None
    assert "traque" not in result.respuesta.lower()
    assert "terapia respiratoria" in result.respuesta.lower()
