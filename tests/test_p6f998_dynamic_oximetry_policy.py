from types import SimpleNamespace

from app.services.dynamic_oximetry_policy import (
    DYNAMIC_OXIMETRY_VALIDATION_STATE,
    apply_dynamic_oximetry_policy,
)
from app.services.intent import classify_intent


def _state(
    message: str,
    *,
    current_state: str = "ST_GENERAL",
    matched_service_id: str | None = "SRV-07",
):
    return SimpleNamespace(
        mensaje_original=message,
        estado_actual=current_state,
        nuevo_estado="ST_GENERAL",
        matched_service_id=matched_service_id,
        next_action="answer_services",
        escalation_required=False,
        state_reason=None,
        respuesta=None,
    )


def test_p6f998_information_does_not_start_appointment():
    state = _state(
        "¿Qué es la oximetría dinámica?"
    )

    result = apply_dynamic_oximetry_policy(state)

    assert result is state
    assert result.next_action == (
        "answer_dynamic_oximetry_information"
    )
    assert result.escalation_required is False
    assert "seguimiento continuo" in result.respuesta
    assert "orden médica" in result.respuesta
    assert result.nuevo_estado == "ST_GENERAL"


def test_p6f998_request_asks_for_clinical_requirements():
    state = _state(
        "Quiero agendar una oximetría dinámica"
    )

    result = apply_dynamic_oximetry_policy(state)

    assert result.next_action == (
        "ask_dynamic_oximetry_requirements"
    )
    assert result.nuevo_estado == (
        DYNAMIC_OXIMETRY_VALIDATION_STATE
    )
    assert "orden médica" in result.respuesta
    assert "cuántos días" in result.respuesta


def test_p6f998_missing_order_escalates():
    state = _state(
        "No tengo orden médica y llevo cinco días con oxígeno",
        current_state=DYNAMIC_OXIMETRY_VALIDATION_STATE,
        matched_service_id=None,
    )

    result = apply_dynamic_oximetry_policy(state)

    assert result.escalation_required is True
    assert result.next_action == (
        "escalate_dynamic_oximetry_missing_order"
    )
    assert result.nuevo_estado == "ST_GENERAL"
    assert "requiere orden médica" in result.respuesta


def test_p6f998_fifteen_days_or_more_escalates():
    for message in (
        "Sí tengo orden y llevo 15 días con oxígeno",
        "Tengo la orden y llevo quince días con oxígeno",
        "Tengo orden y llevo más de dos semanas con oxígeno",
    ):
        state = _state(
            message,
            current_state=DYNAMIC_OXIMETRY_VALIDATION_STATE,
            matched_service_id=None,
        )

        result = apply_dynamic_oximetry_policy(state)

        assert result.escalation_required is True
        assert result.next_action == (
            "escalate_dynamic_oximetry_long_oxygen_support"
        )
        assert result.nuevo_estado == "ST_GENERAL"


def test_p6f998_valid_requirements_continue_to_date():
    state = _state(
        "Sí tengo la orden y llevo 8 días con oxígeno",
        current_state=DYNAMIC_OXIMETRY_VALIDATION_STATE,
        matched_service_id=None,
    )

    result = apply_dynamic_oximetry_policy(state)

    assert result.escalation_required is False
    assert result.next_action == "ask_preferred_date"
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert "¿Para qué día" in result.respuesta


def test_p6f998_partial_answers_keep_validation_state():
    has_order = _state(
        "Sí tengo la orden médica",
        current_state=DYNAMIC_OXIMETRY_VALIDATION_STATE,
        matched_service_id=None,
    )
    has_days = _state(
        "Llevo ocho días con oxígeno",
        current_state=DYNAMIC_OXIMETRY_VALIDATION_STATE,
        matched_service_id=None,
    )

    result_order = apply_dynamic_oximetry_policy(has_order)
    result_days = apply_dynamic_oximetry_policy(has_days)

    assert result_order.nuevo_estado == (
        DYNAMIC_OXIMETRY_VALIDATION_STATE
    )
    assert "cuántos días" in result_order.respuesta.lower()

    assert result_days.nuevo_estado == (
        DYNAMIC_OXIMETRY_VALIDATION_STATE
    )
    assert "orden médica" in result_days.respuesta


def test_p6f998_validation_state_routes_back_to_services():
    assert (
        classify_intent(
            "Sí tengo la orden y llevo ocho días",
            DYNAMIC_OXIMETRY_VALIDATION_STATE,
        )
        == "servicios"
    )


def test_p6f998_optout_and_urgency_keep_priority():
    assert (
        classify_intent(
            "No quiero recibir más mensajes",
            DYNAMIC_OXIMETRY_VALIDATION_STATE,
        )
        == "optout"
    )
    assert (
        classify_intent(
            "No puedo respirar",
            DYNAMIC_OXIMETRY_VALIDATION_STATE,
        )
        == "urgencia"
    )
