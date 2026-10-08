"""Project existing appointment requests to Sheets without applying decisions."""


def reconcile_appointment_requests(*, repository, writer) -> dict:
    requests = repository.list_all()
    summary = {
        "total": len(requests),
        "appended": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    for request in requests:
        try:
            status = writer.upsert_request(request)
            if status in {"appended", "updated"}:
                summary[status] += 1
            elif status == "skipped_disabled":
                summary["skipped"] += 1
            else:
                raise ValueError("unexpected_writer_status")
        except Exception as exc:
            error_code = "sheets_write_failed"
            if isinstance(exc, ValueError) and str(exc) in {
                "invalid_sheet_headers",
                "duplicate_request_id",
                "unexpected_writer_status",
            }:
                error_code = str(exc)

            summary["failed"] += 1
            summary["errors"].append({
                "id_solicitud": request.id_solicitud,
                "error_code": error_code,
            })

    return summary


def prepare_human_review_sheet_contract(*, writer, apply=False) -> str:
    """Inspect headers and explicitly upgrade known historical contracts."""
    from app.adapters.google_sheets_human_review_writer import (
        GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
    )

    legacy_24_columns = [
        "id_solicitud",
        "fecha_registro",
        "telefono",
        "nombre_paciente",
        "fecha_solicitada",
        "fecha_solicitada_texto",
        "preferencia_original",
        "franja_solicitada",
        "modalidad",
        "estado_solicitud",
        "observaciones_elvira",
        "estado_origen",
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

    values = writer.client.get_values(
        writer.spreadsheet_id, f"{writer.tab_name}!A:AK",
    )
    headers = values[0] if values else []
    current = GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS

    if headers == current:
        return "current"

    if headers == current[:26]:
        if not apply:
            return "upgrade_required"
        if not writer.enabled:
            raise ValueError("sheets_disabled")

        writer.client.update_values(
            writer.spreadsheet_id,
            f"{writer.tab_name}!AA1:AK1",
            [current[26:]],
        )
        return "upgraded"

    if headers == legacy_24_columns:
        if not apply:
            return "legacy_upgrade_required"
        if not writer.enabled:
            raise ValueError("sheets_disabled")

        migrated_values = [current]
        for row in values[1:]:
            padded = row + [""] * max(0, len(legacy_24_columns) - len(row))
            legacy_row = dict(zip(legacy_24_columns, padded))
            migrated_values.append([
                legacy_row.get(column, "") for column in current
            ])

        writer.client.update_values(
            writer.spreadsheet_id,
            f"{writer.tab_name}!A1:AK{len(migrated_values)}",
            migrated_values,
        )
        return "legacy_upgraded"

    raise ValueError("invalid_sheet_headers")
