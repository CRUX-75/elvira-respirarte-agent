# P6-F.9.14.16 — Stateful Endpoint Carryover Wiring Closure

## Status

CLOSED / RED-THEN-GREEN / GREEN / COMMITTED

## Objective

Wire appointment context carryover into `POST /test/message-stateful` only.

The goal was to preserve appointment date context between turns so that a patient can first provide a date and then select a time window in the next message without losing `fecha_solicitada`.

## Problem Solved

Before this block, the production dry-run flow behaved like this:

1. Patient said: `El viernes`
2. Runtime resolved:
   - `fecha_solicitada`
   - `fecha_solicitada_texto`
   - `slots_candidatos`
   - availability flags
3. Patient state moved to `ST_CITA_FRANJA`
4. Patient then said: `En la tarde`
5. Runtime correctly routed:
   - `intent = hora_cita`
   - `nuevo_estado = ST_CITA_PENDIENTE`
   - `next_action = confirm_appointment_request`
6. AppointmentRequest persistence was skipped because:
   - `fecha_solicitada` was missing

The decision function was correct.

The missing piece was context carryover between turns.

## Implementation Scope

Changed runtime surface:

- `POST /test/message-stateful`

Real production webhook remains untouched.

## Files Changed

Main runtime:

- `app/main.py`

Tests:

- `tests/test_stateful_appointment_context_carryover.py`
- `tests/test_stateful_appointment_request_wiring.py`

Previously prepared dependencies used by this block:

- `app/services/appointment_context.py`
- `app/repositories/patients.py`
- `scripts/sql/002_add_patient_appointment_context.sql`

## Runtime Behavior Added

`/test/message-stateful` now:

1. Reads `patient.appointment_context`
2. Applies stored context to the current runtime result when:
   - current intent is `hora_cita`
   - current state is `ST_CITA_PENDIENTE`
   - current result has no `fecha_solicitada`
3. Calls `decide_appointment_request_persistence(...)`
4. Persists AppointmentRequest when the decision allows it
5. Captures appointment context after `fecha_cita -> ST_CITA_FRANJA`
6. Clears appointment context after successful AppointmentRequest persistence
7. Clears appointment context when opt-out is true

## Validation

Targeted tests:

```bash
pytest tests/test_stateful_appointment_request_wiring.py -q
pytest tests/test_stateful_appointment_context_carryover.py -q

Result:

4 passed
2 passed

Full suite:

pytest -q

Result:

186 passed
Important Test Isolation Fix

Existing stateful endpoint tests were updated to monkeypatch:

update_patient_appointment_context
clear_patient_appointment_context

Reason:

After carryover wiring, the endpoint can call these repository functions.

Unit tests must not reach the real database.

This fixed the accidental attempt to resolve the production host elvira_elvira during local tests.

Safety Boundaries Preserved

Still not touched:

real POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
Calendar
doctor confirmation flow
therapy/session package tracking
automatic appointment confirmation
Current Conclusion

The stateful dry-run endpoint now supports appointment context carryover safely.

The original runtime bug is fixed at the dry-run validation layer.

Next safe step is production DB migration for:

ALTER TABLE patients
ADD COLUMN IF NOT EXISTS appointment_context JSONB;

This must be done as a controlled production migration before Swagger dry-run can validate the full production behavior.
