-- P6-F.11.4 — Reactivation response persistence
--
-- Additive migration for safe inbound-response metadata.
-- This migration must not be applied without explicit authorization.
-- Raw inbound message text is intentionally not stored here.

BEGIN;

ALTER TABLE reactivation_campaign_contacts
    ADD COLUMN IF NOT EXISTS inbound_whatsapp_message_id TEXT,
    ADD COLUMN IF NOT EXISTS response_classification TEXT,
    ADD COLUMN IF NOT EXISTS response_safe_reason TEXT,
    ADD COLUMN IF NOT EXISTS response_requires_human_escalation
        BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS responded_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_reactivation_campaign_contacts_inbound_message_id
    ON reactivation_campaign_contacts (inbound_whatsapp_message_id)
    WHERE inbound_whatsapp_message_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS reactivation_campaign_response_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id TEXT NOT NULL REFERENCES
        reactivation_campaign_contacts(id) ON DELETE CASCADE,
    inbound_whatsapp_message_id TEXT NOT NULL,
    response_classification TEXT NOT NULL,
    response_safe_reason TEXT,
    global_opt_out_requested BOOLEAN NOT NULL DEFAULT FALSE,
    campaign_opt_out_requested BOOLEAN NOT NULL DEFAULT FALSE,
    requires_human_escalation BOOLEAN NOT NULL DEFAULT FALSE,
    received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (inbound_whatsapp_message_id)
);

CREATE INDEX IF NOT EXISTS
    idx_reactivation_response_events_contact_created
    ON reactivation_campaign_response_events (
        contact_id,
        created_at DESC
    );

COMMIT;
