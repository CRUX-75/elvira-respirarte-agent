from datetime import datetime, timezone
from pathlib import Path

from app.models.reactivation_campaign import (
    ReactivationCampaignContact,
)


SQL_PATH = Path(
    "scripts/sql/009_add_reactivation_response_persistence.sql"
)


def normalized_sql() -> str:
    return " ".join(
        SQL_PATH.read_text(encoding="utf-8").lower().split()
    )


def test_reactivation_contact_schema_persists_safe_response_metadata():
    sql = normalized_sql()

    assert "inbound_whatsapp_message_id text" in sql
    assert "response_classification text" in sql
    assert "response_safe_reason text" in sql
    assert "response_requires_human_escalation boolean" in sql
    assert "responded_at timestamptz" in sql


def test_inbound_reactivation_message_id_is_unique_when_present():
    sql = normalized_sql()

    assert (
        "on reactivation_campaign_contacts "
        "(inbound_whatsapp_message_id)"
    ) in sql
    assert "where inbound_whatsapp_message_id is not null" in sql


def test_reactivation_contact_model_carries_safe_response_metadata():
    responded_at = datetime(
        2026,
        7,
        30,
        11,
        30,
        tzinfo=timezone.utc,
    )

    contact = ReactivationCampaignContact(
        id="contact-001",
        campaign_id="campaign-001",
        source_reference="historical-row-001",
        phone_e164="573000000001",
        inbound_whatsapp_message_id="wamid.inbound-001",
        response_classification="campaign_refusal",
        response_safe_reason="explicit_refusal",
        response_requires_human_escalation=False,
        responded_at=responded_at,
    )

    assert (
        contact.inbound_whatsapp_message_id
        == "wamid.inbound-001"
    )
    assert contact.response_classification == "campaign_refusal"
    assert contact.response_safe_reason == "explicit_refusal"
    assert (
        contact.response_requires_human_escalation
        is False
    )
    assert contact.responded_at == responded_at


def test_response_contract_does_not_store_raw_message_text():
    sql = normalized_sql()

    forbidden_columns = (
        "response_message text",
        "inbound_message text",
        "raw_response text",
        "message_body text",
    )

    for forbidden_column in forbidden_columns:
        assert forbidden_column not in sql
