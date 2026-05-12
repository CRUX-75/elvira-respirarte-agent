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
        dia_semana_solicitado="martes",
        es_dia_disponible=True,
        slots_candidatos=["15:00–17:00", "17:00–19:00"],
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    assert result.respuesta == (
        "Perfecto. Podemos revisar estas franjas: "
        "15:00–17:00 o 17:00–19:00. "
        "¿Cuál le gustaría que registre como preferencia?"
    )


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
        dia_semana_solicitado="sábado",
        es_dia_disponible=False,
        slots_candidatos=[],
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    assert result.respuesta == (
        "Perfecto. ¿En qué horario le quedaría mejor para registrar su preferencia?"
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
        dia_semana_solicitado="sábado",
        es_dia_disponible=False,
        slots_candidatos=[],
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
