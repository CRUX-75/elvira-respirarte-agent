from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.reactivation_batch_metrics import (
    calculate_reactivation_batch_metrics,
)


NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


def test_calculates_batch_funnel_and_cost_metrics():
    contacts = (
        SimpleNamespace(
            id="contact-1",
            status="delivered",
            delivered_at=NOW,
            read_at=None,
            responded_at=None,
            inbound_whatsapp_message_id=None,
            response_classification=None,
        ),
        SimpleNamespace(
            id="contact-2",
            status="read",
            delivered_at=None,
            read_at=NOW,
            responded_at=NOW,
            inbound_whatsapp_message_id="wamid.inbound.2",
            response_classification="positive_contact_request",
        ),
        SimpleNamespace(
            id="contact-3",
            status="opted_out",
            delivered_at=NOW,
            read_at=NOW,
            responded_at=NOW,
            inbound_whatsapp_message_id="wamid.inbound.3",
            response_classification="campaign_refusal",
        ),
        SimpleNamespace(
            id="contact-4",
            status="accepted",
            delivered_at=None,
            read_at=None,
            responded_at=None,
            inbound_whatsapp_message_id=None,
            response_classification=None,
        ),
    )

    result = calculate_reactivation_batch_metrics(
        contacts=contacts,
        appointment_request_contact_ids=("contact-2",),
        delivered_message_unit_cost=Decimal("0.05"),
        currency="USD",
        pricing_source="Meta current marketing rate",
    )

    assert result.total == 4
    assert result.delivered == 3
    assert result.read == 2
    assert result.replied == 2
    assert result.interested == 1
    assert result.appointment_requests == 1
    assert result.opt_out == 1

    assert result.total_cost == Decimal("0.15")
    assert result.cost_per_delivered == Decimal("0.05")
    assert result.cost_per_reply == Decimal("0.075")
    assert result.cost_per_positive_response == Decimal("0.15")
    assert result.cost_per_appointment_request == Decimal("0.15")
    assert result.currency == "USD"
    assert result.pricing_source == "Meta current marketing rate"
