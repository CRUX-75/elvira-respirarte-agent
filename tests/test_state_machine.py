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
    assert result.respuesta == (
        "Claro, con muchísimo gusto. "
        "Le cuento que las atenciones domiciliarias se manejan solamente en la tarde, "
        "normalmente en dos franjas: de 3:00 p. m. a 5:00 p. m. "
        "o de 5:00 p. m. a 7:00 p. m. "
        "¿Para qué día le gustaría agendar su cita?"
    )

def test_fecha_cita_flow():
    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Para el viernes en la tarde",
        estado_actual="ST_CITA_FECHA",
    )
    result = process_message(msg)
    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"
    assert result.fecha_solicitada is not None
    assert result.es_dia_disponible is True
    assert result.is_weekend is False
    assert result.is_colombia_holiday is False
    assert result.slots_candidatos

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


def test_p6f71_explicit_slot_selection_moves_to_pending_appointment_state():
    cases = [
        "La segunda",
        "La primera",
        "La segunda franja",
        "La primera franja",
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


def test_p6f931_loose_exact_hour_requires_franja_confirmation():
    cases = [
        "A las 5 pm",
        "A las cinco",
        "Se puede a las 4?",
    ]

    for message in cases:
        msg = IncomingMessage(
            telefono="573001112233",
            mensaje=message,
            estado_actual="ST_CITA_FRANJA",
        )

        result = process_message(msg)

        assert result.intent == "hora_cita"
        assert result.nuevo_estado == "ST_CITA_FRANJA"
        assert result.next_action == "ask_confirm_exact_hour_as_slot"
        assert result.state_reason == "requires_exact_hour_franja_confirmation"
        assert "queda registrada" not in result.respuesta.lower()


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
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.state_reason == "unavailable_date_guard"

    assert result.fecha_solicitada == "2026-05-17"
    assert result.fecha_solicitada_texto == "domingo 17 de mayo"
    assert result.is_weekend is True
    assert result.is_colombia_holiday is False
    assert result.slots_candidatos == []

    assert result.respuesta == (
        "Se refiere a mañana, domingo 17 de mayo. "
        "Ese día no se atienden consultas. "
        "¿Para qué día entre semana le gustaría agendar su cita?"
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
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.state_reason == "unavailable_date_guard"

    assert result.fecha_solicitada == "2026-05-18"
    assert result.fecha_solicitada_texto == "lunes 18 de mayo"
    assert result.is_weekend is False
    assert result.is_colombia_holiday is True
    assert result.colombia_holiday_name == "Ascensión de Jesús"
    assert result.slots_candidatos == []

    assert result.respuesta == (
        "Se refiere a mañana, lunes 18 de mayo. "
        "Ese día no se atienden consultas porque corresponde al festivo de Ascensión de Jesús. "
        "¿Para qué día entre semana le gustaría agendar su cita?"
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
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.state_reason == "unavailable_date_guard"

    assert result.fecha_solicitada == "2026-05-17"
    assert result.fecha_solicitada_texto == "domingo 17 de mayo"
    assert result.is_weekend is True
    assert result.is_colombia_holiday is False

    assert result.respuesta == (
        "Se refiere a domingo 17 de mayo. "
        "Ese día no se atienden consultas. "
        "¿Para qué día entre semana le gustaría agendar su cita?"
    )


def test_p6f91419_maniana_afternoon_resolves_date_and_offers_slots(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 13),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Maniana en la tarde",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"
    assert result.fecha_solicitada == "2026-05-14"
    assert result.fecha_solicitada_texto == "jueves 14 de mayo"
    assert result.slots_candidatos == [
        "3:00 p. m.–5:00 p. m.",
        "5:00 p. m.–7:00 p. m.",
    ]

    assert "jueves 14 de mayo" in result.respuesta
    assert "la fecha indicada" not in result.respuesta.lower()


def test_p6f91419_maniana_morning_resolves_date_but_redirects_to_afternoon_slots(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 13),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Maniana en la maniana",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"
    assert result.fecha_solicitada == "2026-05-14"
    assert result.fecha_solicitada_texto == "jueves 14 de mayo"

    assert "jueves 14 de mayo" in result.respuesta
    assert "solo atiende consultas domiciliarias en la tarde" in result.respuesta.lower()
    assert "3:00 p. m." in result.respuesta
    assert "la fecha indicada" not in result.respuesta.lower()


def test_p6f91419_time_window_without_date_does_not_advance_to_slot_state(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 13),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="En la maniana",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.fecha_solicitada is None
    assert result.fecha_solicitada_texto is None
    assert result.slots_candidatos == []

    assert "qué día" in result.respuesta.lower() or "que día" in result.respuesta.lower()
    assert "la fecha indicada" not in result.respuesta.lower()


def test_p6f91419_clarification_question_does_not_become_general(monkeypatch):
    from datetime import date
    from app.services import date_resolver

    monkeypatch.setattr(
        date_resolver,
        "get_today_colombia",
        lambda now=None: date(2026, 5, 13),
    )

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Cual fecha indicada?",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.fecha_solicitada is None
    assert result.fecha_solicitada_texto is None

    assert "qué día" in result.respuesta.lower() or "para qué día" in result.respuesta.lower()
    assert "agendar su cita" in result.respuesta.lower()
    assert "la fecha indicada" not in result.respuesta.lower()


def test_p6f91419_guard_blocks_st_cita_franja_without_fecha_solicitada(monkeypatch):
    from app.services import date_resolver

    def fake_resolve_requested_date(*args, **kwargs):
        from datetime import date
        from app.services.date_resolver import RelativeDateResolution

        return RelativeDateResolution(
            fecha_actual_colombia=date(2026, 5, 13),
            fecha_solicitada=None,
            fecha_solicitada_texto=None,
            dia_semana_solicitado=None,
            es_dia_disponible=False,
            slots_candidatos=[],
            is_weekend=False,
            is_colombia_holiday=False,
            colombia_holiday_name=None,
        )

    monkeypatch.setattr(date_resolver, "resolve_requested_date", fake_resolve_requested_date)

    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="Mañana en la tarde",
        estado_actual="ST_CITA_FECHA",
    )

    result = process_message(msg)

    assert result.intent == "fecha_cita"
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.fecha_solicitada is None
    assert result.slots_candidatos == []


def test_p6f91423_generic_afternoon_reply_with_multiple_slots_stays_in_slot_selection():
    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="En la tarde",
        estado_actual="ST_CITA_FRANJA",
    )

    result = process_message(msg)

    assert result.intent == "hora_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_specific_time_slot"
    assert result.state_reason == "ambiguous_slot_selection_guard"
    assert result.appointment_request_decision.should_persist is False if hasattr(result, "appointment_request_decision") else True


def test_p6f91423_generic_afternoon_reply_with_multiple_slots_stays_in_slot_selection():
    msg = IncomingMessage(
        telefono="573001112233",
        mensaje="En la tarde",
        estado_actual="ST_CITA_FRANJA",
    )

    result = process_message(msg)

    assert result.intent == "hora_cita"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_specific_time_slot"
    assert result.state_reason == "ambiguous_slot_selection_guard"
    assert "franjas disponibles" in result.respuesta.lower()
    assert "3:00 p. m." in result.respuesta
    assert "5:00 p. m." in result.respuesta


def test_p6f91430_hora_cita_on_weekend_does_not_advance_to_pending():
    from app.graph.state import ElviraState
    from app.graph.transitions import apply_state_transition

    state = ElviraState(
        telefono="test-p6f91430",
        mensaje_original="se puede a las 5?",
        sanitized_input="se puede a las 5?",
        estado_actual="ST_CITA_FRANJA",
        intent="hora_cita",
        fecha_solicitada="2026-05-30",
        fecha_solicitada_texto="sábado 30 de mayo",
        es_dia_disponible=False,
        slots_candidatos=[],
        is_weekend=True,
        is_colombia_holiday=False,
    )

    result = apply_state_transition(state)

    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.state_reason == "unavailable_date_guard"


def test_p6f91444_unavailable_holiday_date_stays_in_date_state():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.graph.state import ElviraState
    from app.graph.nodes import (
        node_sanitize_input,
        node_classify_intent,
        node_transition_state,
        node_resolve_date_context,
    )

    state = ElviraState(
        telefono="test-p6f91444",
        mensaje_original="para el próximo lunes",
        sanitized_input="",
        estado_actual="ST_CITA_FECHA",
    )

    state = node_sanitize_input(state)
    state = node_classify_intent(state)
    state = node_transition_state(state)
    state = node_resolve_date_context(
        state,
        now=datetime(2026, 6, 1, 10, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert state.intent == "fecha_cita"
    assert state.fecha_solicitada == "2026-06-08"
    assert state.is_colombia_holiday is True
    assert state.colombia_holiday_name == "Corpus Christi"
    assert state.es_dia_disponible is False
    assert state.slots_candidatos == []

    assert state.nuevo_estado == "ST_CITA_FECHA"
    assert state.estado_actual == "ST_CITA_FECHA"
    assert state.next_action == "ask_preferred_date"
    assert state.state_reason == "unavailable_date_guard"


def test_p6f929_slot_preference_before_date_asks_for_date_without_greeting():
    msg = IncomingMessage(
        telefono="test-p6f929-slot-before-date",
        nombre="Paciente Slot Before Date",
        mensaje="Para la de las 5",
        estado_actual="ST_CITA_FECHA",
        opt_out=False,
    )

    result = process_message(msg)

    assert result.intent == "hora_cita"
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_date_for_slot_preference"
    assert "día o fecha" in result.respuesta
    assert "5:00 p. m. a 7:00 p. m." in result.respuesta
    assert not result.respuesta.lower().startswith("hola")


def test_p6f929_first_slot_preference_before_date_asks_for_date_without_greeting():
    msg = IncomingMessage(
        telefono="test-p6f929-slot-before-date-3",
        nombre="Paciente Slot Before Date",
        mensaje="Para la de las 3",
        estado_actual="ST_CITA_FECHA",
        opt_out=False,
    )

    result = process_message(msg)

    assert result.intent == "hora_cita"
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_date_for_slot_preference"
    assert "día o fecha" in result.respuesta
    assert "3:00 p. m. a 5:00 p. m." in result.respuesta
    assert not result.respuesta.lower().startswith("hola")


def test_p6f942_embedded_date_in_initial_cita_skips_ask_preferred_date():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.graph.state import ElviraState
    from app.graph.nodes import (
        node_sanitize_input,
        node_classify_intent,
        node_resolve_date_context,
        node_transition_state,
    )

    state = ElviraState(
        telefono="test-p6f942-embedded-date",
        mensaje_original="quiero reservar una cita para el miercoles",
        sanitized_input="",
        estado_actual="ST_INIT",
    )

    state = node_sanitize_input(state)
    state = node_classify_intent(state)
    state = node_resolve_date_context(
        state,
        now=datetime(2026, 6, 10, 7, 51, tzinfo=ZoneInfo("America/Bogota")),
    )
    state = node_transition_state(state)

    assert state.intent == "cita"
    assert state.fecha_solicitada == "2026-06-10"
    assert state.fecha_solicitada_texto == "miércoles 10 de junio"
    assert state.es_dia_disponible is True
    assert state.slots_candidatos == ["3:00 p. m.–5:00 p. m."]

    assert state.nuevo_estado == "ST_CITA_FRANJA"
    assert state.next_action == "ask_preferred_time"
    assert state.state_reason == "appointment_intent_with_embedded_date"


