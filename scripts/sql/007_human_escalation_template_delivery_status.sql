-- P6-F.10.5 — Approved template delivery and confirmed Meta statuses
-- Apply only while HUMAN_ESCALATION_ENABLED=false.

ALTER TABLE human_escalation_events
    ADD COLUMN IF NOT EXISTS template_parameters JSONB
        NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;

ALTER TABLE human_escalation_events
    DROP CONSTRAINT IF EXISTS human_escalation_events_status_check;

ALTER TABLE human_escalation_events
    ADD CONSTRAINT human_escalation_events_status_check
        CHECK (
            status IN (
                'pending',
                'accepted',
                'sent',
                'delivered',
                'read',
                'failed'
            )
        );

CREATE UNIQUE INDEX IF NOT EXISTS
    idx_human_escalation_events_provider_message_id
    ON human_escalation_events (provider_message_id)
    WHERE provider_message_id IS NOT NULL;
