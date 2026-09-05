from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.models.reactivation_campaign import (
    ReactivationCampaign,
    ReactivationCampaignContact,
    ReactivationCampaignResponseEvent,
)


_CAMPAIGN_COLUMNS = """
    id,
    name,
    template_name,
    template_language,
    status,
    created_at,
    updated_at
"""


_CONTACT_COLUMNS = """
    id,
    campaign_id,
    source_reference,
    name,
    phone_original,
    phone_e164,
    attended,
    authorization_status,
    doctor_review_status,
    status,
    exclusion_reasons,
    idempotency_key,
    provider_message_id,
    inbound_whatsapp_message_id,
    response_classification,
    response_safe_reason,
    response_requires_human_escalation,
    responded_at,
    retryable,
    attempt_count,
    last_error_category,
    claim_token,
    claim_expires_at,
    last_attempt_at,
    accepted_at,
    sent_at,
    delivered_at,
    read_at,
    failed_at,
    created_at,
    updated_at
"""


_RESPONSE_EVENT_COLUMNS = """
    id,
    contact_id,
    inbound_whatsapp_message_id,
    response_classification,
    response_safe_reason,
    global_opt_out_requested,
    campaign_opt_out_requested,
    requires_human_escalation,
    received_at,
    created_at
"""


def _campaign_from_row(
    row: Any | None,
) -> ReactivationCampaign | None:
    if row is None:
        return None

    return ReactivationCampaign(**dict(row))


def _contact_from_row(
    row: Any | None,
) -> ReactivationCampaignContact | None:
    if row is None:
        return None

    return ReactivationCampaignContact(**dict(row))



def _response_event_from_row(
    row: Any | None,
) -> ReactivationCampaignResponseEvent | None:
    if row is None:
        return None

    return ReactivationCampaignResponseEvent(**dict(row))


class ReactivationCampaignRepository:
    """PostgreSQL repository for reactivation campaign metadata."""

    def __init__(self, engine: Any):
        self.engine = engine

    def create_or_get(
        self,
        campaign: ReactivationCampaign,
    ) -> ReactivationCampaign:
        insert_statement = text(
            f"""
            INSERT INTO reactivation_campaigns (
                id,
                name,
                template_name,
                template_language,
                status,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :name,
                :template_name,
                :template_language,
                :status,
                COALESCE(:created_at, NOW()),
                COALESCE(:updated_at, NOW())
            )
            ON CONFLICT (id) DO NOTHING
            RETURNING {_CAMPAIGN_COLUMNS}
            """
        )

        select_statement = text(
            f"""
            SELECT {_CAMPAIGN_COLUMNS}
            FROM reactivation_campaigns
            WHERE id = :campaign_id
            LIMIT 1
            """
        )

        params = campaign.model_dump(mode="python")
        params["status"] = campaign.status.value

        with self.engine.begin() as connection:
            inserted = (
                connection.execute(
                    insert_statement,
                    params,
                )
                .mappings()
                .first()
            )

            if inserted is not None:
                persisted = _campaign_from_row(inserted)
                assert persisted is not None
                return persisted

            existing = (
                connection.execute(
                    select_statement,
                    {"campaign_id": campaign.id},
                )
                .mappings()
                .first()
            )

        persisted = _campaign_from_row(existing)

        if persisted is None:
            raise RuntimeError(
                "Reactivation campaign conflict occurred but the "
                "existing campaign could not be loaded."
            )

        return persisted

    def get_by_id(
        self,
        campaign_id: str,
    ) -> ReactivationCampaign | None:
        statement = text(
            f"""
            SELECT {_CAMPAIGN_COLUMNS}
            FROM reactivation_campaigns
            WHERE id = :campaign_id
            LIMIT 1
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {"campaign_id": campaign_id},
                )
                .mappings()
                .first()
            )

        return _campaign_from_row(row)


    def transition_status(
        self,
        *,
        campaign_id: str,
        expected_status: str,
        next_status: str,
    ) -> ReactivationCampaign:
        """
        Atomically move one campaign from the expected state to the next.

        Lifecycle validity is owned by the service/domain layer. This
        repository only performs the compare-and-set persistence step.
        """
        normalized_campaign_id = str(campaign_id or "").strip()
        normalized_expected = getattr(
            expected_status,
            "value",
            expected_status,
        )
        normalized_next = getattr(
            next_status,
            "value",
            next_status,
        )

        normalized_expected = str(normalized_expected or "").strip()
        normalized_next = str(normalized_next or "").strip()

        if not normalized_campaign_id:
            raise ValueError("campaign_id is required")

        if not normalized_expected:
            raise ValueError("expected_status is required")

        if not normalized_next:
            raise ValueError("next_status is required")

        update_statement = text(
            f"""
            UPDATE reactivation_campaigns
            SET
                status = :next_status,
                updated_at = NOW()
            WHERE id = :campaign_id
              AND status = :expected_status
            RETURNING {_CAMPAIGN_COLUMNS}
            """
        )

        select_statement = text(
            f"""
            SELECT {_CAMPAIGN_COLUMNS}
            FROM reactivation_campaigns
            WHERE id = :campaign_id
            LIMIT 1
            """
        )

        params = {
            "campaign_id": normalized_campaign_id,
            "expected_status": normalized_expected,
            "next_status": normalized_next,
        }

        with self.engine.begin() as connection:
            updated = (
                connection.execute(
                    update_statement,
                    params,
                )
                .mappings()
                .first()
            )

            if updated is not None:
                persisted = _campaign_from_row(updated)
                assert persisted is not None
                return persisted

            existing = (
                connection.execute(
                    select_statement,
                    {
                        "campaign_id": normalized_campaign_id,
                    },
                )
                .mappings()
                .first()
            )

        current = _campaign_from_row(existing)

        if current is None:
            raise ValueError(
                "Reactivation campaign was not found"
            )

        raise RuntimeError(
            "Reactivation campaign state changed unexpectedly: "
            f"expected={normalized_expected} "
            f"current={current.status.value}"
        )


class ReactivationCampaignContactRepository:
    """PostgreSQL repository for idempotent campaign delivery."""

    def __init__(self, engine: Any):
        self.engine = engine

    def create_or_get(
        self,
        contact: ReactivationCampaignContact,
    ) -> ReactivationCampaignContact:
        if not contact.phone_e164:
            raise ValueError(
                "phone_e164 is required for persistent contacts."
            )

        if not contact.idempotency_key:
            raise ValueError(
                "idempotency_key is required for persistent contacts."
            )

        insert_statement = text(
            f"""
            INSERT INTO reactivation_campaign_contacts (
                id,
                campaign_id,
                source_reference,
                name,
                phone_original,
                phone_e164,
                attended,
                authorization_status,
                doctor_review_status,
                status,
                exclusion_reasons,
                idempotency_key,
                provider_message_id,
                retryable,
                attempt_count,
                last_error_category,
                claim_token,
                claim_expires_at,
                last_attempt_at,
                accepted_at,
                sent_at,
                delivered_at,
                read_at,
                failed_at,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :campaign_id,
                :source_reference,
                :name,
                :phone_original,
                :phone_e164,
                :attended,
                :authorization_status,
                :doctor_review_status,
                :status,
                CAST(:exclusion_reasons AS JSONB),
                :idempotency_key,
                :provider_message_id,
                :retryable,
                :attempt_count,
                :last_error_category,
                :claim_token,
                :claim_expires_at,
                :last_attempt_at,
                :accepted_at,
                :sent_at,
                :delivered_at,
                :read_at,
                :failed_at,
                COALESCE(:created_at, NOW()),
                COALESCE(:updated_at, NOW())
            )
            ON CONFLICT (
                campaign_id,
                phone_e164
            )
            DO NOTHING
            RETURNING {_CONTACT_COLUMNS}
            """
        )

        select_statement = text(
            f"""
            SELECT {_CONTACT_COLUMNS}
            FROM reactivation_campaign_contacts
            WHERE campaign_id = :campaign_id
              AND phone_e164 = :phone_e164
            LIMIT 1
            """
        )

        params = contact.model_dump(mode="python")
        params["authorization_status"] = (
            contact.authorization_status.value
        )
        params["doctor_review_status"] = (
            contact.doctor_review_status.value
        )
        params["status"] = contact.status.value
        params["exclusion_reasons"] = json.dumps(
            [
                reason.value
                for reason in contact.exclusion_reasons
            ],
            ensure_ascii=False,
        )

        natural_key = {
            "campaign_id": contact.campaign_id,
            "phone_e164": contact.phone_e164,
        }

        with self.engine.begin() as connection:
            inserted = (
                connection.execute(
                    insert_statement,
                    params,
                )
                .mappings()
                .first()
            )

            if inserted is not None:
                persisted = _contact_from_row(inserted)
                assert persisted is not None
                return persisted

            existing = (
                connection.execute(
                    select_statement,
                    natural_key,
                )
                .mappings()
                .first()
            )

        persisted = _contact_from_row(existing)

        if persisted is None:
            raise RuntimeError(
                "Reactivation contact conflict occurred but the "
                "existing contact could not be loaded."
            )

        return persisted

    def get_by_id(
        self,
        contact_id: str,
    ) -> ReactivationCampaignContact | None:
        statement = text(
            f"""
            SELECT {_CONTACT_COLUMNS}
            FROM reactivation_campaign_contacts
            WHERE id = :contact_id
            LIMIT 1
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {"contact_id": contact_id},
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)

    def get_by_campaign_phone_read_only(
        self,
        *,
        campaign_id: str,
        phone_e164: str,
    ) -> ReactivationCampaignContact | None:
        """
        Load one campaign contact by its natural key without writes.

        Intended for dry-run eligibility and idempotency checks.
        """

        campaign_id = str(campaign_id or "").strip()
        phone_e164 = str(phone_e164 or "").strip()

        if not campaign_id:
            raise ValueError("campaign_id is required.")

        if not phone_e164:
            raise ValueError("phone_e164 is required.")

        statement = text(
            f"""
            SELECT {_CONTACT_COLUMNS}
            FROM reactivation_campaign_contacts
            WHERE campaign_id = :campaign_id
              AND phone_e164 = :phone_e164
            LIMIT 1
            """
        )

        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "campaign_id": campaign_id,
                        "phone_e164": phone_e164,
                    },
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)

    def get_by_provider_message_id(
        self,
        provider_message_id: str,
    ) -> ReactivationCampaignContact | None:
        statement = text(
            f"""
            SELECT {_CONTACT_COLUMNS}
            FROM reactivation_campaign_contacts
            WHERE provider_message_id = :provider_message_id
            LIMIT 1
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "provider_message_id": (
                            provider_message_id
                        )
                    },
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)

    def find_latest_response_candidate_by_phone(
        self,
        *,
        phone_e164: str,
    ) -> ReactivationCampaignContact | None:
        phone_e164 = str(phone_e164 or "").strip()

        if not phone_e164:
            raise ValueError("phone_e164 is required.")

        statement = text(
            f"""
            SELECT {_CONTACT_COLUMNS}
            FROM reactivation_campaign_contacts
            WHERE phone_e164 = :phone_e164
              AND provider_message_id IS NOT NULL
              AND status IN (
                    'accepted',
                    'sent',
                    'delivered',
                    'read',
                    'opted_out'
              )
            ORDER BY
                accepted_at DESC NULLS LAST,
                updated_at DESC,
                created_at DESC
            LIMIT 1
            """
        )

        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    statement,
                    {"phone_e164": phone_e164},
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)

    def record_response_event(
        self,
        *,
        contact_id: str,
        inbound_whatsapp_message_id: str,
        response_classification: str,
        response_safe_reason: str | None,
        global_opt_out_requested: bool,
        campaign_opt_out_requested: bool,
        requires_human_escalation: bool,
        received_at: datetime | None,
    ) -> ReactivationCampaignResponseEvent:
        contact_id = str(contact_id or "").strip()
        inbound_whatsapp_message_id = str(
            inbound_whatsapp_message_id or ""
        ).strip()
        response_classification = str(
            response_classification or ""
        ).strip()

        if not contact_id:
            raise ValueError("contact_id is required.")

        if not inbound_whatsapp_message_id:
            raise ValueError(
                "inbound_whatsapp_message_id is required."
            )

        if not response_classification:
            raise ValueError(
                "response_classification is required."
            )

        if response_safe_reason is not None:
            response_safe_reason = (
                str(response_safe_reason).strip() or None
            )

        statement = text(
            f"""
            WITH inserted_event AS (
                INSERT INTO reactivation_campaign_response_events (
                    contact_id,
                    inbound_whatsapp_message_id,
                    response_classification,
                    response_safe_reason,
                    global_opt_out_requested,
                    campaign_opt_out_requested,
                    requires_human_escalation,
                    received_at
                )
                SELECT
                    :contact_id,
                    :inbound_whatsapp_message_id,
                    :response_classification,
                    :response_safe_reason,
                    :global_opt_out_requested,
                    :campaign_opt_out_requested,
                    :requires_human_escalation,
                    COALESCE(:received_at, NOW())
                FROM reactivation_campaign_contacts
                WHERE id = :contact_id
                  AND provider_message_id IS NOT NULL
                  AND status IN (
                        'accepted',
                        'sent',
                        'delivered',
                        'read',
                        'opted_out'
                  )
                ON CONFLICT (inbound_whatsapp_message_id)
                DO NOTHING
                RETURNING {_RESPONSE_EVENT_COLUMNS}
            ),
            updated_contact AS (
                UPDATE reactivation_campaign_contacts
                SET
                    status = CASE
                        WHEN :campaign_opt_out_requested
                        THEN 'opted_out'
                        ELSE status
                    END,
                    inbound_whatsapp_message_id = CASE
                        WHEN responded_at IS NULL OR COALESCE(:received_at, NOW()) >= responded_at
                        THEN :inbound_whatsapp_message_id
                        ELSE inbound_whatsapp_message_id
                    END,
                    response_classification = CASE
                        WHEN responded_at IS NULL OR COALESCE(:received_at, NOW()) >= responded_at
                        THEN :response_classification
                        ELSE response_classification
                    END,
                    response_safe_reason = CASE
                        WHEN responded_at IS NULL OR COALESCE(:received_at, NOW()) >= responded_at
                        THEN :response_safe_reason
                        ELSE response_safe_reason
                    END,
                    response_requires_human_escalation = CASE
                        WHEN responded_at IS NULL OR COALESCE(:received_at, NOW()) >= responded_at
                        THEN :requires_human_escalation
                        ELSE response_requires_human_escalation
                    END,
                    responded_at = CASE
                        WHEN responded_at IS NULL OR COALESCE(:received_at, NOW()) >= responded_at
                        THEN COALESCE(:received_at, NOW())
                        ELSE responded_at
                    END,
                    updated_at = NOW()
                WHERE id = :contact_id
                  AND EXISTS (
                        SELECT 1
                        FROM inserted_event
                  )
                RETURNING id
            )
            SELECT {_RESPONSE_EVENT_COLUMNS}
            FROM inserted_event

            UNION ALL

            SELECT {_RESPONSE_EVENT_COLUMNS}
            FROM reactivation_campaign_response_events
            WHERE inbound_whatsapp_message_id = (
                :inbound_whatsapp_message_id
            )
              AND contact_id = :contact_id
              AND NOT EXISTS (
                    SELECT 1
                    FROM inserted_event
              )
            LIMIT 1
            """
        )

        params = {
            "contact_id": contact_id,
            "inbound_whatsapp_message_id": (
                inbound_whatsapp_message_id
            ),
            "response_classification": response_classification,
            "response_safe_reason": response_safe_reason,
            "global_opt_out_requested": (
                global_opt_out_requested
            ),
            "campaign_opt_out_requested": (
                campaign_opt_out_requested
            ),
            "requires_human_escalation": (
                requires_human_escalation
            ),
            "received_at": received_at,
        }

        with self.engine.begin() as connection:
            row = (
                connection.execute(statement, params)
                .mappings()
                .first()
            )

        event = _response_event_from_row(row)

        if event is None:
            raise RuntimeError(
                "No eligible reactivation contact was found "
                "for the inbound response."
            )

        return event

    def try_claim_delivery(
        self,
        *,
        contact_id: str,
        claim_token: str,
        lease_seconds: int = 120,
    ) -> ReactivationCampaignContact | None:
        if lease_seconds <= 0:
            raise ValueError(
                "lease_seconds must be greater than zero."
            )

        statement = text(
            """
            UPDATE reactivation_campaign_contacts
            SET
                status = 'pending',
                claim_token = :claim_token,
                claim_expires_at = (
                    NOW()
                    + (:lease_seconds * INTERVAL '1 second')
                ),
                last_attempt_at = NOW(),
                attempt_count = attempt_count + 1,
                retryable = FALSE,
                last_error_category = NULL,
                updated_at = NOW()
            WHERE id = :contact_id
              AND provider_message_id IS NULL
              AND (
                    status = 'eligible'
                    OR (
                        status = 'failed'
                        AND retryable = TRUE
                    )
              )
              AND (
                    claim_token IS NULL
                    OR claim_expires_at IS NULL
                    OR claim_expires_at <= NOW()
              )
              AND EXISTS (
                    SELECT 1
                    FROM reactivation_campaigns
                    WHERE reactivation_campaigns.id =
                        reactivation_campaign_contacts.campaign_id
                      AND reactivation_campaigns.status = 'active'
              )
              AND NOT EXISTS (
                    SELECT 1
                    FROM patients
                    WHERE patients.telefono =
                        reactivation_campaign_contacts.phone_e164
                      AND patients.opt_out = TRUE
              )
            RETURNING *
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "contact_id": contact_id,
                        "claim_token": claim_token,
                        "lease_seconds": lease_seconds,
                    },
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)

    def mark_accepted(
        self,
        *,
        contact_id: str,
        claim_token: str,
        provider_message_id: str,
    ) -> ReactivationCampaignContact | None:
        statement = text(
            """
            UPDATE reactivation_campaign_contacts
            SET
                status = 'accepted',
                provider_message_id = :provider_message_id,
                accepted_at = NOW(),
                retryable = FALSE,
                last_error_category = NULL,
                claim_token = NULL,
                claim_expires_at = NULL,
                updated_at = NOW()
            WHERE id = :contact_id
              AND claim_token = :claim_token
              AND status = 'pending'
              AND provider_message_id IS NULL
            RETURNING *
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "contact_id": contact_id,
                        "claim_token": claim_token,
                        "provider_message_id": (
                            provider_message_id
                        ),
                    },
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)

    def mark_failed(
        self,
        *,
        contact_id: str,
        claim_token: str,
        error_category: str,
        retryable: bool,
    ) -> ReactivationCampaignContact | None:
        statement = text(
            """
            UPDATE reactivation_campaign_contacts
            SET
                status = 'failed',
                retryable = :retryable,
                last_error_category = :error_category,
                failed_at = NOW(),
                claim_token = NULL,
                claim_expires_at = NULL,
                updated_at = NOW()
            WHERE id = :contact_id
              AND claim_token = :claim_token
              AND status = 'pending'
              AND provider_message_id IS NULL
            RETURNING *
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "contact_id": contact_id,
                        "claim_token": claim_token,
                        "error_category": error_category,
                        "retryable": retryable,
                    },
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)

    def apply_provider_status(
        self,
        *,
        provider_message_id: str,
        provider_status: str,
        occurred_at: datetime | None,
        error_category: str | None = None,
    ) -> ReactivationCampaignContact | None:
        allowed = {
            "sent",
            "delivered",
            "read",
            "failed",
        }

        if provider_status not in allowed:
            raise ValueError(
                "Unsupported WhatsApp provider status."
            )

        if provider_status == "sent":
            set_clause = """
                status = 'sent',
                sent_at = COALESCE(
                    sent_at,
                    :occurred_at,
                    NOW()
                ),
                retryable = FALSE,
                last_error_category = NULL,
                updated_at = NOW()
            """
            allowed_current = (
                "('accepted', 'sent')"
            )

        elif provider_status == "delivered":
            set_clause = """
                status = 'delivered',
                delivered_at = COALESCE(
                    delivered_at,
                    :occurred_at,
                    NOW()
                ),
                retryable = FALSE,
                last_error_category = NULL,
                updated_at = NOW()
            """
            allowed_current = (
                "('accepted', 'sent', 'delivered')"
            )

        elif provider_status == "read":
            set_clause = """
                status = 'read',
                read_at = COALESCE(
                    read_at,
                    :occurred_at,
                    NOW()
                ),
                retryable = FALSE,
                last_error_category = NULL,
                updated_at = NOW()
            """
            allowed_current = (
                "('accepted', 'sent', 'delivered', 'read')"
            )

        else:
            set_clause = """
                status = 'failed',
                failed_at = COALESCE(
                    failed_at,
                    :occurred_at,
                    NOW()
                ),
                retryable = FALSE,
                last_error_category = COALESCE(
                    :error_category,
                    'provider_status_failed'
                ),
                updated_at = NOW()
            """
            allowed_current = "('accepted', 'sent', 'failed')"

        statement = text(
            f"""
            UPDATE reactivation_campaign_contacts
            SET {set_clause}
            WHERE provider_message_id = :provider_message_id
              AND status IN {allowed_current}
            RETURNING *
            """
        )

        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    statement,
                    {
                        "provider_message_id": (
                            provider_message_id
                        ),
                        "occurred_at": occurred_at,
                        "error_category": error_category,
                    },
                )
                .mappings()
                .first()
            )

        return _contact_from_row(row)
