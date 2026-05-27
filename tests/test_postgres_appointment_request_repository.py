import pytest
from sqlalchemy import create_engine, text

from app.models.appointment_request import AppointmentRequest
from app.services.appointment_request_factory import create_appointment_request
from app.repositories.postgres_appointment_request_repository import (
    PostgresAppointmentRequestRepository,
)


def make_request(
    *,
    telefono: str = "+573001112233",
    estado_solicitud: str = "nueva",
    id_solicitud: str | None = None,
    fecha_solicitada: str | None = "2026-06-01",
    franja_solicitada: str | None = "tarde",
    servicio_solicitado: str | None = "Terapia respiratoria",
    direccion_domicilio: str | None = "Calle 123 #45-67",
) -> AppointmentRequest:
    request = create_appointment_request(
        telefono=telefono,
        nombre_paciente="Paciente Test",
        intent_origen="cita",
        canal_origen="whatsapp",
        fecha_solicitada=fecha_solicitada,
        franja_solicitada=franja_solicitada,
        hora_solicitada_texto=None,
        servicio_solicitado=servicio_solicitado,
        direccion_domicilio=direccion_domicilio,
        observaciones="Solicitud creada desde test",
        source_interaction_id="interaction-test-001",
    )

    if id_solicitud is not None:
        request.id_solicitud = id_solicitud

    request.estado_solicitud = estado_solicitud
    return request


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE appointment_requests (
                    id_solicitud TEXT PRIMARY KEY,
                    telefono TEXT NOT NULL,
                    nombre_paciente TEXT,
                    estado_solicitud TEXT NOT NULL,
                    intent_origen TEXT NOT NULL,
                    canal_origen TEXT NOT NULL,
                    fecha_solicitada TEXT,
                    franja_solicitada TEXT,
                    hora_solicitada_texto TEXT,
                    fecha_aceptada TEXT,
                    franja_aceptada TEXT,
                    fecha_confirmada TEXT,
                    franja_confirmada TEXT,
                    servicio_solicitado TEXT,
                    direccion_domicilio TEXT,
                    observaciones TEXT,
                    motivo_reagendamiento TEXT,
                    motivo_cancelacion TEXT,
                    source_interaction_id TEXT,
                    created_by TEXT NOT NULL,
                    updated_by TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )

    return engine


@pytest.fixture
def repository(db_engine):
    return PostgresAppointmentRequestRepository(db_engine)


def test_save_inserts_row(repository):
    request = make_request(id_solicitud="sol-test-save-001")

    saved = repository.save(request)

    assert saved.id_solicitud == "sol-test-save-001"
    assert saved.telefono == "+573001112233"
    assert saved.estado_solicitud == "nueva"


def test_save_duplicate_id_fails(repository):
    request = make_request(id_solicitud="sol-test-duplicate-001")

    repository.save(request)

    with pytest.raises(Exception):
        repository.save(request)


def test_get_by_id_returns_model(repository):
    request = make_request(id_solicitud="sol-test-get-001")
    repository.save(request)

    found = repository.get_by_id("sol-test-get-001")

    assert found is not None
    assert found.id_solicitud == "sol-test-get-001"
    assert found.telefono == request.telefono
    assert found.estado_solicitud == request.estado_solicitud


def test_get_by_id_unknown_returns_none(repository):
    found = repository.get_by_id("sol-does-not-exist")

    assert found is None


def test_update_existing_row(repository):
    request = make_request(id_solicitud="sol-test-update-001")
    repository.save(request)

    request.estado_solicitud = "pendiente_confirmacion"
    request.franja_aceptada = "tarde"
    request.updated_by = "test-update"

    updated = repository.update(request)

    assert updated.id_solicitud == "sol-test-update-001"
    assert updated.estado_solicitud == "pendiente_confirmacion"
    assert updated.franja_aceptada == "tarde"
    assert updated.updated_by == "test-update"

    found = repository.get_by_id("sol-test-update-001")
    assert found is not None
    assert found.estado_solicitud == "pendiente_confirmacion"


def test_update_unknown_fails(repository):
    request = make_request(id_solicitud="sol-test-missing-update-001")

    with pytest.raises(Exception):
        repository.update(request)


def test_find_active_by_telefono_ignores_terminal_requests(repository):
    terminal_request = make_request(
        id_solicitud="sol-test-terminal-001",
        telefono="+573009998877",
        estado_solicitud="cerrada",
    )
    repository.save(terminal_request)

    found = repository.find_active_by_telefono("+573009998877")

    assert found is None


def test_find_active_by_telefono_returns_latest_active_request(repository):
    older_request = make_request(
        id_solicitud="sol-test-active-older",
        telefono="+573007771111",
        estado_solicitud="nueva",
    )
    newer_request = make_request(
        id_solicitud="sol-test-active-newer",
        telefono="+573007771111",
        estado_solicitud="pendiente_confirmacion",
    )

    older_request.created_at = "2026-06-01T10:00:00-05:00"
    older_request.updated_at = "2026-06-01T10:00:00-05:00"
    newer_request.created_at = "2026-06-01T11:00:00-05:00"
    newer_request.updated_at = "2026-06-01T11:00:00-05:00"

    repository.save(older_request)
    repository.save(newer_request)

    found = repository.find_active_by_telefono("+573007771111")

    assert found is not None
    assert found.id_solicitud == "sol-test-active-newer"
    assert found.estado_solicitud == "pendiente_confirmacion"


def test_find_active_by_telefono_returns_none_when_no_request_exists(repository):
    found = repository.find_active_by_telefono("+570000000000")

    assert found is None
