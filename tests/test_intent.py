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
