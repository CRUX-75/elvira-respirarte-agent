from datetime import datetime, timezone

from app.services.appointment_request_factory import (
    create_appointment_request,
    generate_appointment_request_id,
)


def test_generate_appointment_request_id_uses_sol_prefix():
    request_id = generate_appointment_request_id(
        telefono="573001112233",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request_id.startswith("SOL-")


def test_generate_appointment_request_id_uses_colombia_time_for_naive_datetime():
    request_id = generate_appointment_request_id(
        telefono="573001112233",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request_id == "SOL-20260526-073022-2233"


def test_generate_appointment_request_id_converts_aware_datetime_to_colombia_time():
    request_id = generate_appointment_request_id(
        telefono="573001112233",
        now=datetime(2026, 5, 26, 12, 30, 22, tzinfo=timezone.utc),
    )

    assert request_id == "SOL-20260526-073022-2233"


def test_generate_appointment_request_id_uses_last_four_phone_digits():
    request_id = generate_appointment_request_id(
        telefono="+57 300 111 2233",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request_id.endswith("-2233")


def test_create_appointment_request_minimal_defaults():
    request = create_appointment_request(
        telefono="573001112233",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request.id_solicitud == "SOL-20260526-073022-2233"
    assert request.telefono == "573001112233"
    assert request.estado_solicitud == "nueva"
    assert request.intent_origen == "cita"
    assert request.canal_origen == "whatsapp"


def test_create_appointment_request_allows_patient_name():
    request = create_appointment_request(
        telefono="573001112233",
        nombre_paciente="María Pérez",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request.nombre_paciente == "María Pérez"


def test_create_appointment_request_allows_requested_date_and_range():
    request = create_appointment_request(
        telefono="573001112233",
        fecha_solicitada="2026-05-27",
        franja_solicitada="tarde",
        hora_solicitada_texto="mañana en la tarde",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request.fecha_solicitada == "2026-05-27"
    assert request.franja_solicitada == "tarde"
    assert request.hora_solicitada_texto == "mañana en la tarde"


def test_create_appointment_request_never_confirms_at_creation():
    request = create_appointment_request(
        telefono="573001112233",
        fecha_solicitada="2026-05-27",
        franja_solicitada="tarde",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request.estado_solicitud != "confirmada"
    assert request.fecha_confirmada is None
    assert request.franja_confirmada is None


def test_create_appointment_request_includes_service_and_address_when_provided():
    request = create_appointment_request(
        telefono="573001112233",
        servicio_solicitado="Terapia respiratoria domiciliaria",
        direccion_domicilio="Calle 123 #45-67",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request.servicio_solicitado == "Terapia respiratoria domiciliaria"
    assert request.direccion_domicilio == "Calle 123 #45-67"


def test_create_appointment_request_sets_created_and_updated_timestamps():
    request = create_appointment_request(
        telefono="573001112233",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request.created_at == "2026-05-26T07:30:22-05:00"
    assert request.updated_at == "2026-05-26T07:30:22-05:00"


def test_create_appointment_request_preserves_source_interaction_id():
    request = create_appointment_request(
        telefono="573001112233",
        source_interaction_id="wamid.test-123",
        now=datetime(2026, 5, 26, 7, 30, 22),
    )

    assert request.source_interaction_id == "wamid.test-123"
