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
