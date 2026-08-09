"""Safe dependency composition for P6-F.11.6 dry runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.adapters.google_sheets_client import (
    GoogleSheetsApiClient,
    build_google_sheets_service,
)
from app.adapters.google_sheets_reactivation import (
    GoogleSheetsReactivationAdapter,
)
from app.config import Settings
from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
)
from app.services.reactivation_dry_run_context import (
    ReactivationDryRunContextResolver,
)


@dataclass(frozen=True)
class ReactivationDryRunDependencies:
    adapter: GoogleSheetsReactivationAdapter
    context_resolver: ReactivationDryRunContextResolver
    default_country_code: str | None


def build_reactivation_dry_run_dependencies(
    *,
    settings: Settings,
    campaign_id: str,
    default_country_code: str | None,
    engine: Any,
    patient_lookup: Callable[[str], Any | None],
    service_builder: Callable[[str | None], object] = build_google_sheets_service,
) -> ReactivationDryRunDependencies | None:
    """Build dry-run dependencies without performing external I/O."""

    if not settings.reactivation_dry_run_enabled:
        return None

    if not settings.google_service_account_json:
        return None

    if not settings.google_sheets_spreadsheet_id:
        return None

    service = service_builder(settings.google_service_account_json)
    client = GoogleSheetsApiClient(service=service)

    adapter = GoogleSheetsReactivationAdapter(
        client=client,
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        tab_name=settings.google_sheets_reactivation_tab,
        enabled=True,
    )

    contact_repository = ReactivationCampaignContactRepository(engine)

    context_resolver = ReactivationDryRunContextResolver(
        campaign_id=campaign_id,
        default_country_code=default_country_code,
        patient_lookup=patient_lookup,
        campaign_contact_lookup=(
            contact_repository.get_by_campaign_phone_read_only
        ),
    )

    return ReactivationDryRunDependencies(
        adapter=adapter,
        context_resolver=context_resolver,
        default_country_code=default_country_code,
    )
