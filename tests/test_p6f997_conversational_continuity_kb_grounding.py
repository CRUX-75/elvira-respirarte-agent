from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.graph.nodes import node_load_kb_context
from app.graph.state import ElviraState
from app.graph.transitions import apply_state_transition
from app.services.appointment_request_runtime import (
    resolve_requested_slot_from_message,
)
from app.services.intent import classify_intent
from app.services.kb import get_kb_context
from app.services.response import generate_response


FIRST_SLOT = "3:00 p. m.–5:00 p. m."
SECOND_SLOT = "5:00 p. m.–7:00 p. m."
CANDIDATE_SLOTS = [FIRST_SLOT, SECOND_SLOT]


@pytest.mark.parametrize(
    ("message", "expected_slot"),
    [
        ("3", FIRST_SLOT),
        ("5", SECOND_SLOT),
    ],
)
def test_p6f997_numeric_slot_selection_is_contextual(
    message: str,
    expected_slot: str,
):
    assert (
        classify_intent(
            message,
            current_state="ST_CITA_FRANJA",
        )
        == "hora_cita"
    )

    assert (
        resolve_requested_slot_from_message(
            message,
            CANDIDATE_SLOTS,
        )
        == expected_slot
    )


@pytest.mark.parametrize("message", ["3", "5"])
def test_p6f997_numeric_slot_selection_is_not_global(message: str):
    assert (
        classify_intent(
            message,
            current_state="ST_GENERAL",
        )
        == "general"
    )


def test_p6f997_general_fallback_inside_slot_flow_does_not_greet_again():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="No entendí",
        sanitized_input="no entendi",
        estado_anterior="ST_CITA_FRANJA",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="general",
        next_action="answer_general",
    )

    result = generate_response(state)

    assert result.respuesta is not None

    normalized_response = result.respuesta.lower()

    forbidden_greetings = (
        "hola",
        "buenos días",
        "buenas tardes",
        "buenas noches",
        "qué gusto saludarle",
        "en qué le podemos ayudar hoy",
    )

    for greeting in forbidden_greetings:
        assert greeting not in normalized_response


def test_p6f997_specific_procedure_question_is_classified_as_services():
    assert (
        classify_intent(
            "Toma de oximetría dinámica.",
            current_state="ST_CITA_PENDIENTE",
        )
        == "servicios"
    )


def test_p6f997_service_match_searches_techniques_and_preserves_current_intent():
    engine = Mock()

    respiratory_service = {
        "service_id": "SRV-01",
        "service_name": "Terapia Respiratoria",
        "category": "Terapia Respiratoria",
        "objective": "Atención respiratoria domiciliaria.",
        "techniques": (
            "Aerosolterapia, drenaje postural, higiene bronquial, "
            "oxigenoterapia, inhaloterapia, oximetría"
        ),
        "patient_scope": "Pacientes que requieren terapia respiratoria.",
        "modality": "Domiciliaria",
        "is_active": True,
        "public_answer_short": (
            "Sí, ofrecemos terapia respiratoria directamente en el domicilio."
        ),
        "public_answer_long": (
            "La terapia respiratoria incluye diferentes procedimientos "
            "registrados en la base de conocimientos."
        ),
        "search_terms": "",
        "escalation_required": False,
    }

    with (
        patch(
            "app.services.kb.search_services",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_active_services",
            return_value=[respiratory_service],
        ),
        patch(
            "app.services.kb.search_schedules",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_all_schedules",
            return_value=[],
        ),
        patch(
            "app.services.kb.search_rules",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_active_rules",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_rules_by_type",
            return_value=[],
        ),
    ):
        result = get_kb_context(
            engine,
            intent="servicios",
            message="Necesito información sobre la toma de oximetría.",
            estado_actual="ST_CITA_PENDIENTE",
        )

    assert result["kb_used"] is True
    assert result["kb_sources"] == ["kb_services"]
    assert "kb_schedules" not in result["kb_sources"]
    assert "Terapia Respiratoria" in result["kb_context"]
    assert "oximetría" in result["kb_context"].lower()
    assert result["matched_service_id"] == "SRV-01"
    assert result["matched_service_term"] == "oximetria"
    assert result["matched_service_field"] == "techniques"
    assert result["service_grounding_status"] == "exact"


def test_p6f997_unknown_procedure_uses_safe_escalation_fallback():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Toma de oximetría dinámica.",
        sanitized_input="toma de oximetria dinamica",
        estado_anterior="ST_CITA_PENDIENTE",
        estado_actual="ST_CITA_PENDIENTE",
        nuevo_estado="ST_CITA_PENDIENTE",
        intent="servicios",
        next_action="answer_services",
        kb_used=False,
        kb_sources=[],
        kb_context=None,
        escalation_required=False,
    )

    result = generate_response(state)

    assert result.escalation_required is True
    assert result.next_action == "escalate_unknown_service"
    assert result.nuevo_estado == "ST_CITA_PENDIENTE"
    assert result.respuesta is not None

    response = result.respuesta.lower()

    assert "información confirmada" in response
    assert "dra." in response or "doctora" in response
    assert "coordinar" not in response
    assert "agendar" not in response
    assert "ofrecemos" not in response


def test_p6f997_service_question_preserves_pending_appointment_state():
    intent = classify_intent(
        "¿Qué servicios ofrece la doctora D'Aleman?",
        current_state="ST_CITA_PENDIENTE",
    )

    state = ElviraState(
        telefono="573001112233",
        mensaje_original="¿Qué servicios ofrece la doctora D'Aleman?",
        sanitized_input="que servicios ofrece la doctora d'aleman",
        estado_anterior="ST_CITA_PENDIENTE",
        estado_actual="ST_CITA_PENDIENTE",
        nuevo_estado="ST_CITA_PENDIENTE",
        intent=intent,
    )

    result = apply_state_transition(state)

    assert result.intent == "servicios"
    assert result.nuevo_estado == "ST_CITA_PENDIENTE"
    assert result.next_action == "answer_services"


def test_p6f997_candidate_slot_copy_does_not_claim_real_availability():
    source_files = (
        Path("app/services/llm.py"),
        Path("app/services/response.py"),
    )

    forbidden_phrases = (
        "para ese día tengo disponibles",
        "solo tenemos disponible la franja",
        "tenemos disponible la franja",
    )

    for source_file in source_files:
        source = source_file.read_text(encoding="utf-8").lower()

        for phrase in forbidden_phrases:
            assert phrase not in source, (
                f"{source_file} todavía contiene lenguaje de disponibilidad "
                f"no confirmada: {phrase!r}"
            )


def test_p6f997_state_machine_test_names_are_unique():
    path = Path("tests/test_state_machine.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    test_names = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]

    duplicates = sorted(
        {
            name
            for name in test_names
            if test_names.count(name) > 1
        }
    )

    assert duplicates == [], f"Duplicate test names found: {duplicates}"


def test_p6f998_dynamic_oximetry_is_exact_approved_service():
    from app.services.kb import get_kb_context

    result = get_kb_context(
        None,
        intent="servicios",
        message="Toma de oximetría dinámica.",
        estado_actual="ST_GENERAL",
    )

    assert result["kb_sources"] == ["kb_services"]
    assert result["matched_service_id"] == "SRV-07"
    assert result["matched_service_term"] == "oximetria dinamica"
    assert result["service_grounding_status"] == "exact"
    assert "orden médica" in result["kb_context"].lower()


def test_p6f997_partial_service_match_is_promoted_to_safe_escalation():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Toma de oximetría dinámica.",
        sanitized_input="toma de oximetria dinamica",
        estado_anterior="ST_CITA_PENDIENTE",
        estado_actual="ST_CITA_PENDIENTE",
        nuevo_estado="ST_CITA_PENDIENTE",
        intent="servicios",
        next_action="answer_services",
    )

    with (
        patch(
            "app.graph.nodes.settings.kb_runtime_enabled",
            True,
        ),
        patch(
            "app.services.kb.get_kb_context",
            return_value={
                "kb_used": True,
                "kb_sources": ["kb_services"],
                "kb_context": (
                    "Servicios activos de Respirarte:\n"
                    "- Terapia Respiratoria | "
                    "procedimientos: oximetría"
                ),
                "matched_service_id": "SRV-01",
                "matched_service_term": "oximetria",
                "matched_service_field": "techniques",
                "service_grounding_status": "partial",
            },
        ),
    ):
        result = node_load_kb_context(state)

    assert result.kb_used is True
    assert result.kb_sources == ["kb_services"]
    assert result.matched_service_id == "SRV-01"
    assert result.matched_service_term == "oximetria"
    assert result.matched_service_field == "techniques"
    assert result.service_grounding_status == "partial"
    assert result.next_action == "escalate_unknown_service"
    assert result.escalation_required is True
    assert (
        result.state_reason
        == "partial_service_match_requires_grounded_review"
    )


def test_p6f997_not_found_service_metadata_is_traceable():
    engine = Mock()

    with (
        patch(
            "app.services.kb.search_services",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_active_services",
            return_value=[],
        ),
        patch(
            "app.services.kb.search_schedules",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_all_schedules",
            return_value=[],
        ),
        patch(
            "app.services.kb.search_rules",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_active_rules",
            return_value=[],
        ),
        patch(
            "app.services.kb.get_rules_by_type",
            return_value=[],
        ),
    ):
        result = get_kb_context(
            engine,
            intent="servicios",
            message="¿Ofrecen un procedimiento inexistente?",
            estado_actual="ST_GENERAL",
        )

    assert result["kb_used"] is False
    assert result["kb_sources"] == []
    assert result["matched_service_id"] is None
    assert result["matched_service_term"] is None
    assert result["matched_service_field"] is None
    assert result["service_grounding_status"] == "not_found"
