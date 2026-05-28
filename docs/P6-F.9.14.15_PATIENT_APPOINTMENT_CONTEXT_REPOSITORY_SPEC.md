# P6-F.9.14.15 — Patient Repository Appointment Context Methods SPEC

## Status

DRAFT / SPEC

## Objective

Add repository-level support for storing and clearing active appointment context in the `patients` table.

This enables appointment date and slot context to survive between turns during the stateful appointment request flow.

## Decision

Persist appointment context in:

```sql
patients.appointment_context JSONB
Required Repository Methods

The patient repository must support:

update_patient_appointment_context(telefono, context)
clear_patient_appointment_context(telefono)
Responsibilities

The repository is responsible only for persistence.

It must not decide:

when to capture context
when to apply carryover
when to clear context
whether an AppointmentRequest should be created
appointment lifecycle transitions
WhatsApp sending
Google Sheets sync
Telegram notification
n8n workflows

Those decisions remain in services/runtime wiring.

Data Shape

The repository stores a JSON-compatible dict like:

{
  "fecha_solicitada": "2026-05-29",
  "fecha_solicitada_texto": "viernes 29 de mayo",
  "slots_candidatos": [
    "3:00 p. m.–5:00 p. m.",
    "5:00 p. m.–7:00 p. m."
  ],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null
}
Runtime Boundary

This block only prepares repository persistence support.

It does not wire runtime carryover yet.

Explicitly Out of Scope

Do not touch:

POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
Calendar
doctor confirmation flow
therapy/session package tracking
Acceptance Criteria

This block is accepted when:

a migration draft exists to add patients.appointment_context
patient repository methods exist
repository tests validate update and clear behavior
full pytest suite remains green
