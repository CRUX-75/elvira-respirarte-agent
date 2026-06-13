from app.graph.state import ElviraState
from app.services import llm


def test_preferred_time_response_is_deterministic_with_slots():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Mañana en la tarde",
        sanitized_input="mañana en la tarde",
        estado_actual="ST_CITA_FECHA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="ask_preferred_time",
        fecha_actual_colombia="2026-05-11",
        fecha_solicitada="2026-05-12",
        fecha_solicitada_texto="martes 12 de mayo",
        dia_semana_solicitado="martes",
        es_dia_disponible=True,
        slots_candidatos=["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
        is_weekend=False,
        is_colombia_holiday=False,
        colombia_holiday_name=None,
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    assert result.respuesta == (
        "Perfecto, se refiere a mañana, martes 12 de mayo. "
        "La doctora solo atiende consultas domiciliarias en la tarde. "
        "Para ese día tengo disponibles entre 3:00 p. m. y 5:00 p. m. "
        "o entre 5:00 p. m. y 7:00 p. m. "
        "¿Cuál le sirve mejor?"
    )


def test_preferred_time_response_with_single_slot_does_not_ask_which_one():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="El miércoles",
        sanitized_input="el miércoles",
        estado_actual="ST_CITA_FECHA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="ask_preferred_time",
        fecha_actual_colombia="2026-05-11",
        fecha_solicitada="2026-05-13",
        fecha_solicitada_texto="miércoles 13 de mayo",
        dia_semana_solicitado="miércoles",
        es_dia_disponible=True,
        slots_candidatos=["3:00 p. m.–5:00 p. m."],
        is_weekend=False,
        is_colombia_holiday=False,
        colombia_holiday_name=None,
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    assert result.respuesta == (
        "Perfecto, se refiere a miércoles 13 de mayo. "
        "La doctora solo atiende consultas domiciliarias en la tarde. "
        "Para ese día solo tenemos disponible la franja de 3:00 p. m. a 5:00 p. m. "
        "¿Desea que registre esa franja como preferencia?"
    )
    assert "¿Cuál le sirve mejor?" not in result.respuesta
    assert "tengo disponibles" not in result.respuesta


def test_preferred_time_response_is_deterministic_without_slots():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Mañana en la tarde",
        sanitized_input="mañana en la tarde",
        estado_actual="ST_CITA_FECHA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="ask_preferred_time",
        fecha_actual_colombia="2026-05-08",
        fecha_solicitada="2026-05-09",
        fecha_solicitada_texto="sábado 9 de mayo",
        dia_semana_solicitado="sábado",
        es_dia_disponible=False,
        slots_candidatos=[],
        is_weekend=True,
        is_colombia_holiday=False,
        colombia_holiday_name=None,
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    assert result.respuesta == (
        "Se refiere a mañana, sábado 9 de mayo. "
        "Ese día no se atienden consultas. "
        "¿Para qué día entre semana le gustaría agendar su cita?"
    )


def test_date_context_section_includes_deterministic_date_context():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Mañana en la tarde",
        sanitized_input="mañana en la tarde",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="answer_general",
        fecha_actual_colombia="2026-05-08",
        fecha_solicitada="2026-05-09",
        fecha_solicitada_texto="sábado 9 de mayo",
        dia_semana_solicitado="sábado",
        es_dia_disponible=False,
        slots_candidatos=[],
        is_weekend=True,
        is_colombia_holiday=False,
        colombia_holiday_name=None,
        date_resolution_source="deterministic_relative_date_resolver",
    )

    date_context = llm._build_date_context_section(state)

    assert "Contexto determinístico de fecha:" in date_context
    assert "Fecha actual en Colombia: 2026-05-08" in date_context
    assert "Fecha solicitada por el paciente: 2026-05-09" in date_context
    assert "Día de semana solicitado: sábado" in date_context
    assert "Día operativo según reglas internas: False" in date_context
    assert "Slots candidatos generados: sin slots candidatos" in date_context
    assert "no ofrezca horas ni slots" in date_context
    assert "nunca como disponibilidad confirmada" in date_context


def test_date_context_section_does_not_expose_operational_day_without_requested_date():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Hola buenas",
        sanitized_input="hola buenas",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="general",
        next_action="answer_general",
        fecha_actual_colombia="2026-05-11",
        fecha_solicitada=None,
        dia_semana_solicitado=None,
        es_dia_disponible=False,
        slots_candidatos=[],
        date_resolution_source="deterministic_relative_date_resolver",
    )

    date_context = llm._build_date_context_section(state)

    assert "No hay fecha solicitada detectada para este mensaje." in date_context
    assert "No interprete disponibilidad operativa sin una fecha solicitada explícita." in date_context
    assert "No diga que hoy no se opera" in date_context
    assert "Día operativo según reglas internas: False" not in date_context
    assert "Slots candidatos generados" not in date_context


def test_preferred_time_response_blocks_colombian_holiday():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Quiero cita el lunes",
        sanitized_input="quiero cita el lunes",
        estado_actual="ST_CITA_FECHA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="ask_preferred_time",
        fecha_actual_colombia="2026-05-17",
        fecha_solicitada="2026-05-18",
        fecha_solicitada_texto="lunes 18 de mayo",
        dia_semana_solicitado="lunes",
        es_dia_disponible=False,
        slots_candidatos=[],
        is_weekend=False,
        is_colombia_holiday=True,
        colombia_holiday_name="Ascensión de Jesús",
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    assert result.respuesta == (
        "Se refiere a lunes 18 de mayo. "
        "Ese día no se atienden consultas porque corresponde al festivo de Ascensión de Jesús. "
        "¿Para qué día entre semana le gustaría agendar su cita?"
    )


def test_preferred_time_response_clarifies_afternoon_for_day_after_tomorrow_morning_request():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Pasado mañana en la mañana",
        sanitized_input="pasado mañana en la mañana",
        estado_actual="ST_CITA_FECHA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="ask_preferred_time",
        fecha_actual_colombia="2026-05-13",
        fecha_solicitada="2026-05-15",
        fecha_solicitada_texto="viernes 15 de mayo",
        dia_semana_solicitado="viernes",
        es_dia_disponible=True,
        slots_candidatos=["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
        is_weekend=False,
        is_colombia_holiday=False,
        colombia_holiday_name=None,
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    assert result.respuesta == (
        "Perfecto, se refiere a pasado mañana, viernes 15 de mayo. "
        "La doctora solo atiende consultas domiciliarias en la tarde. "
        "Para ese día tengo disponibles entre 3:00 p. m. y 5:00 p. m. "
        "o entre 5:00 p. m. y 7:00 p. m. "
        "¿Cuál le sirve mejor?"
    )


def test_p6f941_exact_hour_clarification_uses_single_real_slot_from_context():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="si por favor, es posible que lleguen a las 4?",
        sanitized_input="si por favor, es posible que lleguen a las 4?",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="hora_cita",
        next_action="ask_confirm_exact_hour_as_slot",
        fecha_solicitada="2026-06-17",
        fecha_solicitada_texto="miércoles 17 de junio",
        slots_candidatos=["3:00 p. m.–6:00 p. m."],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
    )

    result = llm.generate_llm_response(state)

    assert "hora exacta garantizada" in result.respuesta
    assert "3:00 p. m. a 6:00 p. m." in result.respuesta
    assert "3:00 p. m. a 5:00 p. m." not in result.respuesta
    assert "5:00 p. m. a 7:00 p. m." not in result.respuesta
    assert "¿Desea que registre esa franja como preferencia?" in result.respuesta


def test_p6f941_exact_hour_clarification_lists_multiple_real_slots_from_context():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="se puede a las 4?",
        sanitized_input="se puede a las 4?",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="hora_cita",
        next_action="ask_confirm_exact_hour_as_slot",
        fecha_solicitada="2026-06-16",
        fecha_solicitada_texto="martes 16 de junio",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
    )

    result = llm.generate_llm_response(state)

    assert "hora exacta garantizada" in result.respuesta
    assert "3:00 p. m. a 5:00 p. m." in result.respuesta
    assert "5:00 p. m. a 7:00 p. m." in result.respuesta
    assert "¿Cuál le queda mejor?" in result.respuesta
