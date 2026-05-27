# P6-F.9.12 — AppointmentRequestRepository Contract

## Status

Draft / SPEC.

## Purpose

Define the persistence contract for `AppointmentRequest` before implementing PostgreSQL storage.

This block follows SDD:

SPEC → CONTRACT → TESTS → IMPLEMENTATION → VALIDATION

No database implementation is allowed in this block until the repository contract is clear.

## Architecture decision

`AppointmentRequest` lifecycle logic remains owned by FastAPI/Python.

The repository is responsible only for persistence and retrieval.

It must not decide:

- patient intent
- appointment lifecycle transitions
- business rules
- appointment availability
- doctor confirmation
- WhatsApp sending
- Telegram notification
- Google Sheets formatting

## Source of truth

The internal Python model remains the source of truth for lifecycle states.

Valid states:

```text
nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada
Active states

For repository lookup purposes, active appointment requests are:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada

These states represent a request that still belongs to the active operational flow.

Terminal states

Terminal appointment requests are:

cancelada
cerrada

These states represent a request that should not block creation of a new request for the same patient.

Required repository operations

The repository contract must support:

save

Persist a new AppointmentRequest.

Expected behavior:

creates a new record
preserves id_solicitud
returns the persisted AppointmentRequest
update

Update an existing AppointmentRequest.

Expected behavior:

updates the existing record by id_solicitud
preserves id_solicitud
returns the updated AppointmentRequest
must not create a duplicate record
get_by_id

Retrieve one request by id_solicitud.

Expected behavior:

returns AppointmentRequest if found
returns None if not found
find_active_by_telefono

Find the active request for a patient phone number.

Expected behavior:

returns the most relevant active AppointmentRequest if one exists
ignores terminal requests
returns None if no active request exists
Duplicate prevention boundary

Duplicate prevention is owned by AppointmentRequestService.

The repository only provides the lookup operation:

find_active_by_telefono(telefono)

The service decides whether to reuse an existing active request or create a new one.

Ordering rule for active lookup

If multiple active requests exist for the same phone number due to legacy data or manual DB inconsistency, the repository should return the most recently updated one.

Preferred ordering:

updated_at descending
created_at descending
deterministic fallback by id_solicitud descending

This rule prepares the contract for imperfect real-world data without making the service ambiguous.

Explicitly out of scope

This contract does not implement:

PostgreSQL table migration
SQLAlchemy repository
raw SQL repository
Google Sheets adapter
Telegram notification
Calendar integration
n8n workflow
appointment availability calculation
automatic appointment confirmation
Future implementation target

A later block should implement a PostgreSQL-backed repository, likely under:

app/repositories/appointment_request_repository.py

The implementation should remain compatible with the service-facing contract defined here.

Initial test strategy

Before implementing PostgreSQL persistence, tests should verify repository behavior using a fake/in-memory adapter.

Initial tests should cover:

saving a request
retrieving by id_solicitud
updating without duplicating
finding active request by phone
ignoring terminal requests
returning the latest active request when more than one exists

