"""
Read-only safety-context resolver for P6-F.11.6 dry runs.

The resolver combines:

- canonical phone normalization;
- duplicate detection inside the current dry-run batch;
- injected read-only patient lookup for global opt-out;
- injected campaign-contact lookup for campaign idempotency;
- existing commercial-send commitment rules.

It performs no writes and owns no database connection.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.services.reactivation_domain import (
    has_committed_commercial_send,
    normalize_reactivation_phone_e164,
)
from app.services.reactivation_dry_run import ReactivationDryRunContext


PatientLookup = Callable[[str], Any | None]
CampaignContactLookup = Callable[[str, str], Any | None]


def _field(value: Any, name: str, default: Any = None) -> Any:
    if value is None:
        return default

    if isinstance(value, dict):
        return value.get(name, default)

    return getattr(value, name, default)


class ReactivationDryRunContextResolver:
    """
    Resolve external safety facts without side effects.

    Lookups are injected so this class can be tested without PostgreSQL and
    later wired only to explicitly read-only repository operations.
    """

    def __init__(
        self,
        *,
        campaign_id: str,
        default_country_code: str | None,
        patient_lookup: PatientLookup,
        campaign_contact_lookup: CampaignContactLookup,
    ) -> None:
        normalized_campaign_id = campaign_id.strip()

        if not normalized_campaign_id:
            raise ValueError("campaign_id is required")

        self.campaign_id = normalized_campaign_id
        self.default_country_code = default_country_code
        self.patient_lookup = patient_lookup
        self.campaign_contact_lookup = campaign_contact_lookup

        self._seen_sources_by_phone: dict[str, str] = {}

    def __call__(
        self,
        record: ReactivationSheetRecord,
    ) -> ReactivationDryRunContext:
        phone_e164 = normalize_reactivation_phone_e164(
            record.phone_original,
            default_country_code=self.default_country_code,
        )

        if not phone_e164:
            return ReactivationDryRunContext()

        source_reference = record.source_reference.strip()

        seen_source = self._seen_sources_by_phone.get(phone_e164)
        duplicate_in_batch = (
            seen_source is not None
            and seen_source != source_reference
        )

        if seen_source is None:
            self._seen_sources_by_phone[phone_e164] = source_reference

        patient = self.patient_lookup(phone_e164)
        existing_contact = self.campaign_contact_lookup(
            campaign_id=self.campaign_id,
            phone_e164=phone_e164,
        )

        patient_opt_out = bool(
            _field(
                patient,
                "opt_out",
                False,
            )
        )

        duplicate_existing_contact = False
        already_processed = False

        if existing_contact is not None:
            existing_source_reference = str(
                _field(
                    existing_contact,
                    "source_reference",
                    "",
                )
                or ""
            ).strip()

            duplicate_existing_contact = (
                existing_source_reference != source_reference
            )

            existing_status = _field(
                existing_contact,
                "status",
            )
            existing_status_value = getattr(
                existing_status,
                "value",
                existing_status,
            )
            existing_retryable = bool(
                _field(
                    existing_contact,
                    "retryable",
                    False,
                )
            )

            already_processed = has_committed_commercial_send(
                status=existing_status,
                provider_message_id=_field(
                    existing_contact,
                    "provider_message_id",
                ),
            )

            if (
                existing_status_value in {"pending", "opted_out"}
                or (
                    existing_status_value == "failed"
                    and not existing_retryable
                )
            ):
                already_processed = True

        return ReactivationDryRunContext(
            duplicate_in_campaign=(
                duplicate_in_batch
                or duplicate_existing_contact
            ),
            patient_opt_out=patient_opt_out,
            prior_complaint=False,
            sensitive_case=False,
            representative_number=False,
            representative_confirmed=False,
            already_processed=already_processed,
        )
