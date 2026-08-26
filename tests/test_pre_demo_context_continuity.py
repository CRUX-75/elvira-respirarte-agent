from unittest.mock import MagicMock, Mock, patch

from app.graph.nodes import node_load_kb_context
from app.graph.state import ElviraState
from app.repositories import interactions


PHONE = "573001112233"

PREVIOUS_SERVICE_INTERACTION = {
    "mensaje": "Necesito información sobre terapia respiratoria domiciliaria",
    "intent": "servicios",
    "kb_used": True,
}


def _state(
    *,
    message,
    intent,
    current_state="ST_GENERAL",
    next_action="answer_general",
):
    return ElviraState(
        telefono=PHONE,
        mensaje_original=message,
        sanitized_input=message.lower(),
        estado_anterior=current_state,
        estado_actual=current_state,
        nuevo_estado=current_state,
        intent=intent,
        next_action=next_action,
        escalation_required=False,
    )


def _empty_kb():
    return {
        "kb_used": False,
        "kb_sources": [],
        "kb_context": "",
        "matched_service_id": None,
        "matched_service_term": None,
        "matched_service_field": None,
        "service_grounding_status": None,
    }


def _therapy_kb():
    return {
        "kb_used": True,
        "kb_sources": ["kb_services"],
        "kb_context": (
            "Terapia Respiratoria. Atención respiratoria domiciliaria. "
            "No requiere orden médica previa."
        ),
        "matched_service_id": "SRV-01",
        "matched_service_term": "terapia respiratoria domiciliaria",
        "matched_service_field": "service_name",
        "service_grounding_status": "exact",
    }


def _spirometry_kb():
    return {
        "kb_used": True,
        "kb_sources": ["kb_services"],
        "kb_context": "Espirometría simple aprobada.",
        "matched_service_id": "SRV-03",
        "matched_service_term": "espirometria",
        "matched_service_field": "service_name",
        "service_grounding_status": "exact",
    }


def _appointment_kb():
    return {
        "kb_used": True,
        "kb_sources": ["kb_schedules", "kb_rules"],
        "kb_context": "Franjas candidatas sujetas a validación.",
        "matched_service_id": None,
        "matched_service_term": None,
        "matched_service_field": None,
        "service_grounding_status": None,
    }


def _contextual_kb_lookup(
    engine,
    *,
    intent,
    message,
    estado_actual,
):
    if message == PREVIOUS_SERVICE_INTERACTION["mensaje"]:
        assert intent == "servicios"
        return _therapy_kb()

    if estado_actual == "ST_CITA_PENDIENTE":
        return _appointment_kb()

    return _empty_kb()


def test_h2_latest_interaction_lookup_is_read_only_and_phone_scoped():
    reader = getattr(
        interactions,
        "get_latest_interaction_by_phone",
        None,
    )
    assert callable(reader), (
        "H2 requires a read-only latest-interaction repository function"
    )

    fake_engine = MagicMock()
    connection = Mock()
    fake_engine.connect.return_value.__enter__.return_value = connection
    connection.execute.return_value.mappings.return_value.first.return_value = (
        PREVIOUS_SERVICE_INTERACTION
    )

    with patch.object(interactions, "engine", fake_engine):
        result = reader(f" {PHONE} ")

    statement, params = connection.execute.call_args.args
    sql = " ".join(str(statement).upper().split())

    assert sql.startswith("SELECT")
    assert "FROM INTERACTIONS" in sql
    assert "WHERE TELEFONO = :TELEFONO" in sql
    assert "ORDER BY CREATED_AT DESC" in sql
    assert "LIMIT 1" in sql
    assert all(
        mutation not in sql
        for mutation in ("INSERT ", "UPDATE ", "DELETE ")
    )
    assert params == {"telefono": PHONE}
    assert result["mensaje"] == PREVIOUS_SERVICE_INTERACTION["mensaje"]

    fake_engine.connect.assert_called_once_with()
    fake_engine.begin.assert_not_called()


def test_h2_order_question_reuses_exact_previous_service_context():
    state = _state(
        message="¿Necesito orden médica?",
        intent="general",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.repositories.interactions.get_latest_interaction_by_phone",
            return_value=PREVIOUS_SERVICE_INTERACTION,
            create=True,
        ) as previous_mock,
        patch(
            "app.services.kb.get_kb_context",
            side_effect=_contextual_kb_lookup,
        ) as kb_mock,
    ):
        result = node_load_kb_context(state)

    previous_mock.assert_called_once_with(PHONE)
    assert any(
        call.kwargs["intent"] == "servicios"
        and call.kwargs["message"]
        == PREVIOUS_SERVICE_INTERACTION["mensaje"]
        for call in kb_mock.call_args_list
    )
    assert result.kb_used is True
    assert result.kb_sources == ["kb_services"]
    assert result.matched_service_id == "SRV-01"
    assert result.service_grounding_status == "exact"
    assert "orden médica" in (result.kb_context or "").lower()


def test_h2_explicit_new_service_overrides_previous_context():
    state = _state(
        message="¿Hacen espirometría?",
        intent="servicios",
        next_action="answer_services",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.repositories.interactions.get_latest_interaction_by_phone",
            return_value=PREVIOUS_SERVICE_INTERACTION,
            create=True,
        ) as previous_mock,
        patch(
            "app.services.kb.get_kb_context",
            return_value=_spirometry_kb(),
        ),
    ):
        result = node_load_kb_context(state)

    previous_mock.assert_not_called()
    assert result.matched_service_id == "SRV-03"
    assert result.service_grounding_status == "exact"


def test_h2_unrelated_topic_does_not_reuse_stale_service_context():
    state = _state(
        message="¿Qué horarios manejan?",
        intent="horarios",
        next_action="answer_schedules",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.repositories.interactions.get_latest_interaction_by_phone",
            return_value=PREVIOUS_SERVICE_INTERACTION,
            create=True,
        ) as previous_mock,
        patch(
            "app.services.kb.get_kb_context",
            return_value={
                **_empty_kb(),
                "kb_used": True,
                "kb_sources": ["kb_schedules"],
                "kb_context": "Horario de atención confirmado.",
            },
        ),
    ):
        result = node_load_kb_context(state)

    previous_mock.assert_not_called()
    assert result.kb_sources == ["kb_schedules"]
    assert result.matched_service_id is None


def test_h2_appointment_state_does_not_suppress_service_followup():
    state = _state(
        message="¿Necesito orden médica?",
        intent="general",
        current_state="ST_CITA_PENDIENTE",
        next_action="answer_general",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.repositories.interactions.get_latest_interaction_by_phone",
            return_value=PREVIOUS_SERVICE_INTERACTION,
            create=True,
        ) as previous_mock,
        patch(
            "app.services.kb.get_kb_context",
            side_effect=_contextual_kb_lookup,
        ),
    ):
        result = node_load_kb_context(state)

    previous_mock.assert_called_once_with(PHONE)
    assert result.kb_sources == ["kb_services"]
    assert result.matched_service_id == "SRV-01"
    assert "kb_schedules" not in result.kb_sources
    assert "kb_rules" not in result.kb_sources

    assert result.intent == "general"
    assert result.estado_actual == "ST_CITA_PENDIENTE"
    assert result.nuevo_estado == "ST_CITA_PENDIENTE"
    assert result.next_action == "answer_general"


def test_h2_non_grounded_previous_service_is_not_reused():
    state = _state(
        message="¿Necesito orden médica?",
        intent="general",
    )
    invalid_previous = {
        **PREVIOUS_SERVICE_INTERACTION,
        "kb_used": False,
    }

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.repositories.interactions.get_latest_interaction_by_phone",
            return_value=invalid_previous,
            create=True,
        ) as previous_mock,
        patch(
            "app.services.kb.get_kb_context",
            return_value=_empty_kb(),
        ) as kb_mock,
    ):
        result = node_load_kb_context(state)

    previous_mock.assert_called_once_with(PHONE)
    assert all(
        call.kwargs["message"] != invalid_previous["mensaje"]
        for call in kb_mock.call_args_list
    )
    assert result.kb_used is False
    assert result.matched_service_id is None


def test_h2_previous_context_lookup_failure_is_safe():
    state = _state(
        message="¿Necesito orden médica?",
        intent="general",
    )

    with (
        patch("app.graph.nodes.settings.kb_runtime_enabled", True),
        patch(
            "app.repositories.interactions.get_latest_interaction_by_phone",
            side_effect=RuntimeError("database unavailable"),
            create=True,
        ) as previous_mock,
        patch(
            "app.services.kb.get_kb_context",
            return_value=_empty_kb(),
        ),
    ):
        result = node_load_kb_context(state)

    previous_mock.assert_called_once_with(PHONE)
    assert result.kb_used is False
    assert result.kb_context is None
    assert result.intent == "general"
    assert result.next_action == "answer_general"
