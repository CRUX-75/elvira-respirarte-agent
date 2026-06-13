"""Factory for the Google Sheets human review writer.

This module is a safe runtime boundary.

It only builds GoogleSheetsHumanReviewWriter when all required Google Sheets
configuration is explicitly present.

It does not write to Google Sheets.
It does not connect to /webhook.
It does not send WhatsApp messages.
It does not own appointment lifecycle rules.
"""

from __future__ import annotations

from collections.abc import Callable

from app.adapters.google_sheets_client import (
    GoogleSheetsApiClient,
    build_google_sheets_service,
)
from app.adapters.google_sheets_human_review_writer import (
    GoogleSheetsHumanReviewWriter,
)
from app.config import Settings


def build_google_sheets_human_review_writer(
    *,
    settings: Settings,
    service_builder: Callable[[str | None], object] = build_google_sheets_service,
) -> GoogleSheetsHumanReviewWriter | None:
    """Build a Google Sheets human review writer when safely configured.

    Returns None unless all required conditions are met:

    - GOOGLE_SHEETS_ENABLED=true
    - GOOGLE_SERVICE_ACCOUNT_JSON exists
    - GOOGLE_SHEETS_SPREADSHEET_ID exists
    """

    if not settings.google_sheets_enabled:
        return None

    if not settings.google_service_account_json:
        return None

    if not settings.google_sheets_spreadsheet_id:
        return None

    service = service_builder(settings.google_service_account_json)
    client = GoogleSheetsApiClient(service=service)

    return GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        tab_name=settings.google_sheets_solicitudes_cita_tab,
        enabled=True,
    )
