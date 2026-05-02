from app.models.message import IncomingMessage
from app.graph.graph import process_message


def test_saludo_general():
    msg = IncomingMessage(telefono="573001112233", mensaje="Hola buenas")
    result = process_message(msg)
    assert result.intent == "general"
    assert result.nuevo_estado == "ST_GENERAL"
    assert result.respuesta is not None

def test_cita_flow():
    msg = IncomingMessage(telefono="573001112233", mensaje="Quiero pedir una cita")
    result = process_message(msg)
    assert result.intent == "cita"
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"

def test_fecha_cita_flow():
    msg = IncomingMessage(telefono="573001112233", mensaje="Mañana en la tarde", estado_actual="ST_CITA_FECHA")
    result = process_message(msg)
    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"

def test_optout_flow():
    msg = IncomingMessage(telefono="573001112233", mensaje="No quiero recibir más mensajes")
    result = process_message(msg)
    assert result.intent == "optout"
    assert result.nuevo_estado == "ST_OPTOUT"
    assert result.opt_out is True

def test_servicios_flow():
    msg = IncomingMessage(telefono="573001112233", mensaje="Qué servicios ofrecen")
    result = process_message(msg)
    assert result.intent == "servicios"
    assert result.next_action == "answer_services"
    assert result.kb_used is True

def test_horarios_flow():
    msg = IncomingMessage(telefono="573001112233", mensaje="Atienden los sábados")
    result = process_message(msg)
    assert result.intent == "horarios"
    assert result.next_action == "answer_schedule"

def test_urgencia_flow():
    msg = IncomingMessage(telefono="573001112233", mensaje="Es urgente, no puedo respirar")
    result = process_message(msg)
    assert result.intent == "urgencia"
    assert result.nuevo_estado == "ST_URGENCIA"
    assert result.escalation_required is True
