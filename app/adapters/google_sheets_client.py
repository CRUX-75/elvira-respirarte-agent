"""Google Sheets API client adapter.

This adapter wraps the official Google Sheets API client behind the small
protocol expected by GoogleSheetsHumanReviewWriter.

It does not decide business rules.
It does not send WhatsApp messages.
It does not connect itself to runtime flows.
"""

from __future__ import annotations

import json
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build


GOOGLE_SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsConfigError(ValueError):
    """Raised when Google Sheets client configuration is missing or invalid."""


def _service_account_credentials_from_info(
    info: dict[str, Any],
    scopes: list[str],
):
    return service_account.Credentials.from_service_account_info(
        info,
        scopes=scopes,
    )


def _build_google_service(service_name: str, version: str, credentials):
    return build(service_name, version, credentials=credentials)


def build_google_sheets_service(service_account_json: str | None):
    """Build an authenticated Google Sheets API service from service account JSON."""

    if not service_account_json:
        raise GoogleSheetsConfigError("GOOGLE_SERVICE_ACCOUNT_JSON is required")

    try:
        service_account_info = json.loads(service_account_json)
    except json.JSONDecodeError as exc:
        raise GoogleSheetsConfigError("Invalid GOOGLE_SERVICE_ACCOUNT_JSON") from exc

    try:
        credentials = _service_account_credentials_from_info(
            service_account_info,
            GOOGLE_SHEETS_SCOPES,
        )
        return _build_google_service("sheets", "v4", credentials)
    except Exception as exc:
        raise GoogleSheetsConfigError("Could not build Google Sheets service") from exc


class GoogleSheetsApiClient:
    """Minimal Google Sheets API client used by the human review writer."""

    def __init__(self, *, service) -> None:
        self.service = service

    def get_values(self, spreadsheet_id: str, range_name: str) -> list[list[str]]:
        result = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            )
            .execute()
        )
        return result.get("values", [])

    def append_row(
        self,
        spreadsheet_id: str,
        range_name: str,
        row: list[str],
    ) -> None:
        (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": [row]},
            )
            .execute()
        )

    def update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[str]],
    ) -> None:
        """Update one exact Sheets range without expanding to a full row."""

        (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": values},
            )
            .execute()
        )

    def update_row(
        self,
        spreadsheet_id: str,
        range_name: str,
        row_number: int,
        row: list[str],
    ) -> None:
        update_range = self._row_range(range_name=range_name, row_number=row_number)

        (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=update_range,
                valueInputOption="USER_ENTERED",
                body={"values": [row]},
            )
            .execute()
        )

    def _row_range(self, *, range_name: str, row_number: int) -> str:
        if "!" not in range_name:
            return range_name

        tab_name, column_range = range_name.split("!", 1)

        if ":" not in column_range:
            return f"{tab_name}!{column_range}{row_number}"

        start_column, end_column = column_range.split(":", 1)
        return f"{tab_name}!{start_column}{row_number}:{end_column}{row_number}"
