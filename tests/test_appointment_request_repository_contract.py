from app.models.appointment_request import AppointmentRequest


ACTIVE_STATES = {
    "nueva",
    "pendiente_datos",
    "pendiente_confirmacion",
    "confirmada",
    "reagendada",
}

TERMINAL_STATES = {
    "cancelada",
    "cerrada",
}


class InMemoryAppointmentRequestRepository:
    """In-memory repository used only to validate the repository contract."""

    def __init__(self):
        self.requests = {}

    def save(self, request: AppointmentRequest) -> AppointmentRequest:
        self.requests[request.id_solicitud] = request
        return request

    def update(self, request: AppointmentRequest) -> AppointmentRequest:
        if request.id_solicitud not in self.requests:
            raise KeyError(request.id_solicitud)

        self.requests[request.id_solicitud] = request
        return request

    def get_by_id(self, id_solicitud: str) -> AppointmentRequest | None:
        return self.requests.get(id_solicitud)

    def find_active_by_telefono(self, telefono: str) -> AppointmentRequest | None:
        active_requests = [
            request
            for request in self.requests.values()
            if request.telefono == telefono
            and request.estado_solicitud in ACTIVE_STATES
        ]

        if not active_requests:
            return None

        return sorted(
            active_requests,
            key=lambda request: (
                request.updated_at or "",
                request.created_at or "",
                request.id_solicitud,
            ),
            reverse=True,
        )[0]

    def count(self) -> int:
        return len(self.requests)


def create_request(
    *,
    id_solicitud: str = "SOL-TEST-001",
    telefono: str = "+573001112233",
    estado_solicitud: str = "nueva",
    created_at: str = "2026-05-27T10:00:00-05:00",
    updated_at: str = "2026-05-27T10:00:00-05:00",
) -> AppointmentRequest:
    return AppointmentRequest(
        id_solicitud=id_solicitud,
        telefono=telefono,
        nombre_paciente="Paciente Test",
        estado_solicitud=estado_solicitud,
        intent_origen="cita",
        canal_origen="whatsapp",
        fecha_solicitada="2026-05-28",
        franja_solicitada="tarde",
        hora_solicitada_texto=None,
        fecha_aceptada=None,
        franja_aceptada=None,
        fecha_confirmada=None,
        franja_confirmada=None,
        servicio_solicitado="Terapia respiratoria",
        direccion_domicilio="Calle 123 #45-67",
        observaciones=None,
        source_interaction_id=None,
        created_by="system",
        updated_by=None,
        created_at=created_at,
        updated_at=updated_at,
    )


def test_repository_saves_and_gets_request_by_id():
    repository = InMemoryAppointmentRequestRepository()
    request = create_request(id_solicitud="SOL-SAVE-001")

    saved = repository.save(request)

    assert saved.id_solicitud == "SOL-SAVE-001"
    assert repository.get_by_id("SOL-SAVE-001") == request
    assert repository.count() == 1


def test_repository_returns_none_for_unknown_id():
    repository = InMemoryAppointmentRequestRepository()

    result = repository.get_by_id("SOL-UNKNOWN")

    assert result is None


def test_repository_updates_existing_request_without_duplicate():
    repository = InMemoryAppointmentRequestRepository()
    request = create_request(id_solicitud="SOL-UPDATE-001")
    repository.save(request)

    updated = request.model_copy(
        update={
            "estado_solicitud": "pendiente_confirmacion",
            "observaciones": "Paciente debe confirmar nueva franja.",
            "updated_at": "2026-05-27T11:00:00-05:00",
        }
    )

    result = repository.update(updated)

    assert result.id_solicitud == request.id_solicitud
    assert result.estado_solicitud == "pendiente_confirmacion"
    assert repository.count() == 1


def test_repository_rejects_update_for_unknown_request():
    repository = InMemoryAppointmentRequestRepository()
    request = create_request(id_solicitud="SOL-MISSING-001")

    try:
        repository.update(request)
    except KeyError as error:
        assert str(error).strip("'") == "SOL-MISSING-001"
    else:
        raise AssertionError("Expected KeyError for unknown request update")


def test_repository_finds_active_request_by_phone():
    repository = InMemoryAppointmentRequestRepository()
    request = create_request(
        id_solicitud="SOL-ACTIVE-001",
        telefono="+573001112233",
        estado_solicitud="pendiente_confirmacion",
    )
    repository.save(request)

    active = repository.find_active_by_telefono("+573001112233")

    assert active == request


def test_repository_ignores_terminal_requests_when_finding_active_by_phone():
    repository = InMemoryAppointmentRequestRepository()

    for state in TERMINAL_STATES:
        repository.save(
            create_request(
                id_solicitud=f"SOL-{state.upper()}",
                telefono="+573001112233",
                estado_solicitud=state,
            )
        )

    active = repository.find_active_by_telefono("+573001112233")

    assert active is None


def test_repository_returns_latest_active_request_when_multiple_active_exist():
    repository = InMemoryAppointmentRequestRepository()

    older = create_request(
        id_solicitud="SOL-ACTIVE-OLDER",
        telefono="+573001112233",
        estado_solicitud="nueva",
        updated_at="2026-05-27T10:00:00-05:00",
    )
    newer = create_request(
        id_solicitud="SOL-ACTIVE-NEWER",
        telefono="+573001112233",
        estado_solicitud="pendiente_confirmacion",
        updated_at="2026-05-27T12:00:00-05:00",
    )

    repository.save(older)
    repository.save(newer)

    active = repository.find_active_by_telefono("+573001112233")

    assert active == newer
