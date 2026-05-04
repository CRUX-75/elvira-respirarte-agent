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
