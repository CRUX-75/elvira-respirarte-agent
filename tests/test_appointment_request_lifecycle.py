import pytest

from app.services.appointment_request_lifecycle import (
    InvalidAppointmentRequestTransition,
    is_valid_transition,
    validate_transition,
)


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        ("nueva", "pendiente_datos"),
        ("nueva", "pendiente_confirmacion"),
        ("pendiente_datos", "pendiente_confirmacion"),
        ("pendiente_datos", "cancelada"),
        ("pendiente_confirmacion", "confirmada"),
        ("pendiente_confirmacion", "cancelada"),
        ("confirmada", "reagendada"),
        ("confirmada", "cancelada"),
        ("confirmada", "cerrada"),
        ("reagendada", "pendiente_confirmacion"),
        ("reagendada", "confirmada"),
        ("reagendada", "cancelada"),
        ("cancelada", "cerrada"),
    ],
)
def test_allows_valid_transitions(current_status, next_status):
    assert is_valid_transition(current_status, next_status) is True
    validate_transition(current_status, next_status)


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        ("nueva", "confirmada"),
        ("pendiente_datos", "confirmada"),
        ("cancelada", "confirmada"),
        ("cerrada", "confirmada"),
        ("cerrada", "pendiente_confirmacion"),
        ("cancelada", "reagendada"),
        ("nueva", "reagendada"),
    ],
)
def test_rejects_invalid_transitions(current_status, next_status):
    assert is_valid_transition(current_status, next_status) is False

    with pytest.raises(InvalidAppointmentRequestTransition):
        validate_transition(current_status, next_status)


def test_protects_confirmation_from_initial_state():
    with pytest.raises(InvalidAppointmentRequestTransition):
        validate_transition("nueva", "confirmada")


def test_protects_confirmation_when_data_is_incomplete():
    with pytest.raises(InvalidAppointmentRequestTransition):
        validate_transition("pendiente_datos", "confirmada")


def test_allows_confirmation_only_from_review_ready_or_rescheduled():
    validate_transition("pendiente_confirmacion", "confirmada")
    validate_transition("reagendada", "confirmada")


def test_allows_rescheduling_from_confirmed_request():
    validate_transition("confirmada", "reagendada")


def test_allows_rescheduled_request_to_return_to_human_review():
    validate_transition("reagendada", "pendiente_confirmacion")


def test_rejects_unknown_current_status():
    assert is_valid_transition("estado_inexistente", "confirmada") is False

    with pytest.raises(InvalidAppointmentRequestTransition):
        validate_transition("estado_inexistente", "confirmada")


def test_rejects_unknown_next_status():
    assert is_valid_transition("nueva", "estado_inexistente") is False

    with pytest.raises(InvalidAppointmentRequestTransition):
        validate_transition("nueva", "estado_inexistente")
