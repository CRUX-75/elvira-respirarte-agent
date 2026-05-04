from __future__ import annotations

from unittest.mock import Mock, patch

from app.services.kb import get_kb_context


def test_kb_context_uses_services_for_service_question():
    engine = Mock()

    with (
        patch(
            "app.services.kb.search_services",
            return_value=[
                {
                    "service_name": "Terapia Respiratoria",
                    "modality": "Domiciliaria",
                    "public_answer_short": "Sí, realizamos terapia respiratoria domiciliaria.",
                    "escalation_required": False,
                }
            ],
        ),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch("app.services.kb.search_schedules", return_value=[]),
        patch("app.services.kb.get_all_schedules", return_value=[]),
        patch("app.services.kb.search_rules", return_value=[]),
        patch("app.services.kb.get_active_rules", return_value=[]),
    ):
        result = get_kb_context(
            engine,
            intent="servicio",
            message="¿Qué servicios ofrecen?",
            estado_actual="ST_GENERAL",
        )

    assert result["kb_used"] is True
    assert "kb_services" in result["kb_sources"]
    assert "Terapia Respiratoria" in result["kb_context"]



def test_kb_context_service_intent_overrides_appointment_state():
    engine = Mock()

    with (
        patch(
            "app.services.kb.search_services",
            return_value=[
                {
                    "service_name": "Terapia Respiratoria",
                    "modality": "Domiciliaria",
                    "public_answer_short": "Sí, ofrecemos terapia respiratoria domiciliaria.",
                    "escalation_required": False,
                }
            ],
        ),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch("app.services.kb.search_schedules", return_value=[]),
        patch("app.services.kb.get_all_schedules", return_value=[]),
        patch("app.services.kb.search_rules", return_value=[]),
        patch("app.services.kb.get_active_rules", return_value=[]),
    ):
        result = get_kb_context(
            engine,
            intent="servicios",
            message="Me podría decir que servicios ofrecen en Respirarte?",
            estado_actual="ST_CITA_FRANJA",
        )

    assert result["kb_used"] is True
    assert result["kb_sources"] == ["kb_services"]
    assert "kb_schedules" not in result["kb_sources"]
    assert "Terapia Respiratoria" in result["kb_context"]


def test_kb_context_uses_schedules_for_appointment_state():
    engine = Mock()

    with (
        patch("app.services.kb.search_services", return_value=[]),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch(
            "app.services.kb.search_schedules",
            return_value=[
                {
                    "day_name": "Lunes a viernes",
                    "modality": "Domiciliaria",
                    "start_time": "15:00",
                    "end_time": "21:00",
                    "is_available": "true",
                    "notes": "Atención domiciliaria en la tarde.",
                }
            ],
        ),
        patch("app.services.kb.get_all_schedules", return_value=[]),
        patch("app.services.kb.search_rules", return_value=[]),
        patch("app.services.kb.get_active_rules", return_value=[]),
    ):
        result = get_kb_context(
            engine,
            intent="cita",
            message="Mañana en la tarde",
            estado_actual="ST_CITA_FECHA",
        )

    assert result["kb_used"] is True
    assert result["kb_sources"] == ["kb_schedules"]
    assert "Lunes a viernes" in result["kb_context"]


def test_kb_context_uses_rules_for_price_question():
    engine = Mock()

    with (
        patch("app.services.kb.search_services", return_value=[]),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch("app.services.kb.search_schedules", return_value=[]),
        patch("app.services.kb.get_all_schedules", return_value=[]),
        patch(
            "app.services.kb.search_rules",
            return_value=[
                {
                    "rule_type": "precio",
                    "condition": "usuario pregunta precio",
                    "response_rule": "No confirmar precios sin evaluación previa.",
                    "allowed_action": "capturar interés y escalar",
                    "escalation": True,
                }
            ],
        ),
        patch("app.services.kb.get_active_rules", return_value=[]),
    ):
        result = get_kb_context(
            engine,
            intent="precio",
            message="¿Cuánto cuesta la terapia?",
            estado_actual="ST_GENERAL",
        )

    assert result["kb_used"] is True
    assert "kb_rules" in result["kb_sources"]
    assert "No confirmar precios" in result["kb_context"]


def test_kb_context_does_not_force_usage_for_irrelevant_message():
    engine = Mock()

    with (
        patch("app.services.kb.search_services", return_value=[]),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch("app.services.kb.search_schedules", return_value=[]),
        patch("app.services.kb.get_all_schedules", return_value=[]),
        patch("app.services.kb.search_rules", return_value=[]),
        patch("app.services.kb.get_active_rules", return_value=[]),
    ):
        result = get_kb_context(
            engine,
            intent="unknown",
            message="Hola",
            estado_actual="ST_INIT",
        )

    assert result == {
        "kb_used": False,
        "kb_sources": [],
        "kb_context": "",
    }


def test_kb_context_explicit_schedule_question_uses_schedules_from_general_state():
    engine = Mock()

    with (
        patch("app.services.kb.search_services", return_value=[]),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch(
            "app.services.kb.search_schedules",
            return_value=[
                {
                    "day_name": "Lunes a viernes",
                    "modality": "Domiciliaria",
                    "start_time": "15:00",
                    "end_time": "21:00",
                    "is_available": "true",
                    "notes": "Atención domiciliaria en la tarde.",
                }
            ],
        ),
        patch("app.services.kb.get_all_schedules", return_value=[]),
        patch("app.services.kb.search_rules", return_value=[]),
        patch("app.services.kb.get_active_rules", return_value=[]),
    ):
        result = get_kb_context(
            engine,
            intent="horarios",
            message="¿Qué horarios manejan?",
            estado_actual="ST_GENERAL",
        )

    assert result["kb_used"] is True
    assert result["kb_sources"] == ["kb_schedules"]
    assert "Lunes a viernes" in result["kb_context"]
    assert "15:00" in result["kb_context"]
    assert "21:00" in result["kb_context"]


def test_kb_context_unknown_service_does_not_invent_kb_context():
    engine = Mock()

    with (
        patch("app.services.kb.search_services", return_value=[]),
        patch("app.services.kb.get_active_services", return_value=[]),
        patch("app.services.kb.search_schedules", return_value=[]),
        patch("app.services.kb.get_all_schedules", return_value=[]),
        patch("app.services.kb.search_rules", return_value=[]),
        patch("app.services.kb.get_active_rules", return_value=[]),
    ):
        result = get_kb_context(
            engine,
            intent="servicios",
            message="¿Ofrecen radiografías a domicilio?",
            estado_actual="ST_GENERAL",
        )

    assert result == {
        "kb_used": False,
        "kb_sources": [],
        "kb_context": "",
    }
