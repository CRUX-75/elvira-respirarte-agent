# P6-F.9.14.13 — Appointment Context Carryover SPEC

## Status

DRAFT / SPEC

## Objective

Define how Elvira carries active appointment context across conversational turns during the stateful appointment request flow.

This block solves the runtime bug discovered in `/test/message-stateful` where the patient provides a valid appointment date in one turn and then selects a time window in the next turn, but the resolved date context is no longer available when AppointmentRequest persistence is evaluated.

## Problem

During the appointment flow, the system currently resolves appointment date information only inside the current runtime state object.

Example flow:

1. Patient says: `El viernes`
2. Runtime resolves:
   - `fecha_solicitada = 2026-05-29`
   - `fecha_solicitada_texto = viernes 29 de mayo`
   - `slots_candidatos`
   - availability flags
3. Runtime moves patient to:
   - `ST_CITA_FRANJA`
4. Patient then says: `En la tarde`
5. Runtime correctly routes:
   - `intent = hora_cita`
   - `nuevo_estado = ST_CITA_PENDIENTE`
   - `next_action = confirm_appointment_request`
6. AppointmentRequest persistence is skipped because:
   - `fecha_solicitada` is missing

The decision function is behaving correctly.

The bug is not in the decision function.

The bug is that appointment context is not persisted between turns.

## Current Storage Limitation

`patients` currently persists the conversational state, mainly:

- `telefono`
- `nombre`
- `estado_actual`
- `opt_out`
- timestamps

`interactions` stores audit/history data but is not designed as active conversational state.

`ElviraState` contains appointment fields, but only during a single request lifecycle.

Therefore, after the `fecha_cita` turn is processed, the active appointment context is lost before the following `hora_cita` turn.

## Decision

Persist active appointment context in the `patients` table as a JSONB field.

Recommended column:

```sql
appointment_context JSONB

Reason:

patients already represents the current patient-level conversational state.

The appointment context is operational state required to continue the active appointment request flow.

This avoids misusing interactions as state storage and keeps the carryover deterministic, explicit, and auditable.

Appointment Context Shape

Expected JSON shape:

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
Capture Rule

Capture and store appointment context when all conditions are true:

result.intent == "fecha_cita"
result.nuevo_estado == "ST_CITA_FRANJA"
result.fecha_solicitada is present

Fields to capture:

fecha_solicitada
fecha_solicitada_texto
slots_candidatos
es_dia_disponible
is_weekend
is_colombia_holiday
colombia_holiday_name

If no fecha_solicitada exists, no appointment context should be stored.

Carryover Rule

Apply stored appointment context when all conditions are true:

result.intent == "hora_cita"
result.nuevo_estado == "ST_CITA_PENDIENTE"
result.fecha_solicitada is missing
patient.appointment_context exists
patient.appointment_context.fecha_solicitada exists

Fields to restore before calling decide_appointment_request_persistence(...):

fecha_solicitada
fecha_solicitada_texto
slots_candidatos
es_dia_disponible
is_weekend
is_colombia_holiday
colombia_holiday_name

The restored context must be applied only to the in-memory runtime state/result used for the persistence decision.

Clear Rule

Clear patient.appointment_context when:

AppointmentRequest persistence succeeds
opt_out becomes true

Minimum current scope does not require clearing on every unrelated message.

Additional cleanup rules may be added later after observing real flow behavior.

Runtime Boundary

This block prepares the carryover strategy for:

POST /test/message-stateful

The real WhatsApp webhook remains out of scope.

Explicitly Out of Scope

Do not touch in this block:

real POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
Calendar integration
doctor confirmation flow
therapy/session package tracking
automatic appointment confirmation
remaining session tracking
executed session tracking
Planned Next Block

Next block:

P6-F.9.14.14 — Appointment Context Pure Helpers + Tests

Planned files:

app/services/appointment_context.py
tests/test_appointment_context.py

Planned pure helpers:

capture_appointment_context_from_state(state)
apply_appointment_context_to_state(state, context)
should_clear_appointment_context(state, persisted: bool)
Acceptance Criteria

This SPEC is accepted when it clearly defines:

the lost-context problem
why patients.appointment_context JSONB is the right storage location
capture rules
carryover rules
clear rules
runtime scope
explicit out-of-scope boundaries
next implementation block
Architectural Rule Preserved

El canal transporta.
El workflow controla.
La KB informa.
El modelo redacta.
La state machine protege.
El log permite auditar.
