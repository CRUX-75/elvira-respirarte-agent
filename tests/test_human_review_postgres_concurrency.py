from concurrent.futures import ThreadPoolExecutor, TimeoutError
import os
from pathlib import Path
import threading
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL

from app.models.appointment_request import AppointmentRequest
from app.models.human_review import HumanReviewAction
from app.repositories.postgres_appointment_request_repository import (
    PostgresAppointmentRequestRepository,
)
from app.services.human_review_decision_processor import HumanReviewDecisionProcessor
from app.services.human_review_sheet_projector import HumanReviewSheetProjector


pytestmark = pytest.mark.skipif(
    os.getenv("P6_F16_POSTGRES_TESTS") != "1",
    reason="Requires the dedicated local P6-F.16 PostgreSQL test container.",
)


@pytest.fixture
def pg_context():
    url = URL.create(
        "postgresql+psycopg",
        username="postgres",
        host="127.0.0.1",
        port=15432,
        database="elvira_p6_f16_test",
    )
    admin = create_engine(url)
    schema = "p6_f16_test_" + uuid4().hex
    engine = None
    created = False
    try:
        with admin.begin() as conn:
            assert conn.execute(text("SELECT current_database()")).scalar_one() == (
                "elvira_p6_f16_test"
            )
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            created = True

        engine = create_engine(
            url,
            connect_args={
                "options": (
                    f"-csearch_path={schema} "
                    "-clock_timeout=5000 -cstatement_timeout=10000"
                ),
            },
            pool_size=5,
            max_overflow=0,
            pool_timeout=5,
        )
        root = Path(__file__).resolve().parents[1] / "scripts/sql"
        with engine.begin() as conn:
            for filename in [
                "001_create_appointment_requests.sql",
                "004_add_human_review_operational_fields.sql",
                "010_create_human_review_decisions.sql",
            ]:
                conn.exec_driver_sql((root / filename).read_text())

        repository = PostgresAppointmentRequestRepository(engine)
        repository.save(AppointmentRequest(
            id_solicitud="SOL-PG-CONCURRENCY-001",
            telefono="0000000000",
            estado_solicitud="pendiente_confirmacion",
            canal_origen="manual",
            created_by="test",
            created_at="2026-10-07T10:00:00+00:00",
            updated_at="2026-10-07T10:00:00+00:00",
        ))
        request = repository.get_by_id("SOL-PG-CONCURRENCY-001")
        yield engine, repository, request
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with admin.begin() as conn:
                conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


def apply_decision(engine, request, decision_id, *, alternative=False):
    action = HumanReviewAction(
        id_solicitud=request.id_solicitud,
        action="propose_alternative" if alternative else "confirm",
        actor="dra_test",
        confirmed_date=None if alternative else "2026-10-08",
        confirmed_franja=None if alternative else "tarde",
        alternative_date="2026-10-08" if alternative else None,
        alternative_franja="tarde" if alternative else None,
    )
    return HumanReviewDecisionProcessor(engine=engine).apply(
        action=action,
        decision_id=decision_id,
        expected_updated_at=request.updated_at,
    )


def audit_count(engine):
    with engine.begin() as conn:
        return conn.execute(
            text("SELECT COUNT(*) FROM human_review_decisions")
        ).scalar_one()


def test_concurrent_replay_applies_one_decision(pg_context):
    engine, repository, request = pg_context
    decision_id = str(uuid4())
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait(timeout=3)
        return apply_decision(engine, request, decision_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]

    assert all(result["result"]["success"] for result in results)
    assert {result["replayed"] for result in results} == {False, True}
    assert results[0]["processed_at"] == results[1]["processed_at"]
    assert audit_count(engine) == 1
    assert repository.get_by_id(request.id_solicitud).estado_solicitud == "confirmada"


def test_concurrent_decisions_reject_the_stale_version(pg_context):
    engine, repository, request = pg_context
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait(timeout=3)
        return apply_decision(engine, request, str(uuid4()))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]

    assert sum(result["result"]["success"] for result in results) == 1
    assert {result["result"]["error_code"] for result in results} == {
        None, "stale_request",
    }
    assert audit_count(engine) == 2
    assert repository.get_by_id(request.id_solicitud).estado_solicitud == "confirmada"


def test_projection_lock_coordinates_with_decision_processing(pg_context):
    engine, repository, request = pg_context
    previous_id = str(uuid4())
    previous = apply_decision(engine, request, previous_id, alternative=True)
    assert previous["result"]["success"]
    current = repository.get_by_id(request.id_solicitud)

    entered = threading.Event()
    release = threading.Event()
    attempted_lock = threading.Event()
    local = threading.local()
    projected_rows = []

    class HoldingWriter:
        enabled = True

        def project_decision(self, request, outcome):
            projected_rows.append((
                request.estado_solicitud,
                outcome["decision_id"],
            ))
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError("Test projection was not released.")
            return "updated"

    def observe_lock(conn, cursor, statement, parameters, context, executemany):
        if getattr(local, "decision", False) and "FOR UPDATE" in statement.upper():
            attempted_lock.set()

    next_id = str(uuid4())

    def waiting_decision():
        local.decision = True
        return apply_decision(engine, current, next_id)

    projector = HumanReviewSheetProjector(engine=engine, writer=HoldingWriter())
    event.listen(engine, "before_cursor_execute", observe_lock)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                projection = pool.submit(projector.project_request, request.id_solicitud)
                assert entered.wait(timeout=3)
                decision = pool.submit(waiting_decision)
                assert attempted_lock.wait(timeout=3)
                with pytest.raises(TimeoutError):
                    decision.result(timeout=0.1)
            finally:
                release.set()

            assert projection.result(timeout=10) == "updated"
            assert decision.result(timeout=10)["result"]["success"]
    finally:
        event.remove(engine, "before_cursor_execute", observe_lock)

    assert projected_rows[0] == ("pendiente_confirmacion", previous_id)
    assert projector.project_request(request.id_solicitud) == "updated"
    assert projected_rows[-1] == ("confirmada", next_id)
    assert audit_count(engine) == 2
