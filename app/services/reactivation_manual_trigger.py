"""Pure preparation helpers for P6-F.12 manual reactivation trigger.

This module does not access PostgreSQL, Google Sheets, Meta or WhatsApp.
It only converts one already-evaluated eligible staging record into the
existing persistent reactivation contact contract.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationCampaign,
    ReactivationCampaignContact,
    ReactivationCampaignStatus,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
)
from app.services.reactivation_domain import (
    build_reactivation_idempotency_key,
    validate_campaign_transition,
)
from app.services.reactivation_template_dispatcher import (
    DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
    DEFAULT_REACTIVATION_TEMPLATE_NAME,
)
from app.services.reactivation_dry_run import (
    ReactivationDryRunDecision,
    ReactivationDryRunInputError,
    evaluate_reactivation_sheet_record,
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



@dataclass(frozen=True)
class ManualReactivationPreflightResult:
    """Read-only preflight summary for the manual trigger."""

    total: int
    eligible: int
    excluded: int
    invalid_input: int
    runtime_error: int
    prepared_items: tuple[
        tuple[ReactivationSheetRecord, ReactivationDryRunDecision],
        ...,
    ]


def preflight_manual_reactivation(
    *,
    adapter,
    context_resolver,
    default_country_code: str | None,
) -> ManualReactivationPreflightResult:
    """
    Read and evaluate Reactivacion_Historica without persistence or sending.

    Row failures are isolated. Only successfully evaluated rows are returned
    in prepared_items for a later explicit persistence step.
    """

    records = adapter.read_records()

    prepared_items: list[
        tuple[ReactivationSheetRecord, ReactivationDryRunDecision]
    ] = []

    invalid_input = 0
    runtime_error = 0

    for record in records:
        try:
            context = context_resolver(record)
        except Exception:
            runtime_error += 1
            continue

        try:
            decision = evaluate_reactivation_sheet_record(
                record,
                context=context,
                default_country_code=default_country_code,
            )
        except ReactivationDryRunInputError:
            invalid_input += 1
            continue
        except Exception:
            runtime_error += 1
            continue

        prepared_items.append((record, decision))

    prepared = tuple(prepared_items)

    return ManualReactivationPreflightResult(
        total=len(records),
        eligible=sum(
            decision.status == ReactivationContactStatus.ELIGIBLE
            for _, decision in prepared
        ),
        excluded=sum(
            decision.status == ReactivationContactStatus.EXCLUDED
            for _, decision in prepared
        ),
        invalid_input=invalid_input,
        runtime_error=runtime_error,
        prepared_items=prepared,
    )



@dataclass(frozen=True)
class ManualReactivationSelection:
    """Explicit operator-selected subset of a manual preflight."""

    source_references: tuple[str, ...]
    eligible: int
    excluded: int
    prepared_items: tuple[
        tuple[ReactivationSheetRecord, ReactivationDryRunDecision],
        ...,
    ]


def select_manual_reactivation_items(
    *,
    preflight: ManualReactivationPreflightResult,
    source_references: Iterable[str],
    max_contacts: int = 3,
) -> ManualReactivationSelection:
    """
    Select only explicitly named staging rows.

    No eligible row is selected implicitly. Invalid, failed or ambiguous
    source references are refused rather than inferred.
    """

    selected_refs = tuple(
        str(value or "").strip()
        for value in source_references
    )

    if not 1 <= len(selected_refs) <= max_contacts:
        raise ValueError(
            f"Manual selection requires between 1 and {max_contacts} "
            "explicit source references"
        )

    if any(not value for value in selected_refs):
        raise ValueError(
            "Manual source references must be explicit and non-empty"
        )

    if len(set(selected_refs)) != len(selected_refs):
        raise ValueError(
            "Manual source references must be unique"
        )

    by_source = {}
    ambiguous_sources = set()

    for item in preflight.prepared_items:
        record, _ = item
        source_reference = str(
            record.source_reference or ""
        ).strip()

        if source_reference in by_source:
            ambiguous_sources.add(source_reference)
            continue

        by_source[source_reference] = item

    selected_items = []

    for source_reference in selected_refs:
        if source_reference in ambiguous_sources:
            raise ValueError(
                "Selected source reference is ambiguous in staging"
            )

        item = by_source.get(source_reference)

        if item is None:
            raise ValueError(
                "Selected source reference was not successfully "
                "evaluated in preflight"
            )

        selected_items.append(item)

    prepared = tuple(selected_items)

    return ManualReactivationSelection(
        source_references=selected_refs,
        eligible=sum(
            decision.status == ReactivationContactStatus.ELIGIBLE
            for _, decision in prepared
        ),
        excluded=sum(
            decision.status == ReactivationContactStatus.EXCLUDED
            for _, decision in prepared
        ),
        prepared_items=prepared,
    )



@dataclass(frozen=True)
class ManualReactivationPersistenceResult:
    """Persisted draft campaign and its explicitly selected contacts."""

    campaign: ReactivationCampaign
    contacts: tuple[ReactivationCampaignContact, ...]


def persist_manual_reactivation_selection(
    *,
    campaign_id: str,
    campaign_name: str,
    selection: ManualReactivationSelection,
    campaign_repository,
    contact_repository,
) -> ManualReactivationPersistenceResult:
    """
    Persist one explicit eligible selection into a draft campaign.

    This function does not activate campaigns and does not dispatch
    WhatsApp messages.
    """

    normalized_campaign_id = str(campaign_id or "").strip()
    normalized_campaign_name = str(campaign_name or "").strip()

    if not normalized_campaign_id:
        raise ValueError("campaign_id is required")

    if not normalized_campaign_name:
        raise ValueError("campaign_name is required")

    selected_count = len(selection.prepared_items)

    if selected_count == 0:
        raise ValueError(
            "Manual reactivation persistence requires an explicit selection"
        )

    if (
        selection.excluded != 0
        or selection.eligible != selected_count
    ):
        raise ValueError(
            "All manually selected contacts must be eligible"
        )

    campaign = ReactivationCampaign(
        id=normalized_campaign_id,
        name=normalized_campaign_name,
        template_name=DEFAULT_REACTIVATION_TEMPLATE_NAME,
        template_language=DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
        status=ReactivationCampaignStatus.DRAFT,
    )

    persisted_campaign = campaign_repository.create_or_get(
        campaign
    )

    if persisted_campaign.id != normalized_campaign_id:
        raise ValueError(
            "Persisted reactivation campaign ID does not match request"
        )

    if persisted_campaign.name != normalized_campaign_name:
        raise ValueError(
            "Existing reactivation campaign name does not match request"
        )

    if (
        persisted_campaign.template_name
        != DEFAULT_REACTIVATION_TEMPLATE_NAME
        or persisted_campaign.template_language
        != DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE
    ):
        raise ValueError(
            "Existing reactivation campaign template contract is invalid"
        )

    if (
        persisted_campaign.status
        != ReactivationCampaignStatus.DRAFT
    ):
        raise ValueError(
            "Contacts may be prepared only while campaign is draft"
        )

    persisted_contacts = persist_manual_reactivation_contacts(
        campaign_id=normalized_campaign_id,
        prepared_items=selection.prepared_items,
        contact_repository=contact_repository,
    )

    if len(persisted_contacts) != selected_count:
        raise RuntimeError(
            "Not all manually selected contacts were persisted"
        )

    return ManualReactivationPersistenceResult(
        campaign=persisted_campaign,
        contacts=persisted_contacts,
    )



def activate_manual_reactivation_campaign(
    *,
    campaign_id: str,
    campaign_repository,
) -> ReactivationCampaign:
    """
    Move one explicitly prepared manual campaign to ACTIVE.

    DRAFT campaigns advance through READY first. ACTIVE is idempotent.
    Other lifecycle states are refused.
    """

    normalized_campaign_id = str(campaign_id or "").strip()

    if not normalized_campaign_id:
        raise ValueError("campaign_id is required")

    campaign = campaign_repository.get_by_id(
        normalized_campaign_id
    )

    if campaign is None:
        raise ValueError(
            "Manual reactivation campaign was not found"
        )

    if campaign.status == ReactivationCampaignStatus.ACTIVE:
        return campaign

    if campaign.status == ReactivationCampaignStatus.DRAFT:
        validate_campaign_transition(
            ReactivationCampaignStatus.DRAFT,
            ReactivationCampaignStatus.READY,
        )

        campaign = campaign_repository.transition_status(
            campaign_id=normalized_campaign_id,
            expected_status=ReactivationCampaignStatus.DRAFT,
            next_status=ReactivationCampaignStatus.READY,
        )

    if campaign.status == ReactivationCampaignStatus.READY:
        validate_campaign_transition(
            ReactivationCampaignStatus.READY,
            ReactivationCampaignStatus.ACTIVE,
        )

        campaign = campaign_repository.transition_status(
            campaign_id=normalized_campaign_id,
            expected_status=ReactivationCampaignStatus.READY,
            next_status=ReactivationCampaignStatus.ACTIVE,
        )

        return campaign

    raise ValueError(
        "Manual reactivation campaign cannot be activated "
        f"from status={campaign.status.value}"
    )
