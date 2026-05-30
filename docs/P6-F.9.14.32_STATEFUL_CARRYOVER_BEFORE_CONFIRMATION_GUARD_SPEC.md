# P6-F.9.14.32 — Stateful Carryover Before Confirmation Guard

## Status

SPEC

## Problem

Production Swagger dry-run in P6-F.9.14.31 showed that `/test/message-stateful` can still return unsafe confirmation copy after an unavailable date context is carried over.

Observed flow:

1. Patient asks for an appointment.
2. Patient says `Para maniana`.
3. The date resolves to Sunday 2026-05-31:
   - `is_weekend = true`
   - `es_dia_disponible = false`
   - `slots_candidatos = []`
4. Elvira correctly says that no consultations are available that day.
5. Patient then says `se puede a las 5?`.

Observed unsafe result:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- response says the request was registered
- `appointment_request_decision.should_persist = false`
- `appointment_request_decision.reason = skipped_weekend`
- `appointment_request = null`

The persistence decision layer blocks correctly, but the response/state layer still behaves as if the request was registered.

## Diagnosis

The state transition reaches confirmation before unavailable appointment context fully protects the runtime response/state persistence path.

The endpoint must not rely only on `decide_appointment_request_persistence(...)` to prevent unsafe copy.

## Required behavior

In `/test/message-stateful`, after appointment context carryover has been applied and before final response/log/state persistence, if:

- `fecha_solicitada` exists, and one of:
  - `is_weekend is True`
  - `is_colombia_holiday is True`
  - `es_dia_disponible is False`
  - `slots_candidatos` is empty

and current result is attempting:

- `nuevo_estado = ST_CITA_PENDIENTE`, or
- `next_action = confirm_appointment_request`

then force safe state:

- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `state_reason = unavailable_date_guard`
- response must ask for another available weekday/date
- `persisted_state = ST_CITA_FECHA`
- no AppointmentRequest is created

## Scope

Only `/test/message-stateful`.

## Out of scope

Do not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking
