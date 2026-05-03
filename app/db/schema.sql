CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telefono TEXT NOT NULL UNIQUE,
    nombre TEXT,
    estado_actual TEXT NOT NULL DEFAULT 'ST_INIT',
    opt_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    telefono TEXT NOT NULL,
    nombre TEXT,
    mensaje TEXT NOT NULL,
    respuesta TEXT,
    intent TEXT,
    estado_anterior TEXT,
    nuevo_estado TEXT,
    next_action TEXT,
    state_reason TEXT,
    router_version TEXT,
    state_machine_version TEXT,
    kb_used BOOLEAN DEFAULT FALSE,
    escalation_required BOOLEAN DEFAULT FALSE,
    whatsapp_message_id TEXT,
    whatsapp_timestamp TEXT,
    delivery_status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_message_id TEXT NOT NULL UNIQUE,
    telefono TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patients_telefono
ON patients (telefono);

CREATE INDEX IF NOT EXISTS idx_interactions_telefono
ON interactions (telefono);

CREATE INDEX IF NOT EXISTS idx_interactions_patient_id
ON interactions (patient_id);

CREATE INDEX IF NOT EXISTS idx_interactions_whatsapp_message_id
ON interactions (whatsapp_message_id);

CREATE INDEX IF NOT EXISTS idx_processed_messages_whatsapp_message_id
ON processed_messages (whatsapp_message_id);
