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
    """Inspect headers; extend the known legacy contract only when requested."""
    from app.adapters.google_sheets_human_review_writer import (
        GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
    )

    values = writer.client.get_values(
        writer.spreadsheet_id, f"{writer.tab_name}!A:AK",
    )
    headers = values[0] if values else []
    current = GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS

    if headers == current:
        return "current"
    if headers != current[:26]:
        raise ValueError("invalid_sheet_headers")
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
