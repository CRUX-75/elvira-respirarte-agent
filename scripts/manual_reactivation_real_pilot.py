"""Controlled administrative entrypoint for P6-F.11.7-F real pilot.

Safety boundary:

- requires explicit REACTIVATION_REAL_PILOT_ENABLED=1;
- requires independent REACTIVATION_REAL_PILOT_SEND_AUTHORIZED=1;
- requires one explicit persisted campaign ID;
- requires an explicit batch of 1-3 unique persisted contact IDs;
- performs no automatic contact selection;
- creates or activates no campaign or contact;
- builds the productive dispatcher only after all administrative gates pass;
- delegates preflight and dispatch safety to the existing real-pilot service.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.db.session import engine
from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
    ReactivationCampaignRepository,
)
from app.services.reactivation_real_pilot import (
    run_reactivation_real_pilot,
)
from app.services.reactivation_template_factory import (
    build_reactivation_template_dispatcher,
)


_ENABLE_ENV = "REACTIVATION_REAL_PILOT_ENABLED"
_SEND_AUTHORIZED_ENV = (
    "REACTIVATION_REAL_PILOT_SEND_AUTHORIZED"
)
_CAMPAIGN_ID_ENV = "REACTIVATION_REAL_PILOT_CAMPAIGN_ID"
_CONTACT_IDS_ENV = "REACTIVATION_REAL_PILOT_CONTACT_IDS"


def _parse_explicit_contact_ids(
    raw_value: str,
) -> tuple[str, ...]:
    raw_parts = raw_value.split(",")
    contact_ids = tuple(
        part.strip()
        for part in raw_parts
    )

    if not 1 <= len(contact_ids) <= 3:
        raise ValueError(
            "Real pilot requires between 1 and 3 explicit contacts."
        )

    if any(not contact_id for contact_id in contact_ids):
        raise ValueError(
            "Real pilot contact IDs must be explicit and non-empty."
        )

    if len(set(contact_ids)) != len(contact_ids):
        raise ValueError(
            "Real pilot contact IDs must be unique."
        )

    return contact_ids


def _print_safe_summary(result: object) -> None:
    print(
        "reactivation_real_pilot"
        f" total={result.total}"
        f" accepted={result.accepted}"
        f" failed={result.failed}"
        f" ignored={result.ignored}"
    )


def main() -> int:
    enabled = os.getenv(_ENABLE_ENV)

    if enabled != "1":
        print(
            "Reactivation real pilot disabled: "
            f"{_ENABLE_ENV} must be exactly 1.",
            file=sys.stderr,
        )
        return 2

    campaign_id = os.getenv(
        _CAMPAIGN_ID_ENV,
        "",
    ).strip()

    if not campaign_id:
        print(
            "Reactivation real pilot refused: "
            f"{_CAMPAIGN_ID_ENV} is required.",
            file=sys.stderr,
        )
        return 2

    raw_contact_ids = os.getenv(
        _CONTACT_IDS_ENV,
        "",
    )

    try:
        contact_ids = _parse_explicit_contact_ids(
            raw_contact_ids
        )
    except ValueError:
        print(
            "Reactivation real pilot refused: "
            f"{_CONTACT_IDS_ENV} must contain "
            "1-3 explicit unique contact IDs.",
            file=sys.stderr,
        )
        return 2

    send_authorized = os.getenv(
        _SEND_AUTHORIZED_ENV
    )

    if send_authorized != "1":
        print(
            "Reactivation real pilot refused: "
            f"{_SEND_AUTHORIZED_ENV} must be exactly 1.",
            file=sys.stderr,
        )
        return 2

    campaign_repository = ReactivationCampaignRepository(
        engine
    )
    contact_repository = (
        ReactivationCampaignContactRepository(
            engine
        )
    )

    try:
        dispatcher = build_reactivation_template_dispatcher(
            engine=engine,
            enabled=True,
        )

        result = asyncio.run(
            run_reactivation_real_pilot(
                campaign_id=campaign_id,
                contact_ids=contact_ids,
                campaign_repository=campaign_repository,
                contact_repository=contact_repository,
                dispatcher=dispatcher,
                send_authorized=True,
            )
        )
    except Exception:
        print(
            "Reactivation real pilot failed safely "
            "during controlled execution.",
            file=sys.stderr,
        )
        return 2

    _print_safe_summary(result)

    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
