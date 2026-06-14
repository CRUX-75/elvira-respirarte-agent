# P6-F.9.71 — Human Review Inbox Contract Implementation Plan

## Status

SPEC / IMPLEMENTATION PLAN / NO CODE CHANGES YET

## Context

P6-F.9.70 documented the operational readiness review after Dra. D’Aleman validated the first real `Solicitudes_Cita` row.

The doctor requested additional operational fields for the human review inbox and confirmed that some fields must be mandatory before a request can be considered ready for human review.

Validated baseline before this phase:

- AppointmentRequest persists correctly in PostgreSQL.
- Google Sheets human review inbox append was validated in controlled mode.
- `human_review_inbox.status=appended` was observed.
- A row was visually confirmed in `Solicitudes_Cita`.
- `WHATSAPP_SENDING_ENABLED=false`.
- `GOOGLE_SHEETS_ENABLED=false` by default.
- `KB_RUNTIME_ENABLED=true`.

## Objective

Define exactly how to implement the expanded Human Review Inbox contract before touching code.

This phase maps:

- model changes
- database migration
- repository mapping
- Google Sheets writer mapping
- readiness logic
- tests
- controlled validation
- closure documentation

## Contract Fields To Add

The following fields must be added to the internal AppointmentRequest / human review contract:

- `tipo_cita`
- `eps`
- `barrio`
- `edad_paciente`
- `notas_clinicas_breves`

## Readiness Fields

The following fields must be treated as required before a request can be considered fully ready for human review:

- `direccion_domicilio`
- `servicio_solicitado`

Important:

This does not mean AppointmentRequest creation is blocked immediately.

A request may still be created even if these fields are missing.

The readiness check should identify whether the request is complete enough for human review, but this phase must not introduce patient-facing follow-up automation yet.

## Fields Not Added

Do not add:

- `motivo_consulta`
- `prioridad_urgencia`

These were explicitly not requested by Dra. D’Aleman for now.

## Proposed File Impact

### 1. AppointmentRequest model

Likely file:

- `app/models/appointment_request.py`

Add optional fields:

- `tipo_cita: str | None`
- `eps: str | None`
- `barrio: str | None`
- `edad_paciente: int | None`
- `notas_clinicas_breves: str | None`

Do not create a strict enum yet for `tipo_cita`.

Recommended possible future values:

- `primera_vez`
- `control`

But for now this can remain nullable free text until more real use is validated.

### 2. PostgreSQL schema / migration

Likely files or folders to inspect:

- `app/db/schema.sql`
- `scripts/sql/`

Add nullable columns to `appointment_requests`:

- `tipo_cita TEXT NULL`
- `eps TEXT NULL`
- `barrio TEXT NULL`
- `edad_paciente INTEGER NULL`
- `notas_clinicas_breves TEXT NULL`

Do not make `direccion_domicilio` or `servicio_solicitado` database-level `NOT NULL` yet.

Reason:

The conversational flow may create appointment requests before all operational review fields are collected.

Readiness should initially be service-level logic, not a hard database constraint.

### 3. Repository mapping

Likely file:

- `app/repositories/postgres_appointment_request_repository.py`

Update:

- INSERT mapping
- SELECT mapping
- UPDATE mapping
- row-to-model hydration

The repository must remain backward-compatible with existing rows where the new fields are NULL.

### 4. Google Sheets human review writer

Likely files:

- `app/adapters/google_sheets_human_review_writer.py`
- `app/adapters/google_sheets_human_review_writer_factory.py`
- related tests

Add new visible columns to the outgoing row:

- `tipo_cita`
- `eps`
- `barrio`
- `edad_paciente`
- `notas_clinicas_breves`

Keep existing accepted columns.

Do not enable Google Sheets by default.

### 5. Human review readiness logic

Potential locations:

- `app/services/human_review_service.py`
- or a small dedicated helper if cleaner

Define a deterministic readiness check:

A request is `ready_for_human_review` only if:

- `direccion_domicilio` is present
- `servicio_solicitado` is present

Do not send WhatsApp messages from this logic.

Do not ask the patient for missing data yet.

The function may only expose missing fields for later workflow use.

Possible result shape:

```python
{
    "ready_for_human_review": bool,
    "missing_fields": list[str],
}

Exact implementation can be decided after inspecting current models and service style.

Test Plan

Add or update tests in the smallest useful set.

Model tests

Validate that AppointmentRequest accepts the new optional fields.

Repository tests

Validate that:

new fields are saved
new fields are loaded
new fields are updated
NULL fields remain compatible with existing records
Google Sheets writer tests

Validate that outgoing rows include:

tipo_cita
eps
barrio
edad_paciente
notas_clinicas_breves

Validate that existing required review columns remain present:

direccion_domicilio
servicio_solicitado
Readiness tests

Validate:

request with direccion_domicilio and servicio_solicitado is ready
missing direccion_domicilio is not ready
missing servicio_solicitado is not ready
missing both returns both missing fields
no WhatsApp sending is triggered
Validation Plan

Local validation:

targeted tests for model/repository/writer/readiness
full suite

Controlled runtime validation only if needed:

/test/message-stateful
WHATSAPP_SENDING_ENABLED=false
GOOGLE_SHEETS_ENABLED=false by default

Controlled Google Sheets validation belongs to a later named phase only if needed.

Out Of Scope

Do not implement:

real /webhook changes
WHATSAPP_SENDING_ENABLED=true
Google Sheets enabled by default
Telegram
n8n
Calendar
doctor confirmation automation
patient-facing missing-data follow-up
campaigns
real patient activation
Implementation Order
Inspect current model, schema, repository, writer, and tests.
Write/adjust tests first.
Add model fields.
Add schema/migration draft.
Update repository mappings.
Update Google Sheets writer mapping.
Add readiness helper/service logic.
Run targeted tests.
Run full suite.
Document closure.
Closure Criteria

P6-F.9.71 is closed when:

this implementation plan is committed
no runtime code has been changed
next implementation block is clearly named

Next recommended block:

P6-F.9.72 — Human Review Inbox Contract Tests

Purpose:

Write failing/targeted tests for the expanded contract before implementation.
