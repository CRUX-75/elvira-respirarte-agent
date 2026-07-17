CREATE TABLE IF NOT EXISTS voice_processing_claims (
    whatsapp_message_id TEXT PRIMARY KEY,
    telefono TEXT NOT NULL,
    claim_token UUID NOT NULL DEFAULT gen_random_uuid(),
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lease_expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_voice_processing_claims_expires_at
ON voice_processing_claims (lease_expires_at);
