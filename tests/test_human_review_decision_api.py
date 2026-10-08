from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import main
from tests.test_human_review_api import FakeHumanReviewRepository


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(main, "get_internal_admin_token", lambda: "test-admin")
    monkeypatch.setattr(
        main, "create_human_review_repository", lambda: FakeHumanReviewRepository(),
    )
    return TestClient(main.app, raise_server_exceptions=False)


def body():
    return {
        "id_solicitud": "SOL-HUMAN-API-001",
        "action": "confirm",
        "actor": "dra_test",
        "confirmed_date": "2026-10-08",
        "confirmed_franja": "15:00–17:00",
        "decision_id": str(uuid4()),
        "expected_updated_at": "2026-10-07T10:00:00+00:00",
    }


def post(api, command):
    return api.post(
        "/internal/human-review/actions",
        headers={"X-Internal-Admin-Token": "test-admin"},
        json=command,
    )


def test_decision_requires_both_id_and_expected_version(api):
    command = body()
    del command["expected_updated_at"]

    assert post(api, command).status_code == 422


def test_projection_failure_can_recover_on_replay_without_whatsapp(api, monkeypatch):
    calls = []
    projections = []
    whatsapp_calls = []

    class Processor:
        def apply(self, *, action, decision_id, expected_updated_at):
            calls.append((action, decision_id, expected_updated_at))
            return {
                "decision_id": decision_id,
                "processed_at": "2026-10-07T10:02:00+00:00",
                "replayed": len(calls) > 1,
                "result": {
                    "success": True,
                    "id_solicitud": action.id_solicitud,
                    "action": action.action,
                    "previous_status": "pendiente_confirmacion",
                    "new_status": "confirmada",
                    "error_code": None,
                },
            }

    def project(outcome):
        projections.append(deepcopy(outcome))
        if len(projections) == 1:
            raise RuntimeError("private Sheets detail")
        return {"status": "updated"}

    async def send(*args, **kwargs):
        whatsapp_calls.append((args, kwargs))

    monkeypatch.setattr(
        main, "create_human_review_decision_processor", lambda: Processor(), raising=False,
    )
    monkeypatch.setattr(main, "_project_human_review_decision", project, raising=False)
    monkeypatch.setattr(main, "send_whatsapp_message", send)
    command = body()

    first = post(api, command)
    second = post(api, command)

    assert first.status_code == second.status_code == 200
    assert first.json()["result"]["success"] is True
    assert first.json()["projection"]["status"] == "failed"
    assert second.json()["projection"]["status"] == "updated"
    assert second.json()["replayed"] is True
    assert first.json()["result"] == second.json()["result"]
    assert calls[0][1] == calls[1][1] == command["decision_id"]
    assert len(projections) == 2
    assert whatsapp_calls == []
    assert "private Sheets detail" not in first.text


def test_processor_error_returns_and_logs_only_safe_details(api, monkeypatch, capsys):
    def unavailable():
        raise RuntimeError("private database credential")

    monkeypatch.setattr(
        main, "create_human_review_decision_processor", unavailable, raising=False,
    )

    response = post(api, body())

    assert response.status_code == 500
    assert response.json()["detail"] == "Human review processing unavailable"
    assert "private database credential" not in response.text
    assert "private database credential" not in capsys.readouterr().out
