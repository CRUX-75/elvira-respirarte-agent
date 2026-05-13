from __future__ import annotations

from unittest.mock import patch

from app.graph.nodes import node_load_kb_context
from app.graph.state import ElviraState


def test_node_load_kb_context_adds_kb_fields_without_changing_state():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="¿Qué servicios ofrecen?",
        sanitized_input="que servicios ofrecen",
        estado_actual="ST_GENERAL",
        nuevo_estado="ST_GENERAL",
        intent="servicios",
        next_action="answer_services",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.services.kb.get_kb_context",
            return_value={
                "kb_used": True,
                "kb_sources": ["kb_services"],
                "kb_context": "Servicios activos de Respirarte: Terapia Respiratoria.",
            },
        ),
    ):
        result = node_load_kb_context(state)

    assert result.kb_used is True
    assert result.kb_sources == ["kb_services"]
    assert "Terapia Respiratoria" in (result.kb_context or "")

    assert result.intent == "servicios"
    assert result.estado_actual == "ST_GENERAL"
    assert result.nuevo_estado == "ST_GENERAL"
    assert result.next_action == "answer_services"


def test_node_load_kb_context_fails_safe_when_enabled():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Hola",
        sanitized_input="hola",
        estado_actual="ST_INIT",
        nuevo_estado="ST_GENERAL",
        intent="general",
        next_action="answer_general",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.services.kb.get_kb_context",
            side_effect=RuntimeError("KB unavailable"),
        ),
    ):
        result = node_load_kb_context(state)

    assert result.kb_used is False
    assert result.kb_sources == []
    assert result.kb_context is None

    assert result.intent == "general"
    assert result.estado_actual == "ST_INIT"
    assert result.nuevo_estado == "ST_GENERAL"
    assert result.next_action == "answer_general"


def test_node_load_kb_context_skips_when_runtime_disabled():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="¿Qué servicios ofrecen?",
        sanitized_input="que servicios ofrecen",
        estado_actual="ST_GENERAL",
        nuevo_estado="ST_GENERAL",
        intent="servicios",
        next_action="answer_services",
    )

    with patch("app.graph.nodes.settings.kb_runtime_enabled", False):
        result = node_load_kb_context(state)

    assert result.kb_used is False
    assert result.kb_sources == []
    assert result.kb_context is None

    assert result.intent == "servicios"
    assert result.estado_actual == "ST_GENERAL"
    assert result.nuevo_estado == "ST_GENERAL"
    assert result.next_action == "answer_services"


def test_node_load_kb_context_services_inside_appointment_state_uses_only_services():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Me podría decir que servicios ofrecen?",
        sanitized_input="me podria decir que servicios ofrecen",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="servicios",
        next_action="answer_services",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.services.kb.get_kb_context",
            return_value={
                "kb_used": True,
                "kb_sources": ["kb_services"],
                "kb_context": "Servicios activos de Respirarte: Terapia Respiratoria.",
            },
        ) as kb_mock,
    ):
        result = node_load_kb_context(state)

    assert result.kb_used is True
    assert result.kb_sources == ["kb_services"]
    assert "Terapia Respiratoria" in (result.kb_context or "")
    assert "kb_schedules" not in result.kb_sources

    assert result.intent == "servicios"
    assert result.estado_actual == "ST_CITA_FRANJA"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "answer_services"

    kb_mock.assert_called_once()
    _, kwargs = kb_mock.call_args
    assert kwargs["intent"] == "servicios"
    assert kwargs["message"] == "Me podría decir que servicios ofrecen?"
    assert kwargs["estado_actual"] == "ST_CITA_FRANJA"


def test_node_load_kb_context_schedule_question_uses_schedules():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Qué horarios manejan?",
        sanitized_input="que horarios manejan",
        estado_actual="ST_GENERAL",
        nuevo_estado="ST_GENERAL",
        intent="horarios",
        next_action="answer_schedules",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.services.kb.get_kb_context",
            return_value={
                "kb_used": True,
                "kb_sources": ["kb_schedules"],
                "kb_context": "Horarios de atención: Lunes a viernes de 15:00 a 21:00.",
            },
        ) as kb_mock,
    ):
        result = node_load_kb_context(state)

    assert result.kb_used is True
    assert result.kb_sources == ["kb_schedules"]
    assert "Lunes a viernes" in (result.kb_context or "")
    assert "15:00" in (result.kb_context or "")
    assert "21:00" in (result.kb_context or "")

    assert result.intent == "horarios"
    assert result.estado_actual == "ST_GENERAL"
    assert result.nuevo_estado == "ST_GENERAL"
    assert result.next_action == "answer_schedules"

    kb_mock.assert_called_once()
    _, kwargs = kb_mock.call_args
    assert kwargs["intent"] == "horarios"
    assert kwargs["message"] == "Qué horarios manejan?"
    assert kwargs["estado_actual"] == "ST_GENERAL"


def test_kb_context_appointment_state_includes_time_slot_disclaimer_rule():
    from app.services.kb import get_kb_context

    engine = object()
    disclaimer = (
        "La franja horaria puede variar por factores externos como el tráfico en Bogotá. "
        "Le pedimos paciencia — la Dra. D'Aleman llegará dentro de la franja confirmada."
    )

    with (
        patch("app.services.kb.search_schedules", return_value=[]),
        patch(
            "app.services.kb.get_all_schedules",
            return_value=[
                {
                    "day_name": "Lunes a viernes",
                    "modality": "Domiciliaria",
                    "start_time": "15:00",
                    "end_time": "19:00",
                    "is_available": True,
                    "notes": "Franja visible al paciente: 2 horas.",
                }
            ],
        ),
        patch(
            "app.services.kb.get_rules_by_type",
            return_value=[
                {
                    "rule_type": "agendamiento",
                    "condition": "appointment_confirmation",
                    "response_rule": disclaimer,
                    "allowed_action": "Incluir disclaimer de franja en toda confirmación de cita",
                    "escalation": False,
                }
            ],
        ) as rules_mock,
    ):
        result = get_kb_context(
            engine,
            intent="fecha_cita",
            message="Mañana en la tarde",
            estado_actual="ST_CITA_FRANJA",
        )

    assert result["kb_used"] is True
    assert "kb_schedules" in result["kb_sources"]
    assert "kb_rules" in result["kb_sources"]
    assert disclaimer in result["kb_context"]
    assert "Nunca confirme" not in result["kb_context"]

    rules_mock.assert_called_once_with(engine, "agendamiento")


def test_kb_context_explicit_services_in_appointment_state_excludes_disclaimer_rules():
    from app.services.kb import get_kb_context

    engine = object()
    disclaimer = "La franja horaria puede variar por factores externos como el tráfico en Bogotá."

    with (
        patch(
            "app.services.kb.search_services",
            return_value=[
                {
                    "service_name": "Terapia Respiratoria Domiciliaria",
                    "public_answer_short": "Atención respiratoria en casa.",
                    "modality": "Domiciliaria",
                    "escalation_required": False,
                }
            ],
        ),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch("app.services.kb.search_schedules") as schedules_mock,
        patch("app.services.kb.get_all_schedules") as all_schedules_mock,
        patch("app.services.kb.get_rules_by_type") as rules_by_type_mock,
        patch("app.services.kb.search_rules") as search_rules_mock,
    ):
        result = get_kb_context(
            engine,
            intent="servicios",
            message="Me podría decir qué servicios ofrecen?",
            estado_actual="ST_CITA_FRANJA",
        )

    assert result["kb_used"] is True
    assert result["kb_sources"] == ["kb_services"]
    assert "Terapia Respiratoria Domiciliaria" in result["kb_context"]
    assert disclaimer not in result["kb_context"]
    assert "kb_rules" not in result["kb_sources"]
    assert "kb_schedules" not in result["kb_sources"]

    schedules_mock.assert_not_called()
    all_schedules_mock.assert_not_called()
    rules_by_type_mock.assert_not_called()
    search_rules_mock.assert_not_called()


def test_kb_context_general_greeting_inside_appointment_state_does_not_load_kb():
    from app.services.kb import get_kb_context

    engine = object()

    with (
        patch("app.services.kb.search_services") as services_mock,
        patch("app.services.kb.get_active_services") as active_services_mock,
        patch("app.services.kb.search_schedules") as schedules_mock,
        patch("app.services.kb.get_all_schedules") as all_schedules_mock,
        patch("app.services.kb.get_rules_by_type") as rules_by_type_mock,
        patch("app.services.kb.search_rules") as search_rules_mock,
        patch("app.services.kb.get_active_rules") as active_rules_mock,
    ):
        result = get_kb_context(
            engine,
            intent="general",
            message="Hola buen día,",
            estado_actual="ST_CITA_FRANJA",
        )

    assert result["kb_used"] is False
    assert result["kb_sources"] == []
    assert result["kb_context"] == ""

    services_mock.assert_not_called()
    active_services_mock.assert_not_called()
    schedules_mock.assert_not_called()
    all_schedules_mock.assert_not_called()
    rules_by_type_mock.assert_not_called()
    search_rules_mock.assert_not_called()
    active_rules_mock.assert_not_called()


def test_node_resolve_date_context_adds_deterministic_fields_for_appointment_date():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.graph.nodes import node_resolve_date_context
    from app.graph.state import ElviraState

    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Mañana en la tarde",
        sanitized_input="mañana en la tarde",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="ask_appointment_time",
    )

    result = node_resolve_date_context(
        state,
        now=datetime(2026, 5, 8, 12, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert result.fecha_actual_colombia == "2026-05-08"
    assert result.fecha_solicitada == "2026-05-09"
    assert result.fecha_solicitada_texto == "sábado 9 de mayo"
    assert result.dia_semana_solicitado == "sábado"
    assert result.es_dia_disponible is False
    assert result.slots_candidatos == []
    assert result.is_weekend is True
    assert result.is_colombia_holiday is False
    assert result.colombia_holiday_name is None


def test_node_resolve_date_context_skips_non_appointment_date_intent():
    from app.graph.nodes import node_resolve_date_context
    from app.graph.state import ElviraState

    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Hola buen día",
        sanitized_input="hola buen dia",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="general",
        next_action="answer_general",
    )

    result = node_resolve_date_context(state)

    assert result.fecha_solicitada is None
    assert result.dia_semana_solicitado is None
    assert result.slots_candidatos == []


def test_kb_context_appointment_time_preference_loads_schedules_and_rules_not_services():
    from unittest.mock import patch

    from app.services.kb import get_kb_context

    engine = object()

    schedule_rows = [
        {
            "day_name": "Lunes a viernes",
            "modality": "Domiciliaria",
            "start_time": "15:00",
            "end_time": "19:00",
            "is_available": True,
            "notes": "Franja sujeta a validación.",
        }
    ]

    rule_rows = [
        {
            "rule_type": "agendamiento",
            "condition": "Preferencia horaria recibida",
            "response_rule": "No confirmar disponibilidad real; registrar preferencia.",
            "allowed_action": "confirm_appointment_request",
            "escalation": False,
        }
    ]

    with (
        patch("app.services.kb.search_services") as services_mock,
        patch("app.services.kb.get_active_services") as active_services_mock,
        patch("app.services.kb.search_schedules", return_value=schedule_rows) as schedules_mock,
        patch("app.services.kb.get_all_schedules") as all_schedules_mock,
        patch("app.services.kb.get_rules_by_type", return_value=rule_rows) as rules_by_type_mock,
        patch("app.services.kb.search_rules") as search_rules_mock,
        patch("app.services.kb.get_active_rules") as active_rules_mock,
    ):
        result = get_kb_context(
            engine,
            intent="hora_cita",
            message="La de 5 de la tarde",
            estado_actual="ST_CITA_FRANJA",
        )

    assert result["kb_used"] is True
    assert result["kb_sources"] == ["kb_schedules", "kb_rules"]
    assert "Horarios y disponibilidad de Respirarte:" in result["kb_context"]
    assert "Reglas operativas relevantes:" in result["kb_context"]
    assert "kb_services" not in result["kb_sources"]

    services_mock.assert_not_called()
    active_services_mock.assert_not_called()
    schedules_mock.assert_called_once()
    all_schedules_mock.assert_not_called()
    rules_by_type_mock.assert_called_once_with(engine, "agendamiento")
    search_rules_mock.assert_not_called()
    active_rules_mock.assert_not_called()
