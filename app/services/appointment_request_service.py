from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.appointment_request import AppointmentRequest
from app.repositories.appointment_request_repository import AppointmentRequestRepository


COLOMBIA_TIMEZONE = "America/Bogota"

ACTIVE_STATUSES = {
    "nueva",
    "pendiente_datos",
    "pendiente_confirmacion",
    "confirmada",
    "reagendada",
}

TERMINAL_STATUSES = {
    "cancelada",
    "cerrada",
}


class AppointmentRequestNotFound(Exception):
    """Raised when an appointment request cannot be found."""


class InvalidAppointmentRequestTransition(Exception):
    """Raised when an appointment request lifecycle transition is invalid."""


class InvalidAppointmentRequestInput(Exception):
    """Raised when appointment request input is invalid."""


def _last_four_digits(value: str) -> str:
    digits = "".join(char for char in value if char.isdigit())
    return digits[-4:] if len(digits) >= 4 else digits.zfill(4)


def _generate_id_solicitud(telefono: str, now: datetime | None = None) -> str:
    colombia_tz = ZoneInfo(COLOMBIA_TIMEZONE)

    if now is None:
        current_time = datetime.now(colombia_tz)
    elif now.tzinfo is None:
        current_time = now.replace(tzinfo=colombia_tz)
    else:
        current_time = now.astimezone(colombia_tz)

    timestamp = current_time.strftime("%Y%m%d-%H%M%S-%f")
    last4 = _last_four_digits(telefono)

    return f"SOL-{timestamp}-{last4}"


def _field_exists(field_name: str) -> bool:
    return field_name in AppointmentRequest.model_fields


def _copy_with_updates(
    request: AppointmentRequest,
    **updates,
) -> AppointmentRequest:
    allowed_updates = {
        key: value
        for key, value in updates.items()
        if _field_exists(key)
    }

    return request.model_copy(update=allowed_updates)


class AppointmentRequestService:
    """Deterministic orchestration service for AppointmentRequest lifecycle."""

    def __init__(self, repository: AppointmentRequestRepository, factory=None):
        self.repository = repository
        self.factory = factory

    def create_or_reuse_active_request(
        self,
        *,
        telefono: str,
        nombre_paciente: str,
        servicio_solicitado: str,
        direccion_domicilio: str,
        fecha_solicitada: str | None = None,
        franja_solicitada: str | None = None,
        source_interaction_id: str | None = None,
        fuente: str = "whatsapp",
    ) -> AppointmentRequest:
        active_request = self.repository.find_active_by_telefono(telefono)

        if active_request is not None:
            return active_request

        request_data = {
            "id_solicitud": _generate_id_solicitud(telefono),
            "telefono": telefono,
            "nombre_paciente": nombre_paciente,
            "servicio_solicitado": servicio_solicitado,
            "direccion_domicilio": direccion_domicilio,
            "fuente": fuente,
            "estado_solicitud": "nueva",
            "fecha_solicitada": fecha_solicitada,
            "franja_solicitada": franja_solicitada,
            "source_interaction_id": source_interaction_id,
        }

        request = AppointmentRequest(**request_data)

        return self.repository.save(request)

    def transition_request(
        self,
        *,
        id_solicitud: str,
        target_state: str,
        **transition_data,
    ) -> AppointmentRequest:
        request = self.repository.get_by_id(id_solicitud)

        if request is None:
            raise AppointmentRequestNotFound(id_solicitud)

        if not self._is_transition_allowed(
            current_state=request.estado_solicitud,
            target_state=target_state,
        ):
            raise InvalidAppointmentRequestTransition(
                f"Invalid transition from {request.estado_solicitud} to {target_state}"
            )

        updated_request = _copy_with_updates(
            request,
            estado_solicitud=target_state,
            **transition_data,
        )

        return self.repository.update(updated_request)

    def apply_contraoffer(
        self,
        *,
        id_solicitud: str,
        fecha_propuesta: str | None = None,
        franja_propuesta: str | None = None,
        motivo: str | None = None,
    ) -> AppointmentRequest:
        return self.transition_request(
            id_solicitud=id_solicitud,
            target_state="pendiente_confirmacion",
            fecha_propuesta=fecha_propuesta,
            franja_propuesta=franja_propuesta,
            motivo=motivo,
        )

    def apply_reschedule(
        self,
        *,
        id_solicitud: str,
        fecha_confirmada: str | None = None,
        franja_confirmada: str | None = None,
        motivo: str | None = None,
    ) -> AppointmentRequest:
        return self.transition_request(
            id_solicitud=id_solicitud,
            target_state="reagendada",
            fecha_confirmada=fecha_confirmada,
            franja_confirmada=franja_confirmada,
            motivo=motivo,
        )

    def cancel_request(
        self,
        *,
        id_solicitud: str,
        reason: str | None = None,
    ) -> AppointmentRequest:
        return self.transition_request(
            id_solicitud=id_solicitud,
            target_state="cancelada",
            motivo_cancelacion=reason,
        )

    def complete_request(self, *, id_solicitud: str) -> AppointmentRequest:
        return self.transition_request(
            id_solicitud=id_solicitud,
            target_state="cerrada",
        )

    def _is_transition_allowed(self, *, current_state: str, target_state: str) -> bool:
        if current_state in TERMINAL_STATUSES:
            return False

        allowed_transitions = {
            "nueva": {
                "pendiente_datos",
                "pendiente_confirmacion",
                "confirmada",
                "cancelada",
            },
            "pendiente_datos": {
                "pendiente_confirmacion",
                "confirmada",
                "cancelada",
            },
            "pendiente_confirmacion": {
                "confirmada",
                "reagendada",
                "cancelada",
            },
            "confirmada": {
                "reagendada",
                "cancelada",
                "cerrada",
            },
            "reagendada": {
                "confirmada",
                "cancelada",
                "cerrada",
            },
        }

        return target_state in allowed_transitions.get(current_state, set())
