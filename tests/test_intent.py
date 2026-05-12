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
    from app.services.intent import classify_intent

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
