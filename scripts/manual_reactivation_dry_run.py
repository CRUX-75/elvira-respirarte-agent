"""Controlled administrative entrypoint for P6-F.11.7-C real dry run.

Safety boundary:

- requires explicit REACTIVATION_DRY_RUN_ENABLED=1;
- reads Reactivacion_Historica through the existing dry-run factory/runtime;
- uses PostgreSQL only for contextual read-only lookups;
- projects only the adapter-owned Sheets fields;
- does not import Meta dispatcher or WhatsApp transport;
- does not create or persist reactivation campaigns/contacts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.config import Settings
from app.db.session import engine
from app.repositories.patients import find_patient_by_phone_read_only
from app.services.reactivation_dry_run_factory import (
    build_reactivation_dry_run_dependencies,
)
from app.services.reactivation_dry_run_runtime import (
    run_reactivation_dry_run_best_effort,
)


_ENABLE_ENV = "REACTIVATION_DRY_RUN_ENABLED"
_CAMPAIGN_ID_ENV = "REACTIVATION_DRY_RUN_CAMPAIGN_ID"
_DEFAULT_COUNTRY_CODE_ENV = "REACTIVATION_DRY_RUN_DEFAULT_COUNTRY_CODE"


def _print_safe_summary(result: object) -> None:
    print(
        "reactivation_dry_run"
        f" total={result.total}"
        f" eligible={result.eligible}"
        f" excluded={result.excluded}"
        f" invalid_input={result.invalid_input}"
        f" runtime_error={result.runtime_error}"
    )


def main() -> int:
    enabled = os.getenv(_ENABLE_ENV)

    if enabled != "1":
        print(
            "Reactivation dry run disabled: "
            f"{_ENABLE_ENV} must be exactly 1.",
            file=sys.stderr,
        )
        return 2

    campaign_id = os.getenv(_CAMPAIGN_ID_ENV, "").strip()
    if not campaign_id:
        print(
            "Reactivation dry run refused: "
            f"{_CAMPAIGN_ID_ENV} is required.",
            file=sys.stderr,
        )
        return 2

    default_country_code = (
        os.getenv(_DEFAULT_COUNTRY_CODE_ENV, "").strip() or None
    )

    settings = Settings()

    dependencies = build_reactivation_dry_run_dependencies(
        settings=settings,
        campaign_id=campaign_id,
        default_country_code=default_country_code,
        engine=engine,
        patient_lookup=find_patient_by_phone_read_only,
    )

    if dependencies is None:
        print(
            "Reactivation dry run refused: "
            "required dry-run or Google Sheets configuration is unavailable.",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_reactivation_dry_run_best_effort(
            adapter=dependencies.adapter,
            context_resolver=dependencies.context_resolver,
            default_country_code=dependencies.default_country_code,
        )
    except Exception:
        print(
            "Reactivation dry run failed safely during runtime execution.",
            file=sys.stderr,
        )
        return 2

    _print_safe_summary(result)
    return 0 if result.runtime_error == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
