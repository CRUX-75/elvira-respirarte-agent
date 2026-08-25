from unittest.mock import Mock, patch

from app.graph.state import ElviraState
from app.services.intent import classify_intent
from app.services.kb import get_kb_context
from app.services.response import generate_response


def test_pre_demo_direct_spirometry_is_classified_as_service():
    assert (
        classify_intent(
            "¿Hacen espirometría?",
            current_state="ST_GENERAL",
        )
        == "servicios"
    )


def test_pre_demo_direct_spirometry_is_grounded_in_approved_kb():
    engine = Mock()
    pulmonary_service = {
        "service_id": "SRV-03",
        "service_name": "Pruebas de Función Pulmonar",
        "category": "Evaluación de función pulmonar",
        "objective": "Evaluar la función pulmonar.",
        "techniques": (
            "Espirometría, caminata de seis minutos, Test de Cooper"
        ),
        "patient_scope": "Pacientes que requieren evaluación pulmonar.",
        "modality": "Domiciliaria",
        "is_active": True,
        "public_answer_short": (
            "Sí, realizamos pruebas de función pulmonar."
        ),
        "public_answer_long": (
            "Las pruebas incluyen espirometría, caminata de seis minutos "
            "y Test de Cooper."
        ),
        "search_terms": "espirometría, espirometria",
        "escalation_required": False,
    }

    with patch(
        "app.services.kb.search_services",
        return_value=[pulmonary_service],
    ):
        result = get_kb_context(
            engine,
            intent="servicios",
            message="¿Hacen espirometría?",
            estado_actual="ST_GENERAL",
        )

    assert result["kb_used"] is True
    assert result["kb_sources"] == ["kb_services"]
    assert result["matched_service_id"] == "SRV-03"
    assert result["service_grounding_status"] == "exact"


def test_pre_demo_all_services_natural_phrase_does_not_escalate_as_unknown():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Deseo conocer todos los servicios",
        sanitized_input="deseo conocer todos los servicios",
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

    assert result.next_action == "answer_services"
    assert result.escalation_required is False
    assert result.respuesta is not None
    assert "información confirmada suficiente" not in result.respuesta.lower()


def test_pre_demo_truly_unknown_service_still_escalates_safely():
    state = ElviraState(
        telefono="573001112233",
        mensaje_original="¿Hacen terapia con delfines?",
        sanitized_input="hacen terapia con delfines",
        estado_anterior="ST_GENERAL",
        estado_actual="ST_GENERAL",
        nuevo_estado="ST_GENERAL",
        intent="servicios",
        next_action="answer_services",
        kb_used=False,
        kb_sources=[],
        kb_context=None,
        escalation_required=False,
    )

    result = generate_response(state)

    assert result.next_action == "escalate_unknown_service"
    assert result.escalation_required is True
