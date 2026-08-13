"""
Pure preparation for a minimal historical reactivation pilot.

This module accepts only an explicit batch of 1-3 candidates, validates
the campaign/template gates and delegates per-contact eligibility to the
existing dry-run evaluator.

It performs no persistence, delivery, campaign activation or automatic
contact selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.models.reactivation_campaign import ReactivationCampaignStatus
from app.services.reactivation_dry_run import (
    ReactivationDryRunContext,
    ReactivationDryRunDecision,
    evaluate_reactivation_sheet_record,
)


_APPROVED_TEMPLATE_NAME = "reactivacion_respirarte"
_APPROVED_TEMPLATE_LANGUAGE = "es_CO"


@dataclass(frozen=True)
class ReactivationPilotCandidate:
    record: Any
    context: ReactivationDryRunContext


def prepare_reactivation_pilot_batch(
    *,
    campaign: Any,
    candidates: Iterable[ReactivationPilotCandidate],
    default_country_code: str | None,
) -> tuple[ReactivationDryRunDecision, ...]:
    """
    Prepare one explicitly supplied minimal pilot batch without side effects.
    """

    explicit_candidates = tuple(candidates)

    if not 1 <= len(explicit_candidates) <= 3:
        raise ValueError(
            "Pilot preparation requires between 1 and 3 explicit contacts."
        )

    try:
        campaign_status = ReactivationCampaignStatus(campaign.status)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Reactivation campaign status is invalid.") from exc

    if campaign_status != ReactivationCampaignStatus.ACTIVE:
        raise ValueError("Reactivation campaign must be active.")

    template_name = str(
        getattr(campaign, "template_name", "") or ""
    ).strip()
    template_language = str(
        getattr(campaign, "template_language", "") or ""
    ).strip()

    if (
        template_name != _APPROVED_TEMPLATE_NAME
        or template_language != _APPROVED_TEMPLATE_LANGUAGE
    ):
        raise ValueError(
            "The approved reactivation template contract "
            "requires reactivacion_respirarte with es_CO."
        )

    return tuple(
        evaluate_reactivation_sheet_record(
            candidate.record,
            context=candidate.context,
            default_country_code=default_country_code,
        )
        for candidate in explicit_candidates
    )
