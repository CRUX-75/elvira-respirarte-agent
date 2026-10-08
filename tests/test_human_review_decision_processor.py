import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.test_postgres_appointment_request_repository import (
    db_engine,
    make_request,
    repository,
)
from app.models.human_review import HumanReviewAction
from app.services.human_review_decision_processor import HumanReviewDecisionProcessor


@pytest.fixture
def decision_context(db_engine, repository):
    with db_engine.begin() as conn:
        migration = (
            Path(__file__).resolve().parents[1]
            / "scripts/sql/010_create_human_review_decisions.sql"
        )
        conn.execute(text(migration.read_text()))

    request = make_request(
        id_solicitud="SOL-DECISION-001",
        estado_solicitud="pendiente_confirmacion",
    )
    request.updated_at = "2026-10-07T10:00:00+00:00"
    repository.save(request)
    return db_engine, repository


def submit(context, *, decision_id, action=None, expected_updated_at=None):
    engine, repository = context
    return HumanReviewDecisionProcessor(engine=engine).apply(
        action=action or HumanReviewAction(
            id_solicitud="SOL-DECISION-001",
            action="confirm",
            actor="dra_test",
            confirmed_date="2026-10-08",
            confirmed_franja="15:00–17:00",
        ),
        decision_id=decision_id,
        expected_updated_at=expected_updated_at or "2026-10-07T10:00:00+00:00",
    )


def decisions(context):
    with context[0].begin() as conn:
        return conn.execute(text("SELECT * FROM human_review_decisions")).mappings().all()


def test_confirm_replay_returns_original_result_without_another_update(decision_context):
    decision_id = str(uuid4())
    first = submit(decision_context, decision_id=decision_id)
    saved = decision_context[1].get_by_id("SOL-DECISION-001").model_dump()
    second = submit(decision_context, decision_id=decision_id)

    assert first["result"]["success"] is True
    assert first["result"]["new_status"] == "confirmada"
    assert first["replayed"] is False
    assert second["replayed"] is True
    assert second["result"] == first["result"]
    assert second["processed_at"] == first["processed_at"]
    assert decision_context[1].get_by_id("SOL-DECISION-001").model_dump() == saved
    assert len(decisions(decision_context)) == 1


def test_proposal_replay_does_not_reapply_same_state_action(decision_context):
    action = HumanReviewAction(
        id_solicitud="SOL-DECISION-001",
        action="propose_alternative",
        actor="dra_test",
        alternative_date="2026-10-08",
        alternative_franja="17:00–19:00",
    )
    decision_id = str(uuid4())
    first = submit(decision_context, decision_id=decision_id, action=action)
    saved = decision_context[1].get_by_id(action.id_solicitud).model_dump()
    second = submit(decision_context, decision_id=decision_id, action=action)

    assert first["result"]["new_status"] == "pendiente_confirmacion"
    assert saved["updated_at"] != "2026-10-07T10:00:00+00:00"
    assert second["replayed"] is True
    assert decision_context[1].get_by_id(action.id_solicitud).model_dump() == saved
    assert len(decisions(decision_context)) == 1


def test_same_id_with_different_command_is_rejected(decision_context):
    decision_id = str(uuid4())
    submit(decision_context, decision_id=decision_id)
    saved = decision_context[1].get_by_id("SOL-DECISION-001").model_dump()
    result = submit(
        decision_context,
        decision_id=decision_id,
        action=HumanReviewAction(
            id_solicitud="SOL-DECISION-001", action="cancel", actor="dra_test",
        ),
    )

    assert result["result"]["error_code"] == "idempotency_conflict"
    assert decision_context[1].get_by_id("SOL-DECISION-001").model_dump() == saved
    assert len(decisions(decision_context)) == 1


def test_stale_version_is_rejected_even_when_status_is_unchanged(decision_context):
    request = decision_context[1].get_by_id("SOL-DECISION-001")
    request.updated_at = "2026-10-07T10:01:00+00:00"
    decision_context[1].update(request)

    result = submit(decision_context, decision_id=str(uuid4()))

    assert result["result"]["error_code"] == "stale_request"
    assert decision_context[1].get_by_id(request.id_solicitud).estado_solicitud == \
        "pendiente_confirmacion"
    assert len(decisions(decision_context)) == 1


def test_invalid_action_is_audited_without_private_payload_or_state_change(decision_context):
    action = HumanReviewAction(
        id_solicitud="SOL-DECISION-001",
        action="unsupported",
        actor="dra_test",
        reason="private clinical detail",
    )
    result = submit(decision_context, decision_id=str(uuid4()), action=action)
    rows = decisions(decision_context)

    assert result["result"]["error_code"] == "invalid_action"
    assert decision_context[1].get_by_id(action.id_solicitud).estado_solicitud == \
        "pendiente_confirmacion"
    assert len(rows) == 1
    assert rows[0]["actor"] == "dra_test"
    assert rows[0]["processed_at"]
    assert json.loads(rows[0]["result_json"])["error_code"] == "invalid_action"
    assert "private clinical detail" not in str(dict(rows[0]))
    assert "patient_message" not in json.loads(rows[0]["result_json"])


def test_audit_insert_failure_rolls_back_appointment_update(decision_context):
    engine, repository = decision_context
    original = repository.get_by_id("SOL-DECISION-001").model_dump()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TRIGGER reject_decision_insert
            BEFORE INSERT ON human_review_decisions
            BEGIN SELECT RAISE(ABORT, 'test audit failure'); END
        """))

    with pytest.raises(Exception):
        submit(decision_context, decision_id=str(uuid4()))

    assert repository.get_by_id("SOL-DECISION-001").model_dump() == original
    assert decisions(decision_context) == []
