"""Read-only operational metrics for one reactivation batch."""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.services.reactivation_batch_metrics import (
    calculate_reactivation_batch_metrics,
)


_ENABLE_ENV = "REACTIVATION_BATCH_REPORT_ENABLED"
_CAMPAIGN_ID_ENV = "REACTIVATION_BATCH_REPORT_CAMPAIGN_ID"
_UNIT_COST_ENV = "REACTIVATION_BATCH_META_UNIT_COST"
_CURRENCY_ENV = "REACTIVATION_BATCH_META_CURRENCY"
_PRICING_SOURCE_ENV = "REACTIVATION_BATCH_META_PRICING_SOURCE"
_PRICING_AS_OF_ENV = "REACTIVATION_BATCH_META_PRICING_AS_OF"
_APPOINTMENT_IDS_ENV = (
    "REACTIVATION_BATCH_APPOINTMENT_CONTACT_IDS"
)


def _build_contact_repository():
    from app.db.session import engine
    from app.repositories.reactivation_campaigns import (
        ReactivationCampaignContactRepository,
    )

    return ReactivationCampaignContactRepository(engine)


def _parse_appointment_contact_ids(
    raw_value: str | None,
) -> tuple[str, ...]:
    raw = str(raw_value or "").strip()

    if not raw:
        return ()

    values = tuple(
        value.strip()
        for value in raw.split(",")
    )

    if any(not value for value in values):
        raise ValueError(
            "Appointment contact IDs must be non-empty"
        )

    if len(set(values)) != len(values):
        raise ValueError(
            "Appointment contact IDs must be unique"
        )

    return values


def _format_cost(value) -> str:
    if value is None:
        return "unavailable"

    return str(value)


def main() -> int:
    if os.getenv(_ENABLE_ENV) != "1":
        print(
            "Batch report disabled: "
            f"{_ENABLE_ENV} must be exactly 1."
        )
        return 2

    campaign_id = os.getenv(
        _CAMPAIGN_ID_ENV,
        "",
    ).strip()
    currency = os.getenv(
        _CURRENCY_ENV,
        "",
    ).strip()
    pricing_source = os.getenv(
        _PRICING_SOURCE_ENV,
        "",
    ).strip()
    pricing_as_of = os.getenv(
        _PRICING_AS_OF_ENV,
        "",
    ).strip()

    if not campaign_id:
        print(
            "Batch report refused: "
            f"{_CAMPAIGN_ID_ENV} is required."
        )
        return 2

    if not currency:
        print(
            "Batch report refused: "
            f"{_CURRENCY_ENV} is required."
        )
        return 2

    if not pricing_source:
        print(
            "Batch report refused: "
            f"{_PRICING_SOURCE_ENV} is required."
        )
        return 2

    try:
        date.fromisoformat(pricing_as_of)
    except ValueError:
        print(
            "Batch report refused: "
            f"{_PRICING_AS_OF_ENV} must be YYYY-MM-DD."
        )
        return 2

    try:
        unit_cost = Decimal(
            os.getenv(_UNIT_COST_ENV, "").strip()
        )
    except InvalidOperation:
        print(
            "Batch report refused: "
            f"{_UNIT_COST_ENV} must be numeric."
        )
        return 2

    try:
        appointment_contact_ids = (
            _parse_appointment_contact_ids(
                os.getenv(_APPOINTMENT_IDS_ENV)
            )
        )

        repository = _build_contact_repository()
        contacts = repository.list_by_campaign_id(
            campaign_id=campaign_id,
        )

        metrics = calculate_reactivation_batch_metrics(
            contacts=contacts,
            appointment_request_contact_ids=(
                appointment_contact_ids
            ),
            delivered_message_unit_cost=unit_cost,
            currency=currency,
            pricing_source=pricing_source,
        )
    except Exception:
        print(
            "Batch report failed safely during "
            "read-only calculation."
        )
        return 2

    print(
        "reactivation_batch_metrics"
        f" total={metrics.total}"
        f" delivered={metrics.delivered}"
        f" read={metrics.read}"
        f" replied={metrics.replied}"
        f" interested={metrics.interested}"
        f" appointment_requests={metrics.appointment_requests}"
        f" opt_out={metrics.opt_out}"
    )

    print(
        "reactivation_batch_costs"
        f" currency={metrics.currency}"
        f" total_cost={_format_cost(metrics.total_cost)}"
        " cost_per_delivered="
        f"{_format_cost(metrics.cost_per_delivered)}"
        f" cost_per_reply={_format_cost(metrics.cost_per_reply)}"
        " cost_per_positive_response="
        f"{_format_cost(metrics.cost_per_positive_response)}"
        " cost_per_appointment_request="
        f"{_format_cost(metrics.cost_per_appointment_request)}"
    )

    print(
        "reactivation_batch_pricing"
        f" pricing_source={metrics.pricing_source}"
        f" pricing_as_of={pricing_as_of}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
