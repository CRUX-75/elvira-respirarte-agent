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
