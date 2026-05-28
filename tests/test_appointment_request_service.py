import pytest

from app.models.appointment_request import AppointmentRequest
from app.services.appointment_request_factory import AppointmentRequestFactory
from app.services.appointment_request_service import (
    AppointmentRequestNotFound,
    AppointmentRequestService,
    InvalidAppointmentRequestTransition,
)


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


class FakeAppointmentRequestRepository:
    def __init__(self):
        self.requests = {}

    def save(self, request: AppointmentRequest) -> AppointmentRequest:
        self.requests[request.id_solicitud] = request
        return request

    def update(self, request: AppointmentRequest) -> AppointmentRequest:
        self.requests[request.id_solicitud] = request
        return request

    def get_by_id(self, id_solicitud: str) -> AppointmentRequest | None:
        return self.requests.get(id_solicitud)

    def find_active_by_telefono(self, telefono: str) -> AppointmentRequest | None:
        for request in self.requests.values():
            if request.telefono == telefono and request.estado_solicitud in ACTIVE_STATUSES:
                return request
        return None

    def count(self) -> int:
        return len(self.requests)


@pytest.fixture
def repository():
    return FakeAppointmentRequestRepository()


@pytest.fixture
def service(repository):
    return AppointmentRequestService(
        repository=repository,
        factory=AppointmentRequestFactory(),
    )


def create_request(
    *,
    telefono: str = "+573001112233",
    estado: str = "nueva",
    id_solicitud: str = "SOL-TEST-001",
) -> AppointmentRequest:
    return AppointmentRequest(
        id_solicitud=id_solicitud,
        telefono=telefono,
        nombre_paciente="Paciente Test",
        servicio_solicitado="Terapia respiratoria",
        direccion_domicilio="Calle 123 #45-67",
        fuente="whatsapp",
        estado_solicitud=estado,
        fecha_solicitada="2026-05-27",
        franja_solicitada="tarde",
    )


def test_creates_new_request_when_no_active_request_exists(service, repository):
    request = service.create_or_reuse_active_request(
        telefono="+573001112233",
        nombre_paciente="Paciente Test",
        servicio_solicitado="Terapia respiratoria",
        direccion_domicilio="Calle 123 #45-67",
        fecha_solicitada="2026-05-27",
        franja_solicitada="tarde",
        fuente="whatsapp",
    )

    assert request.id_solicitud
    assert request.estado_solicitud == "nueva"
    assert repository.count() == 1


@pytest.mark.parametrize(
    "active_status",
    [
        "nueva",
        "pendiente_datos",
        "pendiente_confirmacion",
        "confirmada",
        "reagendada",
    ],
)
def test_reuses_existing_active_request(service, repository, active_status):
    existing = create_request(
        estado=active_status,
        id_solicitud=f"SOL-ACTIVE-{active_status}",
    )
    repository.save(existing)

    result = service.create_or_reuse_active_request(
        telefono=existing.telefono,
        nombre_paciente="Paciente Test",
        servicio_solicitado="Terapia respiratoria",
        direccion_domicilio="Calle 123 #45-67",
        fecha_solicitada="2026-05-28",
        franja_solicitada="mañana",
        fuente="whatsapp",
    )

    assert result.id_solicitud == existing.id_solicitud
    assert result.estado_solicitud == active_status
    assert repository.count() == 1


@pytest.mark.parametrize(
    "terminal_status",
    [
        "cancelada",
        "cerrada",
    ],
)
def test_creates_new_request_after_terminal_request(service, repository, terminal_status):
    previous = create_request(
        estado=terminal_status,
        id_solicitud=f"SOL-TERMINAL-{terminal_status}",
    )
    repository.save(previous)

    result = service.create_or_reuse_active_request(
        telefono=previous.telefono,
        nombre_paciente="Paciente Test",
        servicio_solicitado="Terapia respiratoria",
        direccion_domicilio="Calle 123 #45-67",
        fecha_solicitada="2026-05-28",
        franja_solicitada="mañana",
        fuente="whatsapp",
    )

    assert result.id_solicitud != previous.id_solicitud
    assert result.estado_solicitud == "nueva"
    assert repository.count() == 2


def test_preserves_id_solicitud_during_contraoffer(service, repository):
    existing = create_request(
        estado="nueva",
        id_solicitud="SOL-CONTRA-001",
    )
    repository.save(existing)

    result = service.apply_contraoffer(
        id_solicitud=existing.id_solicitud,
        fecha_propuesta="2026-05-29",
        franja_propuesta="tarde",
        motivo="La franja solicitada no está disponible.",
    )

    assert result.id_solicitud == existing.id_solicitud
    assert result.estado_solicitud == "pendiente_confirmacion"
    assert repository.count() == 1


def test_preserves_id_solicitud_during_reschedule(service, repository):
    existing = create_request(
        estado="confirmada",
        id_solicitud="SOL-REAG-001",
    )
    repository.save(existing)

    result = service.apply_reschedule(
        id_solicitud=existing.id_solicitud,
        fecha_confirmada="2026-05-30",
        franja_confirmada="mañana",
        motivo="Paciente solicita cambio de horario.",
    )

    assert result.id_solicitud == existing.id_solicitud
    assert result.estado_solicitud == "reagendada"
    assert repository.count() == 1


def test_rejects_invalid_lifecycle_transition(service, repository):
    existing = create_request(
        estado="cerrada",
        id_solicitud="SOL-INVALID-001",
    )
    repository.save(existing)

    with pytest.raises(InvalidAppointmentRequestTransition):
        service.transition_request(
            id_solicitud=existing.id_solicitud,
            target_state="pendiente_confirmacion",
        )

    unchanged = repository.get_by_id(existing.id_solicitud)

    assert unchanged.estado_solicitud == "cerrada"


def test_raises_not_found_for_unknown_id_solicitud(service):
    with pytest.raises(AppointmentRequestNotFound):
        service.transition_request(
            id_solicitud="SOL-DOES-NOT-EXIST",
            target_state="pendiente_confirmacion",
        )


def test_terminal_states_are_not_active(repository):
    cancelled = create_request(
        estado="cancelada",
        id_solicitud="SOL-CANCELLED-001",
    )
    closed = create_request(
        estado="cerrada",
        id_solicitud="SOL-CLOSED-001",
    )

    repository.save(cancelled)
    repository.save(closed)

    active = repository.find_active_by_telefono(cancelled.telefono)

    assert active is None


def test_create_or_reuse_active_request_allows_runtime_status(repository):
    service = AppointmentRequestService(repository=repository)

    request = service.create_or_reuse_active_request(
        telefono="3001234567",
        nombre_paciente="Paciente Runtime",
        servicio_solicitado="",
        direccion_domicilio="",
        fecha_solicitada="2026-05-29",
        franja_solicitada="3:00 p. m.–5:00 p. m.",
        source_interaction_id="test-stateful-runtime-status",
        estado_solicitud="pendiente_confirmacion",
    )

    assert request.estado_solicitud == "pendiente_confirmacion"
    assert request.fecha_solicitada == "2026-05-29"
    assert request.franja_solicitada == "3:00 p. m.–5:00 p. m."
