# P6-F.9.14.30 — Weekend/Unavailable Date State Regression Guard

## Status

SPEC

## Problem

Production Swagger dry-run found an unsafe inconsistency.

When a patient selected an unavailable date, for example Saturday, and then asked for a time, the decision layer correctly blocked persistence with `skipped_weekend`, but the state machine had already advanced to:

- `ST_CITA_PENDIENTE`
- `confirm_appointment_request`

The response layer then generated copy implying that the request had been registered.

This is unsafe because unavailable date context must win over hour selection.

## Required behavior

If the patient is in appointment scheduling flow and the current or carried appointment context indicates:

- `is_weekend is True`, or
- `is_colombia_holiday is True`, or
- `es_dia_disponible is False`, or
- `slots_candidatos` is empty

then an incoming `hora_cita` message must not advance to appointment confirmation.

Expected safe result:

- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `state_reason = unavailable_date_guard`
- no `confirm_appointment_request`
- no `ST_CITA_PENDIENTE`
- no copy implying registration
- no AppointmentRequest persistence

## Scope

Apply deterministic protection before appointment persistence.

First target:

- state machine behavior
- `/test/message-stateful` dry-run behavior

## Out of scope

Do not touch:

- POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking
