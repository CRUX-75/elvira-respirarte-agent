import pytest
from pydantic import ValidationError

from app.models.appointment_request import AppointmentRequest


def test_appointment_request_minimal_creation():
    request = AppointmentRequest(
        id_solicitud="SOL-20260526-073022-0163",
        telefono="573001112233",
    )

    assert request.id_solicitud == "SOL-20260526-073022-0163"
    assert request.telefono == "573001112233"
    assert request.estado_solicitud == "nueva"
    assert request.intent_origen == "cita"
    assert request.canal_origen == "whatsapp"


def test_appointment_request_separates_requested_accepted_and_confirmed_fields():
    request = AppointmentRequest(
        id_solicitud="SOL-20260526-073022-0163",
        telefono="573001112233",
        fecha_solicitada="2026-05-27",
        franja_solicitada="tarde",
        fecha_aceptada="2026-05-28",
        franja_aceptada="tarde",
        fecha_confirmada=None,
        franja_confirmada=None,
    )

    assert request.fecha_solicitada == "2026-05-27"
    assert request.franja_solicitada == "tarde"
    assert request.fecha_aceptada == "2026-05-28"
    assert request.franja_aceptada == "tarde"
    assert request.fecha_confirmada is None
    assert request.franja_confirmada is None


def test_appointment_request_supports_reagendada_status():
    request = AppointmentRequest(
        id_solicitud="SOL-20260526-073022-0163",
        telefono="573001112233",
        estado_solicitud="reagendada",
        motivo_reagendamiento="Paciente aceptó una nueva franja.",
    )

    assert request.estado_solicitud == "reagendada"
    assert request.motivo_reagendamiento == "Paciente aceptó una nueva franja."


def test_appointment_request_includes_service_and_address_fields():
    request = AppointmentRequest(
        id_solicitud="SOL-20260526-073022-0163",
        telefono="573001112233",
        servicio_solicitado="Terapia respiratoria domiciliaria",
        direccion_domicilio="Calle 123 #45-67",
    )

    assert request.servicio_solicitado == "Terapia respiratoria domiciliaria"
    assert request.direccion_domicilio == "Calle 123 #45-67"


def test_appointment_request_rejects_invalid_status():
    with pytest.raises(ValidationError):
        AppointmentRequest(
            id_solicitud="SOL-20260526-073022-0163",
            telefono="573001112233",
            estado_solicitud="agendada_automaticamente",
        )


def test_appointment_request_rejects_invalid_source_channel():
    with pytest.raises(ValidationError):
        AppointmentRequest(
            id_solicitud="SOL-20260526-073022-0163",
            telefono="573001112233",
            canal_origen="n8n",
        )


def test_appointment_request_includes_human_review_operational_fields():
    request = AppointmentRequest(
        id_solicitud="SOL-20260614-001",
        telefono="573001112233",
        tipo_cita="primera_vez",
        eps="Sanitas",
        barrio="Chapinero",
        edad_paciente=7,
        notas_clinicas_breves="Paciente pediátrico con síntomas respiratorios reportados por acudiente.",
    )

    assert request.tipo_cita == "primera_vez"
    assert request.eps == "Sanitas"
    assert request.barrio == "Chapinero"
    assert request.edad_paciente == 7
    assert (
        request.notas_clinicas_breves
        == "Paciente pediátrico con síntomas respiratorios reportados por acudiente."
    )
