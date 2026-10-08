import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.adapters.google_sheets_human_review_writer import (
    GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
    GoogleSheetsHumanReviewWriter,
    map_appointment_request_to_sheet_row,
)
from app.services.appointment_request_reconciliation import (
    reconcile_appointment_requests,
)
from tests.test_google_sheets_human_review_writer import FakeSheetsClient
from tests.test_postgres_appointment_request_repository import (
    db_engine,
    make_request,
    repository,
)


@pytest.fixture
def projection_context(db_engine, repository):
    migration = (
        Path(__file__).resolve().parents[1]
        / "scripts/sql/010_create_human_review_decisions.sql"
    )
    with db_engine.begin() as conn:
        conn.execute(text(migration.read_text()))

    current = make_request(
        id_solicitud="SOL-PROJECTION-001",
        estado_solicitud="confirmada",
    ).model_copy(update={"updated_at": "2026-10-07T12:00:00+00:00"})
    repository.save(current)
    mapped = map_appointment_request_to_sheet_row(current)
    client = FakeSheetsClient([
        list(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS),
        [mapped[column] for column in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS],
    ])
    writer = GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita",
        enabled=True,
    )
    return db_engine, repository, current, client, writer


def insert_audit(engine, *, decision_id, actor, processed_at):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO human_review_decisions (
                    decision_id, id_solicitud, command_hash,
                    actor, processed_at, result_json
                ) VALUES (
                    :decision_id, :id_solicitud, :command_hash,
                    :actor, :processed_at, :result_json
                )
            """),
            {
                "decision_id": decision_id,
                "id_solicitud": "SOL-PROJECTION-001",
                "command_hash": "a" * 64,
                "actor": actor,
                "processed_at": processed_at,
                "result_json": json.dumps({
                    "id_solicitud": "SOL-PROJECTION-001",
                    "success": True,
                    "error_code": None,
                }),
            },
        )


def audit_rows(engine):
    with engine.begin() as conn:
        return conn.execute(
            text("SELECT * FROM human_review_decisions ORDER BY processed_at")
        ).fetchall()


def sheet_row(client):
    return dict(zip(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS, client.existing_rows[1]))


def test_reconciliation_recovers_audit_after_sheet_failure(projection_context):
    from app.services.human_review_sheet_projector import HumanReviewSheetProjector

    engine, repository, current, client, writer = projection_context
    insert_audit(
        engine,
        decision_id="00000000-0000-0000-0000-000000000001",
        actor="dra_actual",
        processed_at="2026-10-07T12:00:00+00:00",
    )
    before_request = repository.get_by_id(current.id_solicitud).model_dump()
    before_audit = audit_rows(engine)
    original_update = client.update_values

    def fail_write(*args, **kwargs):
        raise RuntimeError("private transport detail")

    client.update_values = fail_write
    projector = HumanReviewSheetProjector(engine=engine, writer=writer)

    first = reconcile_appointment_requests(repository=repository, writer=projector)

    assert first["failed"] == 1
    assert "private transport detail" not in json.dumps(first)
    assert repository.get_by_id(current.id_solicitud).model_dump() == before_request
    assert audit_rows(engine) == before_audit

    client.update_values = original_update
    recovered = reconcile_appointment_requests(repository=repository, writer=projector)

    assert recovered["updated"] == 1
    assert recovered["failed"] == 0
    assert sheet_row(client)["resultado_decision"] == "aplicada"
    assert sheet_row(client)["procesado_por"] == "dra_actual"
    assert audit_rows(engine) == before_audit


def test_projection_reads_current_request_and_latest_audit(projection_context):
    from app.services.human_review_sheet_projector import HumanReviewSheetProjector

    engine, repository, current, client, writer = projection_context
    insert_audit(
        engine,
        decision_id="00000000-0000-0000-0000-000000000001",
        actor="dra_anterior",
        processed_at="2026-10-07T11:00:00+00:00",
    )
    insert_audit(
        engine,
        decision_id="00000000-0000-0000-0000-000000000002",
        actor="dra_actual",
        processed_at="2026-10-07T12:00:00+00:00",
    )
    stale = current.model_copy(update={
        "estado_solicitud": "pendiente_confirmacion",
        "updated_at": "2026-10-07T10:00:00+00:00",
    })
    projector = HumanReviewSheetProjector(engine=engine, writer=writer)

    assert projector.upsert_request(stale) == "updated"

    projected = sheet_row(client)
    assert projected["estado_solicitud"] == "confirmada"
    assert projected["solicitud_updated_at"] == current.updated_at
    assert projected["decision_id_resultado"].endswith("000002")
    assert projected["procesado_por"] == "dra_actual"
    assert len(audit_rows(engine)) == 2
