-- P6-F.10 — Human Escalation via WhatsApp
-- Additive migration. Do not apply before repository validation.

CREATE TABLE IF NOT EXISTS human_escalation_events (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    patient_id TEXT,
    inbound_whatsapp_message_id TEXT NOT NULL,
    escalation_action TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    notification_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    retryable BOOLEAN NOT NULL DEFAULT TRUE,
    provider_message_id TEXT,
    last_error_category TEXT,
    claim_token TEXT,
    claim_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,

    CONSTRAINT human_escalation_events_status_check
        CHECK (status IN ('pending', 'sent', 'failed')),

    CONSTRAINT human_escalation_events_attempt_count_check
        CHECK (attempt_count >= 0),

    CONSTRAINT human_escalation_events_source_action_unique
        UNIQUE (
            inbound_whatsapp_message_id,
            escalation_action
        )
);

CREATE INDEX IF NOT EXISTS idx_human_escalation_events_status_retry
    ON human_escalation_events (
        status,
        retryable,
        created_at
    );

CREATE INDEX IF NOT EXISTS idx_human_escalation_events_patient
    ON human_escalation_events (
        patient_id,
        created_at
    );
