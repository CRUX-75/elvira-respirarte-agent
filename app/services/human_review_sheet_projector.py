"""Project current PostgreSQL state and audit without applying decisions."""

import json

from sqlalchemy import text

from app.repositories.postgres_appointment_request_repository import (
    PostgresAppointmentRequestRepository,
)


class HumanReviewSheetProjector:
    def __init__(self, *, engine, writer):
        self.engine = engine
        self.writer = writer

    def upsert_request(self, request):
        return self.project_request(request.id_solicitud)

    def project_request(self, id_solicitud):
        if not self.writer.enabled:
            return "skipped_disabled"

        with self.engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                conn.execute(
                    text("""
                        SELECT id_solicitud
                        FROM appointment_requests
                        WHERE id_solicitud = :id_solicitud
                        FOR UPDATE
                    """),
                    {"id_solicitud": id_solicitud},
                )
            elif conn.dialect.name != "sqlite":
                raise ValueError("unsupported_database")

            repository = PostgresAppointmentRequestRepository(
                self.engine, connection=conn,
            )
            current = repository.get_by_id(id_solicitud)
            if current is None:
                raise ValueError("request_not_found")

            latest = conn.execute(
                text("""
                    SELECT decision_id, actor, processed_at, result_json
                    FROM human_review_decisions
                    WHERE id_solicitud = :id_solicitud
                    ORDER BY processed_at DESC, decision_id DESC
                    LIMIT 1
                """),
                {"id_solicitud": id_solicitud},
            ).mappings().first()

            if latest is None:
                return self.writer.upsert_request(current)

            processed_at = latest["processed_at"]
            if hasattr(processed_at, "isoformat"):
                processed_at = processed_at.isoformat()

            outcome = {
                "decision_id": latest["decision_id"],
                "actor": latest["actor"],
                "processed_at": str(processed_at),
                "replayed": True,
                "result": json.loads(latest["result_json"]),
            }
            return self.writer.project_decision(current, outcome)
