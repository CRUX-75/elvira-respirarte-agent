-- P6-F.16 — Persistent human-review decisions.
-- Apply explicitly during deployment, never automatically at application startup.
-- No foreign key on id_solicitud: rejected unknown requests must also be auditable.
-- Store only a command hash and safe outcome, never the full command or patient message.

CREATE TABLE IF NOT EXISTS human_review_decisions (
    decision_id TEXT PRIMARY KEY,
    id_solicitud TEXT NOT NULL,
    command_hash TEXT NOT NULL CHECK (length(command_hash) = 64),
    actor TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    processed_at TIMESTAMPTZ NOT NULL,
    result_json TEXT NOT NULL
);
