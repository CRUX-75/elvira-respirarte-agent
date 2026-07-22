from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.models.human_escalation_event import HumanEscalationEvent


_EVENT_COLUMNS = """
    id,
    idempotency_key,
    patient_id,
    inbound_whatsapp_message_id,
    escalation_action,
    reason_code,
    notification_text,
    status,
    attempt_count,
    retryable,
    provider_message_id,
    last_error_category,
    claim_token,
    claim_expires_at,
    created_at,
    last_attempt_at,
    sent_at
"""


def _event_from_row(row: Any | None) -> HumanEscalationEvent | None:
    if row is None:
        return None

    return HumanEscalationEvent(**dict(row))


class HumanEscalationEventRepository:
    """
    PostgreSQL repository for idempotent escalation delivery.

    The database engine is injected so repository tests do not need a
    production connection and runtime wiring remains separate.
    """

    def __init__(self, engine: Any):
        self.engine = engine

    def create_or_get(
        self,
        event: HumanEscalationEvent,
    ) -> HumanEscalationEvent:
        insert_statement = text(
            f"""
            INSERT INTO human_escalation_events (
                id,
                idempotency_key,
                patient_id,
                inbound_whatsapp_message_id,
                escalation_action,
                reason_code,
                notification_text,
                status,
                attempt_count,
                retryable,
                provider_message_id,
                last_error_category,
                claim_token,
                claim_expires_at,
                created_at,
                last_attempt_at,
                sent_at
            )
            VALUES (
                :id,
                :idempotency_key,
                :patient_id,
                :inbound_whatsapp_message_id,
                :escalation_action,
                :reason_code,
                :notification_text,
                :status,
                :attempt_count,
                :retryable,
                :provider_message_id,
                :last_error_category,
                :claim_token,
                :claim_expires_at,
                :created_at,
                :last_attempt_at,
                :sent_at
            )
            ON CONFLICT (
                inbound_whatsapp_message_id,
                escalation_action
            )
            DO NOTHING
            RETURNING {_EVENT_COLUMNS}
            """
        )

        select_statement = text(
            f"""
            SELECT {_EVENT_COLUMNS}
            FROM human_escalation_events
            WHERE inbound_whatsapp_message_id =
                :inbound_whatsapp_message_id
              AND escalation_action = :escalation_action
            LIMIT 1
            """
        )

        params = event.model_dump(mode="python")
        params["status"] = event.status.value

        source_params = {
            "inbound_whatsapp_message_id": (
                event.inbound_whatsapp_message_id
            ),
            "escalation_action": event.escalation_action,
        }

        with self.engine.begin() as connection:
            inserted = (
                connection.execute(insert_statement, params)
                .mappings()
                .first()
            )

            if inserted is not None:
                persisted = _event_from_row(inserted)
                assert persisted is not None
                return persisted

            existing = (
                connection.execute(select_statement, source_params)
                .mappings()
                .first()
            )

        persisted = _event_from_row(existing)

        if persisted is None:
            raise RuntimeError(
                "Escalation event conflict occurred but the existing "
                "event could not be loaded."
            )

        return persisted

    def get_by_id(
        self,
        event_id: str,
    ) -> HumanEscalationEvent | None:
        statement = text(
            f"""
            SELECT {_EVENT_COLUMNS}
            FROM human_escalation_events
            WHERE id = :event_id
            LIMIT 1
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {"event_id": event_id},
                )
                .mappings()
                .first()
            )

        return _event_from_row(row)

    def try_claim_delivery(
        self,
        *,
        event_id: str,
        claim_token: str,
        lease_seconds: int = 120,
    ) -> HumanEscalationEvent | None:
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be greater than zero.")

        statement = text(
            f"""
            UPDATE human_escalation_events
            SET
                retryable = FALSE,
                claim_token = :claim_token,
                claim_expires_at = (
                    NOW()
                    + (:lease_seconds * INTERVAL '1 second')
                ),
                attempt_count = attempt_count + 1,
                last_attempt_at = NOW()
            WHERE id = :event_id
              AND status <> 'sent'
              AND retryable = TRUE
              AND (
                    claim_token IS NULL
                    OR claim_expires_at IS NULL
                    OR claim_expires_at <= NOW()
              )
            RETURNING {_EVENT_COLUMNS}
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "event_id": event_id,
                        "claim_token": claim_token,
                        "lease_seconds": lease_seconds,
                    },
                )
                .mappings()
                .first()
            )

        return _event_from_row(row)

    def mark_sent(
        self,
        *,
        event_id: str,
        claim_token: str,
        provider_message_id: str | None,
    ) -> HumanEscalationEvent | None:
        statement = text(
            f"""
            UPDATE human_escalation_events
            SET
                status = 'sent',
                retryable = FALSE,
                provider_message_id = :provider_message_id,
                last_error_category = NULL,
                sent_at = NOW(),
                claim_token = NULL,
                claim_expires_at = NULL
            WHERE id = :event_id
              AND claim_token = :claim_token
              AND status <> 'sent'
            RETURNING {_EVENT_COLUMNS}
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "event_id": event_id,
                        "claim_token": claim_token,
                        "provider_message_id": provider_message_id,
                    },
                )
                .mappings()
                .first()
            )

        return _event_from_row(row)

    def mark_failed(
        self,
        *,
        event_id: str,
        claim_token: str,
        error_category: str,
        retryable: bool,
    ) -> HumanEscalationEvent | None:
        statement = text(
            f"""
            UPDATE human_escalation_events
            SET
                status = 'failed',
                retryable = :retryable,
                last_error_category = :error_category,
                claim_token = NULL,
                claim_expires_at = NULL
            WHERE id = :event_id
              AND claim_token = :claim_token
              AND status <> 'sent'
            RETURNING {_EVENT_COLUMNS}
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "event_id": event_id,
                        "claim_token": claim_token,
                        "error_category": error_category,
                        "retryable": retryable,
                    },
                )
                .mappings()
                .first()
            )

        return _event_from_row(row)

    def list_retryable(
        self,
        *,
        limit: int = 50,
    ) -> list[HumanEscalationEvent]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200.")

        statement = text(
            f"""
            SELECT {_EVENT_COLUMNS}
            FROM human_escalation_events
            WHERE status <> 'sent'
              AND retryable = TRUE
              AND (
                    claim_token IS NULL
                    OR claim_expires_at IS NULL
                    OR claim_expires_at <= NOW()
              )
            ORDER BY created_at ASC
            LIMIT :limit
            """
        )

        with self.engine.begin() as connection:
            rows = (
                connection.execute(
                    statement,
                    {"limit": limit},
                )
                .mappings()
                .all()
            )

        return [
            event
            for event in (_event_from_row(row) for row in rows)
            if event is not None
        ]
