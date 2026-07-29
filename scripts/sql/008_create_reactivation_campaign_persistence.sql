-- P6-F.11.3 — Patient reactivation campaign persistence foundation
-- Additive migration. Do not apply without explicit authorization.
-- This script does not enable campaigns or send WhatsApp messages.

CREATE TABLE IF NOT EXISTS reactivation_campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    template_name TEXT NOT NULL,
    template_language TEXT NOT NULL DEFAULT 'es_CO',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT reactivation_campaigns_status_check
        CHECK (
            status IN (
                'draft',
                'ready',
                'active',
                'paused',
                'completed',
                'cancelled'
            )
        )
);

CREATE TABLE IF NOT EXISTS reactivation_campaign_contacts (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL
        REFERENCES reactivation_campaigns (id)
        ON DELETE RESTRICT,
    source_reference TEXT NOT NULL,
    name TEXT,
    phone_original TEXT,
    phone_e164 TEXT NOT NULL,
    attended BOOLEAN,

    authorization_status TEXT NOT NULL DEFAULT 'pending',
    doctor_review_status TEXT NOT NULL DEFAULT 'pending',

    status TEXT NOT NULL DEFAULT 'staged',
    exclusion_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,

    idempotency_key TEXT NOT NULL UNIQUE,
    provider_message_id TEXT,

    retryable BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error_category TEXT,

    claim_token TEXT,
    claim_expires_at TIMESTAMPTZ,

    last_attempt_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT reactivation_campaign_contacts_authorization_check
        CHECK (
            authorization_status IN (
                'pending',
                'approved',
                'denied'
            )
        ),

    CONSTRAINT reactivation_campaign_contacts_doctor_review_check
        CHECK (
            doctor_review_status IN (
                'pending',
                'approved',
                'excluded'
            )
        ),

    CONSTRAINT reactivation_campaign_contacts_status_check
        CHECK (
            status IN (
                'staged',
                'excluded',
                'eligible',
                'pending',
                'accepted',
                'sent',
                'delivered',
                'read',
                'failed',
                'opted_out'
            )
        ),

    CONSTRAINT reactivation_campaign_contacts_attempt_count_check
        CHECK (attempt_count >= 0),

    CONSTRAINT reactivation_campaign_contacts_campaign_phone_unique
        UNIQUE (
            campaign_id,
            phone_e164
        )
);

CREATE INDEX IF NOT EXISTS
    idx_reactivation_campaign_contacts_campaign_status
    ON reactivation_campaign_contacts (
        campaign_id,
        status,
        created_at
    );

CREATE INDEX IF NOT EXISTS
    idx_reactivation_campaign_contacts_retryable_claim
    ON reactivation_campaign_contacts (
        status,
        retryable,
        claim_expires_at,
        created_at
    );

CREATE UNIQUE INDEX IF NOT EXISTS
    idx_reactivation_campaign_contacts_provider_message_id
    ON reactivation_campaign_contacts (provider_message_id)
    WHERE provider_message_id IS NOT NULL;
