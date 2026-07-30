from contextlib import contextmanager
from datetime import datetime, timezone

from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
)


RECEIVED_AT = datetime(
    2026,
    7,
    30,
    12,
    30,
    tzinfo=timezone.utc,
)


class FakeMappings:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return FakeMappings(self.row)


class FakeConnection:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return FakeResult(self.row)


class FakeEngine:
    def __init__(self, row):
        self.connection = FakeConnection(row)
        self.begin_count = 0

    @contextmanager
    def begin(self):
        self.begin_count += 1
        yield self.connection


def response_event_row():
    return {
        "id": "response-event-001",
        "contact_id": "contact-001",
        "inbound_whatsapp_message_id": "wamid.inbound-001",
        "response_classification": "campaign_refusal",
        "response_safe_reason": "explicit_refusal",
        "global_opt_out_requested": False,
        "campaign_opt_out_requested": True,
        "requires_human_escalation": False,
        "received_at": RECEIVED_AT,
        "created_at": RECEIVED_AT,
    }


def test_records_response_event_and_contact_summary_atomically():
    engine = FakeEngine(response_event_row())
    repository = ReactivationCampaignContactRepository(engine)

    event = repository.record_response_event(
        contact_id="contact-001",
        inbound_whatsapp_message_id="wamid.inbound-001",
        response_classification="campaign_refusal",
        response_safe_reason="explicit_refusal",
        global_opt_out_requested=False,
        campaign_opt_out_requested=True,
        requires_human_escalation=False,
        received_at=RECEIVED_AT,
    )

    assert event.id == "response-event-001"
    assert event.contact_id == "contact-001"
    assert (
        event.inbound_whatsapp_message_id
        == "wamid.inbound-001"
    )
    assert event.campaign_opt_out_requested is True

    assert engine.begin_count == 1
    assert len(engine.connection.calls) == 1

    sql, params = engine.connection.calls[0]
    normalized_sql = " ".join(sql.lower().split())

    assert (
        "insert into reactivation_campaign_response_events"
        in normalized_sql
    )
    assert (
        "on conflict (inbound_whatsapp_message_id)"
        in normalized_sql
    )
    assert "do nothing" in normalized_sql

    assert (
        "update reactivation_campaign_contacts"
        in normalized_sql
    )
    assert "inbound_whatsapp_message_id" in normalized_sql
    assert "response_classification" in normalized_sql
    assert "response_safe_reason" in normalized_sql
    assert (
        "response_requires_human_escalation"
        in normalized_sql
    )
    assert "responded_at" in normalized_sql
    assert "'opted_out'" in normalized_sql

    assert "update patients" not in normalized_sql
    assert "raw_message" not in normalized_sql
    assert "message_text" not in normalized_sql
    assert "response_text" not in normalized_sql

    assert params == {
        "contact_id": "contact-001",
        "inbound_whatsapp_message_id": "wamid.inbound-001",
        "response_classification": "campaign_refusal",
        "response_safe_reason": "explicit_refusal",
        "global_opt_out_requested": False,
        "campaign_opt_out_requested": True,
        "requires_human_escalation": False,
        "received_at": RECEIVED_AT,
    }


def test_record_response_event_rejects_missing_identifiers():
    engine = FakeEngine(response_event_row())
    repository = ReactivationCampaignContactRepository(engine)

    invalid_cases = (
        {
            "contact_id": "",
            "inbound_whatsapp_message_id": "wamid.inbound-001",
        },
        {
            "contact_id": "contact-001",
            "inbound_whatsapp_message_id": "",
        },
    )

    for invalid_case in invalid_cases:
        try:
            repository.record_response_event(
                contact_id=invalid_case["contact_id"],
                inbound_whatsapp_message_id=(
                    invalid_case["inbound_whatsapp_message_id"]
                ),
                response_classification="ambiguous",
                response_safe_reason=None,
                global_opt_out_requested=False,
                campaign_opt_out_requested=False,
                requires_human_escalation=False,
                received_at=RECEIVED_AT,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Expected ValueError for missing identifiers."
            )

    assert engine.begin_count == 0
    assert engine.connection.calls == []
