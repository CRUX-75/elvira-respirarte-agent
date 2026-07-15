from fastapi.testclient import TestClient

from app import main
from app.models.appointment_request import AppointmentRequest


client = TestClient(main.app)


class FakeHumanReviewRepository:
    def __init__(self):
        self.requests = {
            "SOL-HUMAN-API-001": AppointmentRequest(
                id_solicitud="SOL-HUMAN-API-001",
                telefono="573009420001",
                nombre_paciente="Paciente API Test",
                estado_solicitud="pendiente_confirmacion",
                fecha_solicitada="2026-06-17",
                franja_solicitada="3:00 p. m.–6:00 p. m.",
            )
        }

    def get_by_id(self, id_solicitud: str):
        return self.requests.get(id_solicitud)

    def update(self, request: AppointmentRequest):
        self.requests[request.id_solicitud] = request
        return request


def test_human_review_endpoint_requires_internal_admin_token(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "confirm",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing internal admin token"


def test_human_review_endpoint_rejects_invalid_internal_admin_token(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "wrong-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "confirm",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing internal admin token"


def test_human_review_endpoint_confirms_request(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        lambda: FakeHumanReviewRepository(),
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "confirm",
            "actor": "dra_daleman",
            "confirmed_date": "2026-06-17",
            "confirmed_franja": "3:00 p. m.–6:00 p. m.",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["success"] is True
    assert payload["id_solicitud"] == "SOL-HUMAN-API-001"
    assert payload["previous_status"] == "pendiente_confirmacion"
    assert payload["new_status"] == "confirmada"
    assert payload["action"] == "confirm"
    assert payload["should_notify_patient"] is True
    assert payload["patient_message"] is not None
    assert payload["error_code"] is None


def test_human_review_endpoint_returns_structured_business_error(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        lambda: FakeHumanReviewRepository(),
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "approve_without_contract",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["success"] is False
    assert payload["error_code"] == "invalid_action"
    assert payload["should_notify_patient"] is False
    assert payload["patient_message"] is None


def test_human_review_endpoint_does_not_send_whatsapp(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        lambda: FakeHumanReviewRepository(),
        raising=False,
    )

    whatsapp_calls = []

    async def fake_send_whatsapp_message(*args, **kwargs):
        whatsapp_calls.append((args, kwargs))

    monkeypatch.setattr(
        main,
        "send_whatsapp_message",
        fake_send_whatsapp_message,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "confirm",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert whatsapp_calls == []


def test_get_internal_admin_token_reads_settings_field(monkeypatch):
    monkeypatch.setattr(
        main.settings,
        "internal_admin_token",
        "configured-secret-token",
        raising=False,
    )

    assert main.get_internal_admin_token() == "configured-secret-token"




def test_human_review_endpoint_logs_successful_transition(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        lambda: FakeHumanReviewRepository(),
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "confirm",
            "actor": "dra_daleman",
            "confirmed_date": "2026-06-17",
            "confirmed_franja": "3:00 p. m.–6:00 p. m.",
        },
    )

    assert response.status_code == 200

    output = capsys.readouterr().out

    assert "human_review_callback_received" in output
    assert "human_review_transition_applied" in output
    assert "SOL-HUMAN-API-001" in output
    assert "dra_daleman" in output
    assert "pendiente_confirmacion" in output
    assert "confirmada" in output


def test_human_review_endpoint_logs_request_not_found(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        lambda: FakeHumanReviewRepository(),
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-MISSING",
            "action": "confirm",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 200
    assert response.json()["error_code"] == "request_not_found"

    output = capsys.readouterr().out

    assert "human_review_callback_received" in output
    assert "human_review_request_not_found" in output
    assert "SOL-HUMAN-API-MISSING" in output
    assert "dra_daleman" in output
    assert "human_review_transition_applied" not in output


def test_human_review_endpoint_logs_forbidden_transition(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        lambda: FakeHumanReviewRepository(),
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "close",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["success"] is False
    assert payload["error_code"] == "forbidden_transition"
    assert payload["previous_status"] == "pendiente_confirmacion"
    assert payload["new_status"] is None

    output = capsys.readouterr().out

    assert "human_review_callback_received" in output
    assert "human_review_transition_not_applied" in output
    assert "SOL-HUMAN-API-001" in output
    assert "dra_daleman" in output
    assert "pendiente_confirmacion" in output
    assert "forbidden_transition" in output
    assert "human_review_transition_applied" not in output


def test_human_review_endpoint_logs_ignored_invalid_action(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        lambda: FakeHumanReviewRepository(),
        raising=False,
    )

    response = client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "approve_without_contract",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 200
    assert response.json()["error_code"] == "invalid_action"

    output = capsys.readouterr().out

    assert "human_review_callback_received" in output
    assert "human_review_callback_ignored" in output
    assert "SOL-HUMAN-API-001" in output
    assert "dra_daleman" in output
    assert "invalid_action" in output
    assert "human_review_transition_applied" not in output




def test_human_review_endpoint_logs_processing_error(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "get_internal_admin_token",
        lambda: "test-secret-token",
        raising=False,
    )

    def failing_repository_factory():
        raise RuntimeError("repository unavailable")

    monkeypatch.setattr(
        main,
        "create_human_review_repository",
        failing_repository_factory,
        raising=False,
    )

    error_client = TestClient(main.app, raise_server_exceptions=False)

    response = error_client.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-secret-token"},
        json={
            "id_solicitud": "SOL-HUMAN-API-001",
            "action": "confirm",
            "actor": "dra_daleman",
        },
    )

    assert response.status_code == 500

    output = capsys.readouterr().out

    assert "human_review_callback_received" in output
    assert "human_review_processing_error" in output
    assert "SOL-HUMAN-API-001" in output
    assert "dra_daleman" in output
    assert "RuntimeError" in output
    assert "repository unavailable" in output
