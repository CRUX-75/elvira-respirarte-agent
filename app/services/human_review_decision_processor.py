"""Apply explicit human decisions with persistent idempotency and audit."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import text

from app.models.human_review import HumanReviewResult
from app.repositories.postgres_appointment_request_repository import (
    PostgresAppointmentRequestRepository,
)
from app.services.human_review_service import HumanReviewService


def _version(value):
    if value is None:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class _DecisionRequestRepository(PostgresAppointmentRequestRepository):
    def update(self, request):
        now = datetime.now(timezone.utc)
        previous = _version(request.updated_at)
        if previous is not None and now <= previous:
            now = previous + timedelta(microseconds=1)
        return super().update(
            request.model_copy(update={"updated_at": now.isoformat()})
        )


class HumanReviewDecisionProcessor:
    def __init__(self, *, engine):
        self.engine = engine

    def apply(self, *, action, decision_id, expected_updated_at):
        decision_id = str(UUID(decision_id))
        if not action.actor.strip() or not action.id_solicitud.strip():
            raise ValueError("invalid_decision_identity")
        expected_version = _version(expected_updated_at)
        if expected_version is None:
            raise ValueError("missing_expected_version")

        command = json.dumps(
            {
                "action": action.model_dump(mode="json"),
                "expected_updated_at": expected_version.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        command_hash = sha256(command.encode()).hexdigest()

        with self.engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                lock_key = int.from_bytes(
                    sha256(decision_id.encode()).digest()[:8],
                    byteorder="big",
                    signed=True,
                )
                conn.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": lock_key},
                )
            elif conn.dialect.name != "sqlite":
                raise ValueError("unsupported_database")

            stored = conn.execute(
                text("""
                    SELECT command_hash, processed_at, result_json
                    FROM human_review_decisions
                    WHERE decision_id = :decision_id
                """),
                {"decision_id": decision_id},
            ).mappings().first()

            if stored is not None:
                if stored["command_hash"] != command_hash:
                    return self._response(
                        decision_id,
                        stored["processed_at"],
                        self._error(action, "idempotency_conflict"),
                        replayed=False,
                    )
                return self._response(
                    decision_id,
                    stored["processed_at"],
                    json.loads(stored["result_json"]),
                    replayed=True,
                )

            repository = _DecisionRequestRepository(
                self.engine, connection=conn,
            )
            if conn.dialect.name == "postgresql":
                conn.execute(
                    text("""
                        SELECT id_solicitud
                        FROM appointment_requests
                        WHERE id_solicitud = :id_solicitud
                        FOR UPDATE
                    """),
                    {"id_solicitud": action.id_solicitud},
                )

            request = repository.get_by_id(action.id_solicitud)
            if request is None:
                result = self._error(action, "request_not_found")
            elif _version(request.updated_at) != expected_version:
                result = self._error(
                    action, "stale_request", request.estado_solicitud,
                )
            else:
                result = HumanReviewService(repository).apply_action(action)
                result = result.model_dump(exclude={"patient_message"})

            processed_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                text("""
                    INSERT INTO human_review_decisions (
                        decision_id, id_solicitud, command_hash,
                        actor, processed_at, result_json
                    )
                    VALUES (
                        :decision_id, :id_solicitud, :command_hash,
                        :actor, :processed_at, :result_json
                    )
                """),
                {
                    "decision_id": decision_id,
                    "id_solicitud": action.id_solicitud,
                    "command_hash": command_hash,
                    "actor": action.actor,
                    "processed_at": processed_at,
                    "result_json": json.dumps(result, sort_keys=True),
                },
            )
            return self._response(
                decision_id, processed_at, result, replayed=False,
            )

    @staticmethod
    def _error(action, code, previous_status=None):
        return HumanReviewResult(
            success=False,
            id_solicitud=action.id_solicitud,
            action=action.action,
            previous_status=previous_status,
            error_code=code,
            message={
                "idempotency_conflict": "Decision ID already used for another command.",
                "request_not_found": "Appointment request was not found.",
                "stale_request": "Request changed; refresh before submitting a new decision.",
            }[code],
        ).model_dump(exclude={"patient_message"})

    @staticmethod
    def _response(decision_id, processed_at, result, *, replayed):
        if hasattr(processed_at, "isoformat"):
            processed_at = processed_at.isoformat()
        return {
            "decision_id": decision_id,
            "processed_at": processed_at,
            "replayed": replayed,
            "result": result,
        }
