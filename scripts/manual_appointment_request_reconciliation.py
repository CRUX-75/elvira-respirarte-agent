"""Manual appointment visibility reconciliation. No decisions or WhatsApp."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.human_review_sheet_projector import HumanReviewSheetProjector

from app.services.appointment_request_reconciliation import (
    prepare_human_review_sheet_contract,
    reconcile_appointment_requests,
)


def run_reconciliation(
    *,
    repository,
    writer,
    apply: bool = False,
    test_request_ids=(),
    projection_writer=None,
) -> dict:
    requests = repository.list_all()
    request_ids = {request.id_solicitud for request in requests}
    confirmed_test_ids = frozenset(test_request_ids)

    if not confirmed_test_ids.issubset(request_ids):
        raise ValueError("unknown_test_request_id")

    contract = prepare_human_review_sheet_contract(writer=writer)

    if not apply:
        values = writer.client.get_values(
            writer.spreadsheet_id,
            f"{writer.tab_name}!A:AK",
        )
        counts = Counter(
            row[0] for row in values[1:] if row and row[0]
        )
        present = len(request_ids.intersection(counts))
        return {
            "mode": "preview",
            "total": len(requests),
            "present": present,
            "missing": len(requests) - present,
            "duplicate_request_ids": sum(
                count > 1 for count in counts.values()
            ),
            "contract": contract,
        }

    if not writer.enabled:
        raise ValueError("sheets_disabled")

    prepare_human_review_sheet_contract(writer=writer, apply=True)
    writer.test_request_ids = confirmed_test_ids
    return {
        "mode": "apply",
        **reconcile_appointment_requests(
            repository=repository,
            writer=projection_writer if projection_writer is not None else writer,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Upgrade known headers and reconcile system-owned cells.",
    )
    parser.add_argument(
        "--test-request-id",
        action="append",
        default=[],
        help="Explicitly verified test request ID; repeat as needed.",
    )
    args = parser.parse_args()

    try:
        from app.adapters.google_sheets_human_review_writer_factory import (
            build_google_sheets_human_review_writer,
        )
        from app.config import Settings
        from app.repositories.postgres_appointment_request_repository import (
            PostgresAppointmentRequestRepository,
        )

        settings = Settings()
        if not settings.database_url:
            raise ValueError("database_not_configured")

        writer = build_google_sheets_human_review_writer(settings=settings)
        if writer is None:
            raise ValueError("sheets_not_configured")

        from app.db.session import engine

        result = run_reconciliation(
            repository=PostgresAppointmentRequestRepository(engine),
            writer=writer,
            apply=args.apply,
            test_request_ids=args.test_request_id,
            projection_writer=HumanReviewSheetProjector(
                engine=engine, writer=writer,
            ),
        )
    except Exception as exc:
        safe_codes = {
            "database_not_configured",
            "sheets_not_configured",
            "sheets_disabled",
            "invalid_sheet_headers",
            "unknown_test_request_id",
        }
        error_code = "reconciliation_unavailable"
        if isinstance(exc, ValueError) and str(exc) in safe_codes:
            error_code = str(exc)
        print(json.dumps({"error_code": error_code}))
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
