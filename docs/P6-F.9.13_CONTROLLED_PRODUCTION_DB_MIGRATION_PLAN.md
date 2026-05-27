# P6-F.9.13 — Controlled Production DB Migration Plan

## Status

Draft.

## Purpose

This document defines the controlled plan for applying the `appointment_requests` table migration to the real production PostgreSQL database.

The goal is to prepare and validate the migration safely before any runtime integration is connected.

---

## Scope

In scope:

- Review the existing SQL migration draft.
- Define production pre-checks.
- Define the controlled execution step.
- Define production post-checks.
- Define rollback / containment strategy.
- Confirm that no runtime integration is activated during this block.

Out of scope:

- Connecting AppointmentRequestService to the live runtime flow.
- Creating appointment requests from WhatsApp messages.
- Google Sheets integration.
- Telegram notification.
- n8n workflow changes.
- Swagger endpoint creation.
- WhatsApp sending changes.
- Calendar integration.
- Therapy/session package tracking.

---

## Source SQL File

Migration file:

```text
scripts/sql/001_create_appointment_requests.sql
Target table:

appointment_requests

Important rule:

This SQL file is versioned and reviewable, but it must not be executed automatically by the application.

Production execution must be manual and controlled.

Production Safety Principles
Do not execute SQL before reviewing the migration file.
Do not modify existing production tables during this block.
Do not connect runtime code to the new table during this block.
Do not change WhatsApp sending flags.
Do not touch Google Sheets.
Do not touch Telegram.
Do not touch n8n.
Validate the table exists after migration.
Validate indexes exist after migration.
Keep the system behavior unchanged after migration.
Pre-Migration Checklist

Before executing SQL in production:

 Confirm local repository is clean.
 Confirm latest test suite is green.
 Confirm current branch is main.
 Confirm main is pushed to origin/main.
 Review scripts/sql/001_create_appointment_requests.sql.
 Confirm production DB connection method.
 Confirm access to inspect production database.
 Confirm no runtime code currently depends on appointment_requests.
 Confirm no application deployment is required for this migration.
 Confirm appointment request runtime integration remains disabled/not implemented.

Expected current validation:

149 passed
working tree clean
SQL Review Checklist

The SQL migration must include:

 CREATE TABLE IF NOT EXISTS appointment_requests
 id_solicitud TEXT PRIMARY KEY
 telefono TEXT NOT NULL
 estado_solicitud TEXT NOT NULL
 canal_origen TEXT NOT NULL
 CHECK constraint for valid estado_solicitud
 CHECK constraint for valid canal_origen
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
 idx_appointment_requests_telefono
 idx_appointment_requests_active_lookup

Valid estado_solicitud values:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada

Valid canal_origen values:

whatsapp
manual
system
Pre-Check Queries

Before applying the migration, inspect whether the table already exists:

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'appointment_requests';

Expected result before first migration:

0 rows

If the table already exists, stop and inspect its schema before proceeding.

Controlled Migration Execution

Execution method:

Manual execution against the production PostgreSQL database.

SQL file:

scripts/sql/001_create_appointment_requests.sql

Do not execute through application startup.

Do not execute through runtime code.

Do not deploy new runtime behavior as part of this step.

Post-Migration Verification Queries

Verify table exists:

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'appointment_requests';

Verify columns:

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'appointment_requests'
ORDER BY ordinal_position;

Verify constraints:

SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'public.appointment_requests'::regclass;

Verify indexes:

SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'appointment_requests'
ORDER BY indexname;

Expected indexes:

appointment_requests_pkey
idx_appointment_requests_telefono
idx_appointment_requests_active_lookup
Post-Migration Application Safety Check

After applying the migration:

 Do not enable runtime appointment request persistence yet.
 Do not create test appointment requests from WhatsApp yet.
 Do not activate Google Sheets sync.
 Do not activate Telegram notifications.
 Do not change WhatsApp sending flags.
 Confirm /health still works.
 Confirm /ready still works.
 Confirm existing application behavior remains unchanged.
Rollback / Containment Strategy

Because no runtime code depends on this table yet, the safest containment strategy is:

If migration fails before table creation:
stop
capture the error
do not retry blindly
If table is created incorrectly and no data exists:
inspect the schema
decide whether to drop and recreate manually
If table exists but runtime is not connected:
application behavior should remain unchanged
do not connect runtime until schema is verified

Potential destructive rollback command, only if explicitly approved:

DROP TABLE appointment_requests;

Do not run this casually.

Completion Criteria

This block is complete when:

 SQL migration file has been reviewed.
 Production DB pre-check has been performed.
 Migration has been executed manually or explicitly deferred.
 Post-migration table verification has passed.
 Index verification has passed.
 Application health remains unchanged.
 No runtime integration has been activated.
 Results are documented.
Next Recommended Block After This

After controlled DB migration is verified:

P6-F.9.14 — Runtime Integration SPEC

Goal:

Define where and how AppointmentRequestService enters the existing message flow without changing behavior prematurely.

Do not implement runtime integration before writing the SPEC.

---

## P6-F.9.13.2 — SQL Migration Draft Review Result

Status:

CLOSED / GREEN

Reviewed file:

```text
scripts/sql/001_create_appointment_requests.sql

Review result:

The SQL migration draft is coherent with the AppointmentRequest persistence contract.

Confirmed:

CREATE TABLE IF NOT EXISTS appointment_requests
id_solicitud TEXT PRIMARY KEY
lifecycle state CHECK constraint
source channel CHECK constraint
required telefono
required estado_solicitud
required canal_origen
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
index idx_appointment_requests_telefono
index idx_appointment_requests_active_lookup

The active lookup index matches the repository lookup strategy:

telefono,
estado_solicitud,
updated_at DESC,
created_at DESC,
id_solicitud DESC

Important decision:

No PostgreSQL trigger for updated_at is required at this stage.

Reason:

PostgresAppointmentRequestRepository.update() explicitly persists updated_at from the AppointmentRequest model. The repository owns persistence behavior and the service/model layer owns lifecycle timestamps.

This keeps timestamp updates deterministic and visible in Python instead of adding hidden database-side behavior.

Boundary confirmed:

The SQL migration only creates a new table and indexes.

It does not:

modify existing production tables
activate runtime persistence
connect AppointmentRequestService to WhatsApp flow
touch Google Sheets
touch Telegram
touch n8n
change WhatsApp sending flags

Production SQL has still not been executed.

---

## P6-F.9.13.5 — Production Migration Post-Checks Result

Status:

CLOSED / GREEN

Execution method:

pgweb via EasyPanel browser UI.

Production database:

elvira_respirarte_prod

Migration result:

The `appointment_requests` table was created successfully in production.

Pre-check result:

Before migration, the production database contained the existing operational tables:

- interactions
- kb_rules
- kb_schedules
- kb_services
- patients
- processed_messages

The `appointment_requests` table did not exist before migration.

Post-check result:

The `appointment_requests` table now exists in production.

Verified columns:

- id_solicitud
- telefono
- nombre_paciente
- estado_solicitud
- intent_origen
- canal_origen
- fecha_solicitada
- franja_solicitada
- hora_solicitada_texto
- fecha_aceptada
- franja_aceptada
- fecha_confirmada
- franja_confirmada
- servicio_solicitado
- direccion_domicilio
- observaciones
- motivo_reagendamiento
- motivo_cancelacion
- source_interaction_id
- created_by
- updated_by
- created_at
- updated_at

Verified constraints:

- appointment_requests_canal_origen_check
- appointment_requests_estado_solicitud_check
- appointment_requests_pkey

Verified indexes:

- appointment_requests_pkey
- idx_appointment_requests_active_lookup
- idx_appointment_requests_telefono

Boundary confirmed:

The migration only created the new table and indexes.

No runtime integration was activated.

No WhatsApp sending behavior was changed.

No Google Sheets integration was touched.

No Telegram or n8n workflow was touched.

No existing production table was modified.


---

## P6-F.9.13.6 — Application Health / Ready Safety Check Result

Status:

CLOSED / GREEN

Production endpoint checked:

```text
/ready

Result:

{
  "status": "ready",
  "service": "elvira-respirarte-agent",
  "environment": "production",
  "app_version": "0.2.1",
  "whatsapp_sending_enabled": false,
  "kb_runtime_enabled": true,
  "database": {
    "configured": true
  },
  "repositories": {
    "patients": "configured",
    "interactions": "configured",
    "processed_messages": "configured",
    "kb": "configured"
  },
  "langsmith": {
    "tracing_enabled": true,
    "project": "elvira-respirarte-prod",
    "configured": true
  },
  "openai_configured": true,
  "whatsapp_configured": true,
  "hard_failures": [],
  "safety": {
    "real_whatsapp_sending_allowed": false,
    "p6a_rule": "WHATSAPP_SENDING_ENABLED must remain false during P6-A"
  }
}

Conclusion:

The production application remains healthy after the appointment_requests table migration.

No runtime behavior changed.

WhatsApp sending remains disabled.

No hard failures were detected.

