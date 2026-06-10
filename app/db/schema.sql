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

-- ============================================================
-- Knowledge Base Tables
-- Sprint P5 — Knowledge Base integration
-- Source: Google Sheets editorial KB
-- ============================================================

CREATE TABLE IF NOT EXISTS kb_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id TEXT UNIQUE NOT NULL,
    service_name TEXT NOT NULL,
    category TEXT,
    objective TEXT,
    techniques TEXT,
    patient_scope TEXT,
    modality TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    public_answer_short TEXT,
    public_answer_long TEXT,
    search_terms TEXT,
    escalation_required BOOLEAN NOT NULL DEFAULT FALSE,
    source TEXT NOT NULL DEFAULT 'google_sheets',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kb_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id TEXT UNIQUE NOT NULL,
    day_type TEXT NOT NULL,
    day_name TEXT NOT NULL,
    modality TEXT,
    start_time TEXT,
    end_time TEXT,
    slot_duration_minutes TEXT,
    max_patients TEXT,
    location_type TEXT,
    is_available TEXT NOT NULL DEFAULT 'true',
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'google_sheets',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kb_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id TEXT UNIQUE NOT NULL,
    rule_type TEXT NOT NULL,
    condition TEXT NOT NULL,
    response_rule TEXT NOT NULL,
    allowed_action TEXT,
    escalation BOOLEAN NOT NULL DEFAULT FALSE,
    priority TEXT NOT NULL DEFAULT 'medium',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    source TEXT NOT NULL DEFAULT 'google_sheets',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_services_active
ON kb_services(is_active);

CREATE INDEX IF NOT EXISTS idx_kb_services_name
ON kb_services(service_name);

CREATE INDEX IF NOT EXISTS idx_kb_schedules_available
ON kb_schedules(is_available);

CREATE INDEX IF NOT EXISTS idx_kb_schedules_day_type
ON kb_schedules(day_type);

CREATE INDEX IF NOT EXISTS idx_kb_rules_active
ON kb_rules(is_active);

CREATE INDEX IF NOT EXISTS idx_kb_rules_type
ON kb_rules(rule_type);

CREATE INDEX IF NOT EXISTS idx_kb_rules_condition
ON kb_rules(condition);

