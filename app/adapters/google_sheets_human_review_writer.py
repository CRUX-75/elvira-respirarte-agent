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
    "tipo_cita",
    "eps",
    "barrio",
    "edad_paciente",
    "notas_clinicas_breves",
    "fecha_confirmada",
    "franja_confirmada",
    "accion_doctora",
    "motivo_decision",
    "revisado_por",
    "fecha_revision",
    "sync_status",
    "last_sync_at",
    "sync_error",
    "fecha_decision",
    "franja_decision",
    "datos_faltantes",
    "decision_id",
    "solicitud_updated_at",
    "decision_id_resultado",
    "resultado_decision",
    "error_decision",
    "procesado_por",
    "fecha_procesamiento",
    "tipo_registro",
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

    def update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[str]],
    ) -> None:
        """Update an exact range of system-owned cells."""

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
        "tipo_cita": _string(request.tipo_cita),
        "eps": _string(request.eps),
        "barrio": _string(request.barrio),
        "edad_paciente": _string(request.edad_paciente),
        "notas_clinicas_breves": _string(request.notas_clinicas_breves),
        "fecha_confirmada": _string(request.fecha_confirmada),
        "franja_confirmada": _string(request.franja_confirmada),
        "accion_doctora": "",
        "motivo_decision": "",
        "revisado_por": "",
        "fecha_revision": "",
        "sync_status": sync_status,
        "last_sync_at": last_sync_at or _now_iso(),
        "sync_error": sync_error,
        "fecha_decision": "",
        "franja_decision": "",
        "datos_faltantes": "",
        "decision_id": "",
        "solicitud_updated_at": _string(request.updated_at),
        "decision_id_resultado": "",
        "resultado_decision": "",
        "error_decision": "",
        "procesado_por": "",
        "fecha_procesamiento": "",
        "tipo_registro": "sin_clasificar",
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
        test_request_ids: frozenset[str] = frozenset(),
    ) -> None:
        self.client = client
        self.spreadsheet_id = spreadsheet_id
        self.tab_name = tab_name
        self.enabled = enabled
        self.test_request_ids = frozenset(test_request_ids)

    def upsert_request(self, request: AppointmentRequest) -> str:
        """Project request fields without writing human inputs or decision results."""
        return self._upsert(request)

    def project_decision(self, request: AppointmentRequest, outcome: dict) -> str:
        """Project a safe decision outcome without overwriting a newer result."""
        if outcome["result"]["id_solicitud"] != request.id_solicitud:
            raise ValueError("decision_request_mismatch")
        return self._upsert(request, outcome=outcome)

    def _upsert(self, request: AppointmentRequest, *, outcome=None) -> str:
        if not self.enabled:
            return "skipped_disabled"

        range_name = f"{self.tab_name}!A:AK"
        values = self.client.get_values(self.spreadsheet_id, range_name)
        if not values or values[0] != GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS:
            raise ValueError("invalid_sheet_headers")

        incoming = map_appointment_request_to_sheet_row(request)
        index = self._find_existing_row_index(values, request.id_solicitud)
        existing = (
            _row_dict_from_list(values[0], values[index])
            if index is not None else {}
        )

        if existing.get("tipo_registro") in {"operativo", "prueba_confirmada"}:
            incoming["tipo_registro"] = existing["tipo_registro"]
        if request.id_solicitud in self.test_request_ids:
            incoming["tipo_registro"] = "prueba_confirmada"

        if outcome is not None:
            previous_time = existing.get("fecha_procesamiento")
            if previous_time:
                previous = datetime.fromisoformat(previous_time.replace("Z", "+00:00"))
                current = datetime.fromisoformat(
                    outcome["processed_at"].replace("Z", "+00:00")
                )
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                if current.tzinfo is None:
                    current = current.replace(tzinfo=timezone.utc)
                if previous > current:
                    return "skipped_stale_result"

            incoming.update({
                "decision_id_resultado": outcome["decision_id"],
                "resultado_decision": (
                    "aplicada" if outcome["result"]["success"] else "rechazada"
                ),
                "error_decision": outcome["result"].get("error_code") or "",
                "procesado_por": outcome["actor"],
                "fecha_procesamiento": outcome["processed_at"],
                "sync_status": "sincronizada",
            })

        row = _row_list_from_dict(incoming)
        if index is None:
            self.client.append_row(self.spreadsheet_id, range_name, row)
            return "appended"

        row_number = index + 1
        ranges = [
            ("A", "S", row[:19]),
            ("X", "Z", row[23:26]),
        ]
        if outcome is None:
            ranges.extend([
                ("AE", "AE", row[30:31]),
                ("AK", "AK", row[36:37]),
            ])
        else:
            ranges.append(("AE", "AK", row[30:37]))

        for first, last, cells in ranges:
            self.client.update_values(
                self.spreadsheet_id,
                f"{self.tab_name}!{first}{row_number}:{last}{row_number}",
                [cells],
            )
        return "updated"

    def _find_existing_row_index(
        self,
        values: list[list[str]],
        id_solicitud: str,
    ) -> int | None:
        matches = [
            index
            for index, row in enumerate(values[1:], start=1)
            if row and row[0] == id_solicitud
        ]
        if len(matches) > 1:
            raise ValueError("duplicate_request_id")
        return matches[0] if matches else None

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
