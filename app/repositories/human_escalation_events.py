from __future__ import annotations

import json
from datetime import datetime
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
    template_parameters,
    status,
    attempt_count,
    retryable,
    provider_message_id,
    last_error_category,
    claim_token,
    claim_expires_at,
    created_at,
    last_attempt_at,
    accepted_at,
    sent_at,
    delivered_at,
    read_at
"""


def _event_from_row(row: Any | None) -> HumanEscalationEvent | None:
    if row is None:
        return None

    return HumanEscalationEvent(**dict(row))


class HumanEscalationEventRepository:
    """PostgreSQL repository for idempotent escalation delivery."""

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
                template_parameters,
                status,
                attempt_count,
                retryable,
                provider_message_id,
                last_error_category,
                claim_token,
                claim_expires_at,
                created_at,
                last_attempt_at,
                accepted_at,
                sent_at,
                delivered_at,
                read_at
            )
            VALUES (
                :id,
                :idempotency_key,
                :patient_id,
                :inbound_whatsapp_message_id,
                :escalation_action,
                :reason_code,
                :notification_text,
                CAST(:template_parameters AS JSONB),
                :status,
                :attempt_count,
                :retryable,
                :provider_message_id,
                :last_error_category,
                :claim_token,
                :claim_expires_at,
                :created_at,
                :last_attempt_at,
                :accepted_at,
                :sent_at,
                :delivered_at,
                :read_at
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
        params["template_parameters"] = json.dumps(
            event.template_parameters,
            ensure_ascii=False,
        )

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

    def get_by_provider_message_id(
        self,
        provider_message_id: str,
    ) -> HumanEscalationEvent | None:
        statement = text(
            f"""
            SELECT {_EVENT_COLUMNS}
            FROM human_escalation_events
            WHERE provider_message_id = :provider_message_id
            LIMIT 1
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {"provider_message_id": provider_message_id},
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
              AND status <> 'accepted'
              AND status <> 'sent'
              AND status <> 'delivered'
              AND status <> 'read'
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

    def mark_accepted(
        self,
        *,
        event_id: str,
        claim_token: str,
        provider_message_id: str,
    ) -> HumanEscalationEvent | None:
        statement = text(
            f"""
            UPDATE human_escalation_events
            SET
                status = 'accepted',
                retryable = FALSE,
                provider_message_id = :provider_message_id,
                last_error_category = NULL,
                accepted_at = NOW(),
                claim_token = NULL,
                claim_expires_at = NULL
            WHERE id = :event_id
              AND claim_token = :claim_token
              AND status <> 'accepted'
              AND status <> 'sent'
              AND status <> 'delivered'
              AND status <> 'read'
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

    def mark_sent(
        self,
        *,
        event_id: str,
        claim_token: str,
        provider_message_id: str | None,
    ) -> HumanEscalationEvent | None:
        """Compatibility method retained for pre-P6-F.10.5 tests/tools."""
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
              AND status <> 'accepted'
              AND status <> 'sent'
              AND status <> 'delivered'
              AND status <> 'read'
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

    def apply_provider_status(
        self,
        *,
        provider_message_id: str,
        provider_status: str,
        occurred_at: datetime | None,
        error_category: str | None = None,
    ) -> HumanEscalationEvent | None:
        allowed = {"sent", "delivered", "read", "failed"}

        if provider_status not in allowed:
            raise ValueError("Unsupported WhatsApp provider status.")

        if provider_status == "sent":
            set_clause = """
                status = 'sent',
                sent_at = COALESCE(sent_at, :occurred_at, NOW()),
                retryable = FALSE,
                last_error_category = NULL
            """
            allowed_current = "('accepted', 'sent')"
        elif provider_status == "delivered":
            set_clause = """
                status = 'delivered',
                delivered_at = COALESCE(delivered_at, :occurred_at, NOW()),
                retryable = FALSE,
                last_error_category = NULL
            """
            allowed_current = "('accepted', 'sent', 'delivered')"
        elif provider_status == "read":
            set_clause = """
                status = 'read',
                read_at = COALESCE(read_at, :occurred_at, NOW()),
                retryable = FALSE,
                last_error_category = NULL
            """
            allowed_current = "('accepted', 'sent', 'delivered', 'read')"
        else:
            set_clause = """
                status = 'failed',
                retryable = FALSE,
                last_error_category = COALESCE(
                    :error_category,
                    'provider_status_failed'
                )
            """
            allowed_current = "('accepted', 'sent', 'failed')"

        statement = text(
            f"""
            UPDATE human_escalation_events
            SET {set_clause}
            WHERE provider_message_id = :provider_message_id
              AND status IN {allowed_current}
            RETURNING {_EVENT_COLUMNS}
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "provider_message_id": provider_message_id,
                        "occurred_at": occurred_at,
                        "error_category": error_category,
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
            WHERE status <> 'accepted'
              AND status <> 'sent'
              AND status <> 'delivered'
              AND status <> 'read'
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
