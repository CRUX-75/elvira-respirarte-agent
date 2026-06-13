"""Google Sheets human review inbox writer.

This adapter maps AppointmentRequest models to the Solicitudes_Cita sheet.

It does not own business logic.
It does not send WhatsApp messages.
It does not read doctor decisions yet.
PostgreSQL remains the source of truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.models.appointment_request import AppointmentRequest


GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS = [
    "id_solicitud",
    "fecha_registro",
    "telefono",
    "nombre_paciente",
    "fecha_solicitada_texto",
    "franja_solicitada",
    "modalidad",
    "estado_solicitud",
    "observaciones_elvira",
    "interaction_id_origen",
    "direccion_domicilio",
    "servicio_solicitado",
    "fecha_confirmada",
    "franja_confirmada",
    "accion_doctora",
    "motivo_decision",
    "revisado_por",
    "fecha_revision",
    "sync_status",
    "last_sync_at",
    "sync_error",
]

DOCTOR_OWNED_COLUMNS = {
    "accion_doctora",
    "motivo_decision",
    "revisado_por",
    "fecha_revision",
}


class SheetsClient(Protocol):
    """Minimal Google Sheets client protocol used by the writer."""

    def get_values(self, spreadsheet_id: str, range_name: str) -> list[list[str]]:
        """Return sheet values including header row."""

    def append_row(self, spreadsheet_id: str, range_name: str, row: list[str]) -> None:
        """Append one row to the sheet."""

    def update_row(
        self,
        spreadsheet_id: str,
        range_name: str,
        row_number: int,
        row: list[str],
    ) -> None:
        """Update one 1-based sheet row."""


def _string(value: object) -> str:
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def map_appointment_request_to_sheet_row(
    request: AppointmentRequest,
    *,
    sync_status: str = "pendiente",
    last_sync_at: str | None = None,
    sync_error: str = "",
) -> dict[str, str]:
    """Map an AppointmentRequest to the Solicitudes_Cita sheet contract."""

    return {
        "id_solicitud": _string(request.id_solicitud),
        "fecha_registro": _string(request.created_at),
        "telefono": _string(request.telefono),
        "nombre_paciente": _string(request.nombre_paciente),
        "fecha_solicitada_texto": _string(request.fecha_solicitada),
        "franja_solicitada": _string(request.franja_solicitada),
        "modalidad": "Domiciliaria",
        "estado_solicitud": _string(request.estado_solicitud),
        "observaciones_elvira": _string(request.observaciones),
        "interaction_id_origen": _string(request.source_interaction_id),
        "direccion_domicilio": _string(request.direccion_domicilio),
        "servicio_solicitado": _string(request.servicio_solicitado),
        "fecha_confirmada": _string(request.fecha_confirmada),
        "franja_confirmada": _string(request.franja_confirmada),
        "accion_doctora": "",
        "motivo_decision": "",
        "revisado_por": "",
        "fecha_revision": "",
        "sync_status": sync_status,
        "last_sync_at": last_sync_at or _now_iso(),
        "sync_error": sync_error,
    }


def _row_list_from_dict(row: dict[str, str]) -> list[str]:
    return [row.get(column, "") for column in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS]


def _row_dict_from_list(headers: list[str], row: list[str]) -> dict[str, str]:
    padded = row + [""] * max(0, len(headers) - len(row))
    return dict(zip(headers, padded))


class GoogleSheetsHumanReviewWriter:
    """Write AppointmentRequest rows into the Solicitudes_Cita sheet."""

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

    def upsert_request(self, request: AppointmentRequest) -> str:
        """Append or update one AppointmentRequest by id_solicitud."""

        if not self.enabled:
            return "skipped_disabled"

        range_name = f"{self.tab_name}!A:U"
        values = self.client.get_values(self.spreadsheet_id, range_name)

        if not values:
            values = [GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS]

        headers = values[0]
        incoming = map_appointment_request_to_sheet_row(request)

        existing_row_index = self._find_existing_row_index(values, request.id_solicitud)

        if existing_row_index is None:
            self.client.append_row(
                self.spreadsheet_id,
                range_name,
                _row_list_from_dict(incoming),
            )
            return "appended"

        existing_row = _row_dict_from_list(headers, values[existing_row_index])
        merged = self._merge_preserving_doctor_owned_values(
            incoming=incoming,
            existing=existing_row,
        )

        sheet_row_number = existing_row_index + 1
        self.client.update_row(
            self.spreadsheet_id,
            range_name,
            sheet_row_number,
            _row_list_from_dict(merged),
        )
        return "updated"

    def _find_existing_row_index(
        self,
        values: list[list[str]],
        id_solicitud: str,
    ) -> int | None:
        for index, row in enumerate(values[1:], start=1):
            if row and row[0] == id_solicitud:
                return index
        return None

    def _merge_preserving_doctor_owned_values(
        self,
        *,
        incoming: dict[str, str],
        existing: dict[str, str],
    ) -> dict[str, str]:
        merged = dict(incoming)

        for column in DOCTOR_OWNED_COLUMNS:
            existing_value = existing.get(column, "")
            if existing_value:
                merged[column] = existing_value

        return merged
