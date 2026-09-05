"""Pure preparation helpers for P6-F.12 manual reactivation trigger.

This module does not access PostgreSQL, Google Sheets, Meta or WhatsApp.
It only converts one already-evaluated eligible staging record into the
existing persistent reactivation contact contract.
"""

from __future__ import annotations

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationCampaignContact,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
)
from app.services.reactivation_domain import (
    build_reactivation_idempotency_key,
)
from app.services.reactivation_dry_run import (
    ReactivationDryRunDecision,
)


def build_manual_reactivation_contact(
    *,
    campaign_id: str,
    record: ReactivationSheetRecord,
    decision: ReactivationDryRunDecision,
) -> ReactivationCampaignContact | None:
    """Build one persistent contact only when the row is eligible."""

    normalized_campaign_id = str(campaign_id or "").strip()

    if not normalized_campaign_id:
        raise ValueError("campaign_id is required")

    if (
        decision.row_number != record.row_number
        or decision.source_reference != record.source_reference
    ):
        raise ValueError(
            "Reactivation decision does not match the staging record"
        )

    if decision.status != ReactivationContactStatus.ELIGIBLE:
        return None

    phone_e164 = str(decision.phone_e164 or "").strip()

    if not phone_e164:
        raise ValueError(
            "Eligible reactivation contact requires phone_e164"
        )

    idempotency_key = build_reactivation_idempotency_key(
        campaign_id=normalized_campaign_id,
        phone_e164=phone_e164,
    )

    digest = idempotency_key.removeprefix("reactivation:")

    return ReactivationCampaignContact(
        id=f"manual-reactivation:{digest}",
        campaign_id=normalized_campaign_id,
        source_reference=record.source_reference.strip(),
        name=record.name.strip() or None,
        phone_original=record.phone_original.strip() or None,
        phone_e164=phone_e164,
        attended=True,
        authorization_status=ReactivationAuthorizationStatus.APPROVED,
        doctor_review_status=ReactivationDoctorReviewStatus.APPROVED,
        status=ReactivationContactStatus.ELIGIBLE,
        exclusion_reasons=(),
        idempotency_key=idempotency_key,
    )


def persist_manual_reactivation_contacts(
    *,
    campaign_id: str,
    prepared_items,
    contact_repository,
) -> tuple[ReactivationCampaignContact, ...]:
    """
    Persist only eligible manually prepared contacts.

    The campaign must already exist. This function does not create or
    activate campaigns and does not dispatch WhatsApp messages.
    """

    normalized_campaign_id = str(campaign_id or "").strip()

    if not normalized_campaign_id:
        raise ValueError("campaign_id is required")

    persisted: list[ReactivationCampaignContact] = []

    for record, decision in prepared_items:
        contact = build_manual_reactivation_contact(
            campaign_id=normalized_campaign_id,
            record=record,
            decision=decision,
        )

        if contact is None:
            continue

        persisted_contact = contact_repository.create_or_get(
            contact
        )

        persisted.append(persisted_contact)

    return tuple(persisted)
