"""Read-only funnel and cost metrics for reactivation batches.

Pricing is always supplied by the caller from a current external source.
No Meta tariff is fixed in application code.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


_POSITIVE_CLASSIFICATIONS = {
    "positive_contact_request",
}

_OPT_OUT_CLASSIFICATIONS = {
    "campaign_refusal",
    "global_opt_out",
}


@dataclass(frozen=True)
class ReactivationBatchMetrics:
    total: int
    delivered: int
    read: int
    replied: int
    interested: int
    appointment_requests: int
    opt_out: int
    total_cost: Decimal
    cost_per_delivered: Decimal | None
    cost_per_reply: Decimal | None
    cost_per_positive_response: Decimal | None
    cost_per_appointment_request: Decimal | None
    currency: str
    pricing_source: str


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _normalized_text(value: Any) -> str:
    return str(_value(value) or "").strip()


def _cost_per(
    total_cost: Decimal,
    count: int,
) -> Decimal | None:
    if count == 0:
        return None

    return total_cost / Decimal(count)


def calculate_reactivation_batch_metrics(
    *,
    contacts: Iterable[Any],
    appointment_request_contact_ids: Iterable[str] = (),
    delivered_message_unit_cost: Decimal,
    currency: str,
    pricing_source: str,
) -> ReactivationBatchMetrics:
    """Calculate one campaign snapshot without persistence or external calls."""

    contact_items = tuple(contacts)
    appointment_ids = {
        str(contact_id or "").strip()
        for contact_id in appointment_request_contact_ids
        if str(contact_id or "").strip()
    }

    unit_cost = Decimal(str(delivered_message_unit_cost))

    if unit_cost < 0:
        raise ValueError(
            "delivered_message_unit_cost cannot be negative"
        )

    normalized_currency = str(currency or "").strip().upper()
    normalized_pricing_source = str(
        pricing_source or ""
    ).strip()

    if not normalized_currency:
        raise ValueError("currency is required")

    if not normalized_pricing_source:
        raise ValueError("pricing_source is required")

    delivered = 0
    read = 0
    replied = 0
    interested = 0
    appointment_requests = 0
    opt_out = 0

    for contact in contact_items:
        contact_id = _normalized_text(
            getattr(contact, "id", None)
        )
        status = _normalized_text(
            getattr(contact, "status", None)
        )
        classification = _normalized_text(
            getattr(
                contact,
                "response_classification",
                None,
            )
        )

        has_response = bool(
            getattr(contact, "responded_at", None)
            or getattr(
                contact,
                "inbound_whatsapp_message_id",
                None,
            )
            or classification
        )

        has_read = bool(
            getattr(contact, "read_at", None)
            or status == "read"
        )

        has_delivery = bool(
            getattr(contact, "delivered_at", None)
            or has_read
            or has_response
            or status in {
                "delivered",
                "read",
                "opted_out",
            }
        )

        delivered += has_delivery
        read += has_read
        replied += has_response
        interested += (
            classification in _POSITIVE_CLASSIFICATIONS
        )
        appointment_requests += (
            contact_id in appointment_ids
        )
        opt_out += (
            status == "opted_out"
            or classification in _OPT_OUT_CLASSIFICATIONS
        )

    total_cost = unit_cost * Decimal(delivered)

    return ReactivationBatchMetrics(
        total=len(contact_items),
        delivered=delivered,
        read=read,
        replied=replied,
        interested=interested,
        appointment_requests=appointment_requests,
        opt_out=opt_out,
        total_cost=total_cost,
        cost_per_delivered=_cost_per(
            total_cost,
            delivered,
        ),
        cost_per_reply=_cost_per(
            total_cost,
            replied,
        ),
        cost_per_positive_response=_cost_per(
            total_cost,
            interested,
        ),
        cost_per_appointment_request=_cost_per(
            total_cost,
            appointment_requests,
        ),
        currency=normalized_currency,
        pricing_source=normalized_pricing_source,
    )
