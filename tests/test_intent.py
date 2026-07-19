from app.services.intent import classify_intent


def test_general():
    assert classify_intent("Hola buenas") == "general"


def test_cita():
    assert classify_intent("Quiero pedir una cita") == "cita"


def test_fecha_cita_por_contexto():
    assert classify_intent("Mañana en la tarde", "ST_CITA_FECHA") == "fecha_cita"


def test_pago():
    assert classify_intent("Cuánto cuesta la terapia") == "pago"


def test_servicios():
    assert classify_intent("Qué servicios ofrecen") == "servicios"


def test_horarios():
    assert classify_intent("Atienden los sábados") == "horarios"


def test_optout_wins():
    assert classify_intent("No quiero recibir más mensajes") == "optout"


def test_urgencia():
    assert classify_intent("Es urgente, no puedo respirar") == "urgencia"


def test_p6c_urgency_intent_detects_critical_respiratory_phrases():
    cases = [
        "Tengo dolor fuerte en el pecho y me cuesta respirar",
        "Me falta el aire",
        "Tengo los labios morados",
        "Mi saturación está muy baja",
        "Tengo saturacion de oxigeno muy baja",
        "Me estoy ahogando",
    ]

    for message in cases:
        assert classify_intent(message) == "urgencia"


def test_p6f71_colombian_time_preference_is_detected_inside_appointment_slot_state():
    cases = [
        "La de 5 de la tarde",
        "A las 5 pm",
        "17:00",
        "La segunda",
        "La primera",
        "A las cinco",
        "Tipo 5",
        "Como a las 5",
        "Por ahí a las 5",
        "A eso de las 5",
        "Cinco de la tarde",
        "La de cinco",
    ]

    for message in cases:
        assert classify_intent(message, "ST_CITA_FRANJA") == "hora_cita"


def test_en_la_tarde_in_st_cita_franja_is_hora_cita():
    assert classify_intent("En la tarde", "ST_CITA_FRANJA") == "hora_cita"


def test_p6f91419_maniana_variant_is_fecha_cita_inside_appointment_date_state():
    assert classify_intent("Maniana en la tarde", "ST_CITA_FECHA") == "fecha_cita"
    assert classify_intent("Maniana en la maniana", "ST_CITA_FECHA") == "fecha_cita"


def test_p6f91419_clarification_question_stays_in_appointment_date_context():
    cases = [
        "Cual fecha indicada?",
        "Cuál fecha indicada?",
        "Qué fecha indicada?",
        "No entendí",
        "Qué quiere decir?",
    ]

    for message in cases:
        assert classify_intent(message, "ST_CITA_FECHA") == "fecha_cita"


def test_p6f929_slot_preference_before_date_is_not_general():
    assert classify_intent("Para la de las 5", "ST_CITA_FECHA") == "hora_cita"
    assert classify_intent("Para la de las 3", "ST_CITA_FECHA") == "hora_cita"
    assert classify_intent("La de las 5", "ST_CITA_FECHA") == "hora_cita"


def test_p6f989b_manana_is_fecha_cita_inside_appointment_slot_state():
    assert classify_intent("Mañana", "ST_CITA_FRANJA") == "fecha_cita"

def test_retired_tracheostomy_service_has_deterministic_intent():
    messages = [
        "¿Manejan pacientes traqueotomizados?",
        "Tengo una traqueostomía",
        "Quiero una cita para un paciente traqueostomizado",
    ]

    for message in messages:
        assert classify_intent(message) == "servicio_no_disponible"

    assert (
        classify_intent("Paciente traqueostomizado no puede respirar")
        == "urgencia"
    )
