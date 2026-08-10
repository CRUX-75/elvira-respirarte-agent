from datetime import datetime, timezone
from pathlib import Path

import app.models.reactivation_campaign as reactivation_models


SQL_PATH = Path(
    "scripts/sql/009_add_reactivation_response_persistence.sql"
)


def normalized_sql() -> str:
    return " ".join(
        SQL_PATH.read_text(encoding="utf-8").lower().split()
    )


def test_response_event_schema_supports_multiple_replies_per_contact():
    sql = normalized_sql()

    assert (
        "create table if not exists "
        "reactivation_campaign_response_events"
    ) in sql
    assert (
        "contact_id text not null references "
        "reactivation_campaign_contacts(id) on delete cascade"
    ) in sql
    assert "inbound_whatsapp_message_id text not null" in sql
    assert "response_classification text not null" in sql
    assert "response_safe_reason text" in sql
    assert "global_opt_out_requested boolean not null default false" in sql
    assert "campaign_opt_out_requested boolean not null default false" in sql
    assert "requires_human_escalation boolean not null default false" in sql
    assert "received_at timestamptz" in sql
    assert "created_at timestamptz not null default now()" in sql


def test_response_event_idempotency_is_per_inbound_message_not_contact():
    sql = normalized_sql()

    assert (
        "unique (inbound_whatsapp_message_id)"
        in sql
    )
    assert "unique (contact_id)" not in sql


def test_response_event_model_carries_only_safe_decision_metadata():
    event_model = getattr(
        reactivation_models,
        "ReactivationCampaignResponseEvent",
    )

    received_at = datetime(
        2026,
        7,
        30,
        12,
        0,
        tzinfo=timezone.utc,
    )

    event = event_model(
        id="response-event-001",
        contact_id="contact-001",
        inbound_whatsapp_message_id="wamid.inbound-001",
        response_classification="campaign_refusal",
        response_safe_reason="explicit_refusal",
        global_opt_out_requested=False,
        campaign_opt_out_requested=True,
        requires_human_escalation=False,
        received_at=received_at,
        created_at=received_at,
    )

    assert event.contact_id == "contact-001"
    assert (
        event.inbound_whatsapp_message_id
        == "wamid.inbound-001"
    )
    assert event.response_classification == "campaign_refusal"
    assert event.response_safe_reason == "explicit_refusal"
    assert event.global_opt_out_requested is False
    assert event.campaign_opt_out_requested is True
    assert event.requires_human_escalation is False
    assert event.received_at == received_at


def test_response_event_contract_does_not_store_raw_message_text():
    sql = normalized_sql()

    forbidden_columns = (
        "message_text text",
        "response_message text",
        "inbound_message text",
        "raw_response text",
        "raw_payload json",
        "raw_payload jsonb",
    )

    for forbidden_column in forbidden_columns:
        assert forbidden_column not in sql

def test_response_event_contact_fk_matches_text_campaign_contact_id():
    sql = normalized_sql()

    assert (
        "contact_id text not null references "
        "reactivation_campaign_contacts(id) on delete cascade"
    ) in sql
