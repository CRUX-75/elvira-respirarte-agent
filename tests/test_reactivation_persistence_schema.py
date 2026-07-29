import re
from pathlib import Path


MIGRATION = Path(
    "scripts/sql/008_create_reactivation_campaign_persistence.sql"
)


def migration_sql() -> str:
    assert MIGRATION.exists(), (
        "Missing versioned migration: "
        "008_create_reactivation_campaign_persistence.sql"
    )

    source = MIGRATION.read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", source).strip().lower()


def test_migration_creates_independent_campaign_tables():
    sql = migration_sql()

    assert (
        "create table if not exists reactivation_campaigns"
        in sql
    )
    assert (
        "create table if not exists "
        "reactivation_campaign_contacts"
        in sql
    )
    assert "human_escalation_events" not in sql


def test_campaign_schema_matches_domain_contract():
    sql = migration_sql()

    required_fragments = [
        "id text primary key",
        "name text not null",
        "template_name text not null",
        "template_language text not null default 'es_co'",
        "status text not null default 'draft'",
        "created_at timestamptz not null default now()",
        "updated_at timestamptz not null default now()",
    ]

    for fragment in required_fragments:
        assert fragment in sql

    for status in (
        "draft",
        "ready",
        "active",
        "paused",
        "completed",
        "cancelled",
    ):
        assert f"'{status}'" in sql


def test_contact_schema_preserves_staging_and_review_fields():
    sql = migration_sql()

    required_fragments = [
        "id text primary key",
        "campaign_id text not null",
        "references reactivation_campaigns (id)",
        "source_reference text not null",
        "name text",
        "phone_original text",
        "phone_e164 text not null",
        "attended boolean",
        "authorization_status text not null default 'pending'",
        "doctor_review_status text not null default 'pending'",
        "status text not null default 'staged'",
        "exclusion_reasons jsonb not null default '[]'::jsonb",
        "idempotency_key text not null unique",
    ]

    for fragment in required_fragments:
        assert fragment in sql

    for authorization_status in (
        "pending",
        "approved",
        "denied",
    ):
        assert f"'{authorization_status}'" in sql

    for doctor_review_status in (
        "pending",
        "approved",
        "excluded",
    ):
        assert f"'{doctor_review_status}'" in sql


def test_contact_schema_contains_delivery_lifecycle_and_claim():
    sql = migration_sql()

    required_fragments = [
        "provider_message_id text",
        "retryable boolean not null default false",
        "attempt_count integer not null default 0",
        "last_error_category text",
        "claim_token text",
        "claim_expires_at timestamptz",
        "last_attempt_at timestamptz",
        "accepted_at timestamptz",
        "sent_at timestamptz",
        "delivered_at timestamptz",
        "read_at timestamptz",
        "failed_at timestamptz",
        "created_at timestamptz not null default now()",
        "updated_at timestamptz not null default now()",
        "check (attempt_count >= 0)",
    ]

    for fragment in required_fragments:
        assert fragment in sql

    for status in (
        "staged",
        "excluded",
        "eligible",
        "pending",
        "accepted",
        "sent",
        "delivered",
        "read",
        "failed",
        "opted_out",
    ):
        assert f"'{status}'" in sql


def test_contact_natural_key_blocks_duplicate_commercial_contact():
    sql = migration_sql()

    assert "unique ( campaign_id, phone_e164 )" in sql


def test_provider_message_id_has_partial_unique_index():
    sql = migration_sql()

    assert (
        "on reactivation_campaign_contacts "
        "(provider_message_id)"
        in sql
    )
    assert "where provider_message_id is not null" in sql


def test_schema_indexes_retryable_claims_without_enabling_campaign():
    sql = migration_sql()

    assert "status" in sql
    assert "retryable" in sql
    assert "claim_expires_at" in sql
    assert "campaign_enabled" not in sql
