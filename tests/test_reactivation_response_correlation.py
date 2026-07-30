from contextlib import contextmanager
from datetime import datetime, timezone

from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
)


NOW = datetime(2026, 7, 29, 18, 0, tzinfo=timezone.utc)


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

    @contextmanager
    def connect(self):
        yield self.connection


def test_finds_latest_accepted_reactivation_contact_by_phone_read_only():
    engine = FakeEngine(
        {
            "id": "contact-001",
            "campaign_id": "campaign-001",
            "source_reference": "historical-row-001",
            "phone_e164": "573000000001",
            "status": "read",
            "provider_message_id": "wamid.outbound-001",
            "accepted_at": NOW,
        }
    )
    repository = ReactivationCampaignContactRepository(engine)

    contact = repository.find_latest_response_candidate_by_phone(
        phone_e164="573000000001"
    )

    assert contact is not None
    assert contact.id == "contact-001"
    assert contact.phone_e164 == "573000000001"
    assert contact.provider_message_id == "wamid.outbound-001"

    assert len(engine.connection.calls) == 1
    sql, params = engine.connection.calls[0]
    normalized_sql = " ".join(sql.lower().split())

    assert "from reactivation_campaign_contacts" in normalized_sql
    assert "phone_e164 = :phone_e164" in normalized_sql
    assert "provider_message_id is not null" in normalized_sql

    for qualifying_status in (
        "accepted",
        "sent",
        "delivered",
        "read",
        "opted_out",
    ):
        assert f"'{qualifying_status}'" in normalized_sql

    assert "order by" in normalized_sql
    assert "accepted_at desc" in normalized_sql
    assert "limit 1" in normalized_sql
    assert params == {"phone_e164": "573000000001"}


def test_response_correlation_projects_safe_response_metadata():
    engine = FakeEngine(
        {
            "id": "contact-002",
            "campaign_id": "campaign-001",
            "source_reference": "historical-row-002",
            "phone_e164": "573000000002",
            "status": "opted_out",
            "provider_message_id": "wamid.outbound-002",
            "inbound_whatsapp_message_id": "wamid.inbound-002",
            "response_classification": "campaign_refusal",
            "response_safe_reason": "explicit_refusal",
            "response_requires_human_escalation": False,
            "responded_at": NOW,
            "accepted_at": NOW,
        }
    )
    repository = ReactivationCampaignContactRepository(engine)

    contact = repository.find_latest_response_candidate_by_phone(
        phone_e164="573000000002"
    )

    assert contact is not None
    assert (
        contact.inbound_whatsapp_message_id
        == "wamid.inbound-002"
    )
    assert contact.response_classification == "campaign_refusal"
    assert contact.response_safe_reason == "explicit_refusal"
    assert (
        contact.response_requires_human_escalation
        is False
    )
    assert contact.responded_at == NOW

    sql, _ = engine.connection.calls[0]
    normalized_sql = " ".join(sql.lower().split())

    for projected_column in (
        "inbound_whatsapp_message_id",
        "response_classification",
        "response_safe_reason",
        "response_requires_human_escalation",
        "responded_at",
    ):
        assert projected_column in normalized_sql
