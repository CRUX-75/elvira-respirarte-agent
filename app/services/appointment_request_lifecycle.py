from app.models.appointment_request import AppointmentRequestStatus


class InvalidAppointmentRequestTransition(ValueError):
    """Raised when an appointment request status transition is not allowed."""


_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "nueva": {
        "pendiente_datos",
        "pendiente_confirmacion",
    },
    "pendiente_datos": {
        "pendiente_confirmacion",
        "cancelada",
    },
    "pendiente_confirmacion": {
        "confirmada",
        "cancelada",
    },
    "confirmada": {
        "reagendada",
        "cancelada",
        "cerrada",
    },
    "reagendada": {
        "pendiente_confirmacion",
        "confirmada",
        "cancelada",
    },
    "cancelada": {
        "cerrada",
    },
    "cerrada": set(),
}


def is_valid_transition(
    current_status: AppointmentRequestStatus,
    next_status: AppointmentRequestStatus,
) -> bool:
    """Return True when the lifecycle transition is explicitly allowed."""
    return next_status in _ALLOWED_TRANSITIONS.get(current_status, set())


def validate_transition(
    current_status: AppointmentRequestStatus,
    next_status: AppointmentRequestStatus,
) -> None:
    """Validate an AppointmentRequest lifecycle transition.

    Raises:
        InvalidAppointmentRequestTransition: if the transition is not allowed.
    """
    if not is_valid_transition(current_status, next_status):
        raise InvalidAppointmentRequestTransition(
            f"Invalid AppointmentRequest transition: "
            f"{current_status} -> {next_status}"
        )
