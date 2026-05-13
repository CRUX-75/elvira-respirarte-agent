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


def test_p6f71_colombian_time_preference_moves_to_pending_appointment_state():
    cases = [
        "La de 5 de la tarde",
        "A las 5 pm",
        "17:00",
        "La segunda",
        "La primera",
        "A las cinco",
    ]

    for message in cases:
        msg = IncomingMessage(
            telefono="573001112233",
            mensaje=message,
            estado_actual="ST_CITA_FRANJA",
        )

        result = process_message(msg)

        assert result.intent == "hora_cita"
        assert result.nuevo_estado == "ST_CITA_PENDIENTE"
        assert result.next_action == "confirm_appointment_request"


def test_p6f8_valid_relative_tomorrow_repeats_absolute_date_and_pm_window(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 13),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Mañana",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"

    assert result.fecha_solicitada == "2026-05-14"
    assert result.fecha_solicitada_texto == "jueves 14 de mayo"
    assert result.is_weekend is False
    assert result.is_colombia_holiday is False

    assert result.respuesta == (
        "Perfecto, se refiere a mañana, jueves 14 de mayo. "
        "La doctora solo atiende consultas domiciliarias en la tarde. "
        "Para ese día tengo disponibles entre 3:00 p. m. y 5:00 p. m. "
        "o entre 5:00 p. m. y 7:00 p. m. "
        "¿Cuál le sirve mejor?"
    )


def test_p6f8_day_after_tomorrow_morning_request_is_redirected_to_pm_window(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 13),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Pasado mañana en la mañana",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"

    assert result.fecha_solicitada == "2026-05-15"
    assert result.fecha_solicitada_texto == "viernes 15 de mayo"
    assert result.is_weekend is False
    assert result.is_colombia_holiday is False

    assert result.respuesta == (
        "Perfecto, se refiere a pasado mañana, viernes 15 de mayo. "
        "La doctora solo atiende consultas domiciliarias en la tarde. "
        "Para ese día tengo disponibles entre 3:00 p. m. y 5:00 p. m. "
        "o entre 5:00 p. m. y 7:00 p. m. "
        "¿Cuál le sirve mejor?"
    )


def test_p6f8_sunday_request_is_blocked_in_full_flow(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 16),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Mañana",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"

    assert result.fecha_solicitada == "2026-05-17"
    assert result.fecha_solicitada_texto == "domingo 17 de mayo"
    assert result.is_weekend is True
    assert result.is_colombia_holiday is False
    assert result.slots_candidatos == []

    assert result.respuesta == (
        "Se refiere a mañana, domingo 17 de mayo. "
        "Ese día no se atienden consultas. "
        "¿Le gustaría indicarme otro día entre semana?"
    )


def test_p6f8_colombian_holiday_request_is_blocked_in_full_flow(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 17),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Mañana",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"

    assert result.fecha_solicitada == "2026-05-18"
    assert result.fecha_solicitada_texto == "lunes 18 de mayo"
    assert result.is_weekend is False
    assert result.is_colombia_holiday is True
    assert result.colombia_holiday_name == "Ascensión de Jesús"
    assert result.slots_candidatos == []

    assert result.respuesta == (
        "Se refiere a mañana, lunes 18 de mayo. "
        "Ese día no se atienden consultas porque corresponde al festivo de Ascensión de Jesús. "
        "¿Le gustaría indicarme otro día entre semana?"
    )


def test_p6f8_sunday_word_inside_appointment_date_state_is_treated_as_date(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 13),
    )

    msg = IncomingMessage(
        telefono="573001112675",
        mensaje="El domingo",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"

    assert result.fecha_solicitada == "2026-05-17"
    assert result.fecha_solicitada_texto == "domingo 17 de mayo"
    assert result.is_weekend is True
    assert result.is_colombia_holiday is False

    assert result.respuesta == (
        "Se refiere a domingo 17 de mayo. "
        "Ese día no se atienden consultas. "
        "¿Le gustaría indicarme otro día entre semana?"
    )
