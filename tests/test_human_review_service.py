import pytest

from app.models.human_review import HumanReviewAction
from app.services.human_review_service import HumanReviewService


class FakeAppointmentRequestRepository:
    def __init__(self, request=None):
        self.request = request
        self.updated = None

    def find_by_id_solicitud(self, id_solicitud: str):
        if self.request and self.request["id_solicitud"] == id_solicitud:
            return self.request
        return None

    def update_status(self, id_solicitud: str, new_status: str, updates: dict | None = None):
        self.updated = {
            "id_solicitud": id_solicitud,
            "new_status": new_status,
            "updates": updates or {},
        }
        if self.request:
            self.request["estado_solicitud"] = new_status
        return self.request


def make_request(status: str = "pendiente_confirmacion"):
    return {
        "id_solicitud": "SOL-TEST-001",
        "telefono": "573009420001",
        "nombre_paciente": "Paciente Test",
        "estado_solicitud": status,
        "fecha_solicitada": "2026-06-17",
        "franja_solicitada": "3:00 p. m.–6:00 p. m.",
    }


def make_service(status: str = "pendiente_confirmacion"):
    repo = FakeAppointmentRequestRepository(request=make_request(status))
    return HumanReviewService(repository=repo), repo


def test_confirm_from_pendiente_confirmacion_to_confirmada():
    service, repo = make_service("pendiente_confirmacion")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="confirm",
            actor="dra_daleman",
        )
    )

    assert result.success is True
    assert result.previous_status == "pendiente_confirmacion"
    assert result.new_status == "confirmada"
    assert result.should_notify_patient is True
    assert result.patient_message is not None
    assert repo.updated["new_status"] == "confirmada"


def test_request_missing_data_from_pendiente_confirmacion_to_pendiente_datos():
    service, repo = make_service("pendiente_confirmacion")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="request_missing_data",
            actor="dra_daleman",
            missing_fields=["direccion_paciente"],
        )
    )

    assert result.success is True
    assert result.previous_status == "pendiente_confirmacion"
    assert result.new_status == "pendiente_datos"
    assert result.should_notify_patient is True
    assert repo.updated["new_status"] == "pendiente_datos"


def test_propose_alternative_keeps_pendiente_confirmacion():
    service, repo = make_service("pendiente_confirmacion")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="propose_alternative",
            actor="dra_daleman",
            alternative_date="2026-06-18",
            alternative_franja="5:00 p. m.–7:00 p. m.",
        )
    )

    assert result.success is True
    assert result.previous_status == "pendiente_confirmacion"
    assert result.new_status == "pendiente_confirmacion"
    assert result.should_notify_patient is True
    assert repo.updated["new_status"] == "pendiente_confirmacion"


def test_reschedule_from_confirmada_to_reagendada():
    service, repo = make_service("confirmada")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="reschedule",
            actor="dra_daleman",
            alternative_date="2026-06-18",
            alternative_franja="5:00 p. m.–7:00 p. m.",
        )
    )

    assert result.success is True
    assert result.previous_status == "confirmada"
    assert result.new_status == "reagendada"
    assert result.should_notify_patient is True
    assert repo.updated["new_status"] == "reagendada"


def test_cancel_from_active_status_to_cancelada():
    service, repo = make_service("pendiente_confirmacion")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="cancel",
            actor="dra_daleman",
            reason="No hay disponibilidad",
        )
    )

    assert result.success is True
    assert result.previous_status == "pendiente_confirmacion"
    assert result.new_status == "cancelada"
    assert result.should_notify_patient is True
    assert repo.updated["new_status"] == "cancelada"


def test_close_from_confirmada_to_cerrada():
    service, repo = make_service("confirmada")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="close",
            actor="dra_daleman",
        )
    )

    assert result.success is True
    assert result.previous_status == "confirmada"
    assert result.new_status == "cerrada"
    assert result.should_notify_patient is False
    assert repo.updated["new_status"] == "cerrada"


def test_invalid_action_is_rejected():
    service, repo = make_service("pendiente_confirmacion")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="approve_without_contract",
            actor="dra_daleman",
        )
    )

    assert result.success is False
    assert result.error_code == "invalid_action"
    assert repo.updated is None


def test_missing_request_is_rejected():
    repo = FakeAppointmentRequestRepository(request=None)
    service = HumanReviewService(repository=repo)

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-MISSING",
            action="confirm",
            actor="dra_daleman",
        )
    )

    assert result.success is False
    assert result.error_code == "request_not_found"
    assert repo.updated is None


def test_forbidden_cancelada_to_confirmada_is_rejected():
    service, repo = make_service("cancelada")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="confirm",
            actor="dra_daleman",
        )
    )

    assert result.success is False
    assert result.error_code == "forbidden_transition"
    assert repo.updated is None


def test_forbidden_cerrada_to_active_status_is_rejected():
    service, repo = make_service("cerrada")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="request_missing_data",
            actor="dra_daleman",
            missing_fields=["direccion_paciente"],
        )
    )

    assert result.success is False
    assert result.error_code == "forbidden_transition"
    assert repo.updated is None


def test_missing_required_fields_are_rejected_for_missing_data_action():
    service, repo = make_service("pendiente_confirmacion")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="request_missing_data",
            actor="dra_daleman",
        )
    )

    assert result.success is False
    assert result.error_code == "missing_required_fields"
    assert repo.updated is None


def test_service_does_not_send_whatsapp_messages():
    service, repo = make_service("pendiente_confirmacion")

    result = service.apply_action(
        HumanReviewAction(
            id_solicitud="SOL-TEST-001",
            action="confirm",
            actor="dra_daleman",
        )
    )

    assert result.success is True
    assert result.should_notify_patient is True
    assert result.patient_message is not None
    assert not hasattr(service, "send_whatsapp_message")
