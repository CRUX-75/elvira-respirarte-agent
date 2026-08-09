"""
Google Sheets adapter for the historical patient reactivation staging tab.

This adapter owns only the spreadsheet boundary:

- read the approved ten-column contract;
- preserve the physical sheet row number;
- update only the two system-owned projection columns;
- remain inert when disabled.

It does not normalize phones, evaluate eligibility, persist campaigns,
activate sending or call WhatsApp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


GOOGLE_SHEETS_REACTIVATION_COLUMNS = [
    "source_reference",
    "nombre",
    "telefono_original",
    "atendido",
    "autorizado_contacto",
    "telefono_e164",
    "revision_doctora",
    "motivo_exclusion",
    "estado_reactivacion",
    "observaciones",
]


class ReactivationSheetContractError(ValueError):
    """Raised when Reactivacion_Historica does not match its approved schema."""


class SheetsClient(Protocol):
    """Minimal Google Sheets client surface required by this adapter."""

    def get_values(
        self,
        spreadsheet_id: str,
        range_name: str,
    ) -> list[list[str]]:
        """Return values including the header row."""

    def update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[str]],
    ) -> None:
        """Update one exact Sheets range."""

    def update_row(
        self,
        spreadsheet_id: str,
        range_name: str,
        row_number: int,
        row: list[str],
    ) -> None:
        """Update one 1-based sheet row."""


@dataclass(frozen=True)
class ReactivationSheetRecord:
    """One row read from the Reactivacion_Historica staging tab."""

    row_number: int
    source_reference: str
    name: str
    phone_original: str
    attended: str
    authorization_status: str
    phone_e164: str
    doctor_review_status: str
    exclusion_reason: str
    reactivation_status: str
    observations: str


def _string(value: object) -> str:
    if value is None:
        return ""

    return str(value)


def _row_dict(
    headers: list[str],
    row: list[str],
) -> dict[str, str]:
    return {
        header: _string(row[index]) if index < len(row) else ""
        for index, header in enumerate(headers)
    }


def _record_from_row(
    *,
    row_number: int,
    headers: list[str],
    row: list[str],
) -> ReactivationSheetRecord:
    values = _row_dict(headers, row)

    return ReactivationSheetRecord(
        row_number=row_number,
        source_reference=values["source_reference"],
        name=values["nombre"],
        phone_original=values["telefono_original"],
        attended=values["atendido"],
        authorization_status=values["autorizado_contacto"],
        phone_e164=values["telefono_e164"],
        doctor_review_status=values["revision_doctora"],
        exclusion_reason=values["motivo_exclusion"],
        reactivation_status=values["estado_reactivacion"],
        observations=values["observaciones"],
    )


def _row_from_record(record: ReactivationSheetRecord) -> list[str]:
    return [
        record.source_reference,
        record.name,
        record.phone_original,
        record.attended,
        record.authorization_status,
        record.phone_e164,
        record.doctor_review_status,
        record.exclusion_reason,
        record.reactivation_status,
        record.observations,
    ]


class GoogleSheetsReactivationAdapter:
    """Read and project Reactivacion_Historica staging records."""

    def __init__(
        self,
        *,
        client: SheetsClient,
        spreadsheet_id: str,
        tab_name: str,
        enabled: bool,
    ) -> None:
        self.client = client
        self.spreadsheet_id = spreadsheet_id
        self.tab_name = tab_name
        self.enabled = enabled

    @property
    def range_name(self) -> str:
        return f"{self.tab_name}!A:J"

    def read_records(self) -> tuple[ReactivationSheetRecord, ...]:
        """Read staging rows without applying domain decisions."""

        if not self.enabled:
            return ()

        values = self.client.get_values(
            self.spreadsheet_id,
            self.range_name,
        )

        if not values:
            return ()

        headers = [_string(value).strip() for value in values[0]]
        missing_columns = [
            column
            for column in GOOGLE_SHEETS_REACTIVATION_COLUMNS
            if column not in headers
        ]

        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ReactivationSheetContractError(
                "Missing required Reactivacion_Historica columns: "
                f"{missing}"
            )

        if headers != GOOGLE_SHEETS_REACTIVATION_COLUMNS:
            raise ReactivationSheetContractError(
                "Invalid Reactivacion_Historica column order."
            )

        return tuple(
            _record_from_row(
                row_number=row_number,
                headers=headers,
                row=row,
            )
            for row_number, row in enumerate(values[1:], start=2)
        )

    def update_system_projection(
        self,
        record: ReactivationSheetRecord,
        *,
        phone_e164: str,
        reactivation_status: str,
    ) -> str:
        """
        Update only telefono_e164 and estado_reactivacion.

        Source and human-owned columns are never written by this method.
        """

        if not self.enabled:
            return "skipped_disabled"

        self.client.update_values(
            self.spreadsheet_id,
            f"{self.tab_name}!F{record.row_number}",
            [[_string(phone_e164)]],
        )
        self.client.update_values(
            self.spreadsheet_id,
            f"{self.tab_name}!I{record.row_number}",
            [[_string(reactivation_status)]],
        )

        return "updated"
