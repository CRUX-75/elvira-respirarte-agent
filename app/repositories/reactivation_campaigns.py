from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.models.reactivation_campaign import (
    ReactivationCampaign,
    ReactivationCampaignContact,
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
                "('accepted', 'sent', 'failed')"
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
                "('accepted', 'sent', 'delivered', 'failed')"
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
                "('accepted', 'sent', 'delivered', 'read', "
                "'failed')"
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
