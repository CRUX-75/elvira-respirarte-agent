"""Controlled batch reactivation contracts for P6-F.13.

This module performs no persistence, campaign activation or WhatsApp send.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.models.reactivation_campaign import ReactivationExclusionReason
from app.services.reactivation_dry_run import ReactivationDryRunDecision
from app.services.reactivation_manual_trigger import (
    ManualReactivationPersistenceResult,
    ManualReactivationPreflightResult,
    ManualReactivationSelection,
    persist_manual_reactivation_selection,
    select_manual_reactivation_items,
)


MAX_REACTIVATION_BATCH_CONTACTS = 10


@dataclass(frozen=True)
class ReactivationBatchPreflightResult:
    requested: int
    eligible: int
    excluded: int
    already_processed: int
    estimated_sends: int
    source_references: tuple[str, ...]
    prepared_items: tuple[
        tuple[ReactivationSheetRecord, ReactivationDryRunDecision],
        ...,
    ]


@dataclass(frozen=True)
class ReactivationBatchAuthorization:
    campaign_id: str
    source_references: tuple[str, ...]
    prepared_items: tuple[
        tuple[ReactivationSheetRecord, ReactivationDryRunDecision],
        ...,
    ]
    authorization_token: str


def build_reactivation_batch_preflight(
    *,
    preflight: ManualReactivationPreflightResult,
    source_references: Iterable[str],
) -> ReactivationBatchPreflightResult:
    """Build a side-effect-free summary for one explicit batch."""

    selection = select_manual_reactivation_items(
        preflight=preflight,
        source_references=source_references,
        max_contacts=MAX_REACTIVATION_BATCH_CONTACTS,
    )

    already_processed = sum(
        ReactivationExclusionReason.ALREADY_PROCESSED
        in decision.exclusion_reasons
        for _, decision in selection.prepared_items
    )

    return ReactivationBatchPreflightResult(
        requested=len(selection.source_references),
        eligible=selection.eligible,
        excluded=selection.excluded,
        already_processed=already_processed,
        estimated_sends=selection.eligible,
        source_references=selection.source_references,
        prepared_items=selection.prepared_items,
    )


def _normalize_batch_identity(
    *,
    campaign_id: str,
    source_references: Iterable[str],
) -> tuple[str, tuple[str, ...]]:
    normalized_campaign_id = str(campaign_id or "").strip()
    normalized_references = tuple(
        str(value or "").strip()
        for value in source_references
    )

    if not normalized_campaign_id:
        raise ValueError("campaign_id is required")

    if not 1 <= len(normalized_references) <= MAX_REACTIVATION_BATCH_CONTACTS:
        raise ValueError("Batch requires between 1 and 10 contacts")

    if any(not value for value in normalized_references):
        raise ValueError("Batch source references must be non-empty")

    if len(set(normalized_references)) != len(normalized_references):
        raise ValueError("Batch source references must be unique")

    return normalized_campaign_id, normalized_references


def build_reactivation_batch_authorization_token(
    *,
    campaign_id: str,
    source_references: Iterable[str],
) -> str:
    """Bind operator authorization to one campaign and exact selection."""

    normalized_campaign_id, normalized_references = (
        _normalize_batch_identity(
            campaign_id=campaign_id,
            source_references=source_references,
        )
    )

    material = "\n".join(
        (normalized_campaign_id, *normalized_references)
    )
    digest = hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()[:16]

    return (
        f"AUTHORIZE_BATCH:{normalized_campaign_id}:{digest}"
    )


def authorize_reactivation_batch(
    *,
    campaign_id: str,
    preflight: ReactivationBatchPreflightResult,
    authorization_token: str,
) -> ReactivationBatchAuthorization:
    """Authorize only a fully eligible, unchanged preflight selection."""

    normalized_campaign_id, normalized_references = (
        _normalize_batch_identity(
            campaign_id=campaign_id,
            source_references=preflight.source_references,
        )
    )

    requested = len(normalized_references)

    if (
        preflight.requested != requested
        or preflight.eligible != requested
        or preflight.excluded != 0
        or preflight.already_processed != 0
        or preflight.estimated_sends != requested
        or len(preflight.prepared_items) != requested
    ):
        raise ValueError(
            "Batch preflight is not eligible for authorization"
        )

    expected_token = build_reactivation_batch_authorization_token(
        campaign_id=normalized_campaign_id,
        source_references=normalized_references,
    )

    supplied_token = str(
        authorization_token or ""
    ).strip()

    if not hmac.compare_digest(
        supplied_token,
        expected_token,
    ):
        raise ValueError("Batch authorization token is invalid")

    return ReactivationBatchAuthorization(
        campaign_id=normalized_campaign_id,
        source_references=normalized_references,
        prepared_items=preflight.prepared_items,
        authorization_token=expected_token,
    )


from app.services.reactivation_real_pilot import (
    preflight_reactivation_real_pilot,
)
from app.services.reactivation_template_runtime import (
    ReactivationTemplateBatchResult,
    dispatch_reactivation_contacts_best_effort,
)


async def run_reactivation_batch(
    *,
    authorization: ReactivationBatchAuthorization,
    contact_ids: Iterable[str],
    campaign_repository: Any,
    contact_repository: Any,
    dispatcher: Any,
    send_authorized: bool = False,
) -> ReactivationTemplateBatchResult:
    """Dispatch one explicitly authorized batch of up to ten contacts."""

    campaign_id = str(
        authorization.campaign_id or ""
    ).strip()
    authorized_references = tuple(
        str(value or "").strip()
        for value in authorization.source_references
    )

    contacts = preflight_reactivation_real_pilot(
        campaign_id=campaign_id,
        contact_ids=contact_ids,
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
        max_contacts=MAX_REACTIVATION_BATCH_CONTACTS,
    )

    persisted_references = tuple(
        str(
            getattr(contact, "source_reference", "")
            or ""
        ).strip()
        for contact in contacts
    )

    if persisted_references != authorized_references:
        raise ValueError(
            "Persisted contacts do not match batch authorization"
        )

    if send_authorized is not True:
        raise ValueError(
            "Batch requires explicit send authorization"
        )

    validated_contact_ids = tuple(
        str(contact.id).strip()
        for contact in contacts
    )

    return await dispatch_reactivation_contacts_best_effort(
        contact_ids=validated_contact_ids,
        dispatcher=dispatcher,
    )



def persist_authorized_reactivation_batch(
    *,
    campaign_name: str,
    authorization: ReactivationBatchAuthorization,
    campaign_repository: Any,
    contact_repository: Any,
) -> ManualReactivationPersistenceResult:
    """Persist an authorized selection through the existing manual contract."""

    selected_count = len(authorization.prepared_items)

    selection = ManualReactivationSelection(
        source_references=authorization.source_references,
        eligible=selected_count,
        excluded=0,
        prepared_items=authorization.prepared_items,
    )

    return persist_manual_reactivation_selection(
        campaign_id=authorization.campaign_id,
        campaign_name=campaign_name,
        selection=selection,
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
    )
