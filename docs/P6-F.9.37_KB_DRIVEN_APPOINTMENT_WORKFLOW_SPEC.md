# P6-F.9.37 — KB-Driven Appointment Workflow Spec

## Status

DRAFT / ACTIVE

## Objective

Redesign the appointment workflow so date availability, candidate slots, appointment context, slot selection, and AppointmentRequest persistence follow one clean architecture.

Core rule:

FECHA → KB → SLOTS → CONTEXT  
HORA → CONTEXT → SLOT SELECTION → APPOINTMENT_REQUEST

## Problem Statement

The previous flow became fragile because appointment availability was being mixed across:

- current turn state
- restored appointment context
- default availability flags
- KB schedule data
- persistence guards

This caused contradictions such as:

- one turn offering valid slots for a date
- the next turn saying the same date was unavailable

The issue is architectural, not only a single bug like `la de las 5`.

## Source of Truth

The KB is the source of truth for schedule availability.

Current intended KB schedule:

- HOR-01: Lunes a viernes excepto miércoles, 15:00–19:00, max 2 patients, slots 15:00–17:00 and 17:00–19:00.
- HOR-02: Miércoles, 15:00–18:00, max 1 patient, slot 15:00–18:00.
- HOR-03: Saturday unavailable.
- HOR-04: Sunday unavailable.
- Colombia holidays unavailable unless explicitly overridden later.

The system must adapt to the doctor's real operational schedule.

The doctor must not be forced into uniform slots because the code prefers that.

## Workflow Contract

### Date Turn

When the patient provides a date, the system must:

1. Resolve the requested date.
2. Check Colombia weekend/holiday constraints.
3. Query or apply KB schedule rules.
4. Calculate candidate slots.
5. Save the full appointment_context.
6. Ask the patient to choose an available franja.

A date turn must not create an AppointmentRequest.

### Time / Slot Turn

When the patient provides a time or slot preference, the system must:

1. Load patient.appointment_context.
2. Restore the full appointment_context as authoritative operational state.
3. Resolve the requested slot from slots_candidatos.
4. Validate slot selection.
5. Persist AppointmentRequest only if selection is valid.
6. Clear appointment_context after successful persistence.

A time / slot turn must not recalculate date availability in a way that contradicts the stored appointment_context.

## Appointment Context Contract

appointment_context is the operational package created after a valid date turn.

Minimum expected shape:

```json
{
  "flow": "appointment_request",
  "fecha_solicitada": "2026-06-17",
  "fecha_solicitada_texto": "miércoles 17 de junio",
  "slots_candidatos": ["3:00 p. m.–6:00 p. m."],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null
}

For hora_cita turns, appointment_context must be restored as a complete authoritative package, not only field-by-field missing values.

Authoritative fields:

fecha_solicitada
fecha_solicitada_texto
slots_candidatos
es_dia_disponible
is_weekend
is_colombia_holiday
colombia_holiday_name
Slot Selection Rules
Single-Slot Day

If slots_candidatos contains exactly one slot, soft confirmations may be accepted.

Examples:

sí
ok
listo
esa
esa franja
me sirve
registre esa
la de las 3

Expected result:

franja_solicitada = only available slot
AppointmentRequest may persist if all other rules pass
Multi-Slot Day

If slots_candidatos contains multiple slots, the patient must choose explicitly.

Valid examples:

la primera
la segunda
la de las 3
la de las 5
de 3 a 5
de 5 a 7

Ambiguous replies must not persist AppointmentRequest.

Ambiguous examples:

sí
ok
esa
en la tarde
me sirve
listo

Expected result for ambiguous multi-slot reply:

remain in ST_CITA_FRANJA
do not persist AppointmentRequest
ask patient to choose one concrete offered slot
Exact-Hour Behavior

Elvira must not promise exact arrival times.

If the patient asks for an exact hour inside a visible franja:

Explain that care is handled by franjas, not guaranteed exact hours.
Map the exact hour to the corresponding KB-backed franja if possible.
Ask the patient to confirm that franja.
Do not persist until the patient confirms.

Example:

Patient:

no se puede a las 4?

If available slot is:

3:00 p. m.–6:00 p. m.

Expected response behavior:

explain franja policy
mention 3:00 p. m.–6:00 p. m.
ask whether to register that franja as preference
no AppointmentRequest yet
AppointmentRequest Persistence Rules

AppointmentRequest can be created only when:

intent is hora_cita
date context exists
selected date is available
candidate slot selection is valid
franja_solicitada is resolved
Elvira is registering a request, not confirming an appointment

When persistence is allowed:

estado_solicitud = pendiente_confirmacion

The system must never create:

estado_solicitud = confirmada

Doctor/human confirmation remains out of scope.

Terminal patient copy after successful request registration:

“Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.”

This copy must not be used unless AppointmentRequest was actually created.

Out of Scope

Do not touch in this phase:

real POST /webhook
real WhatsApp sending
real patients
Google Sheets
Telegram
n8n
Calendar
doctor confirmation automation
campaigns
therapy session package tracking

WHATSAPP_SENDING_ENABLED must remain false.

Test Plan

This phase must define tests for:

appointment_context authoritative restore
Tuesday two-slot flow
Wednesday single-slot flow
Saturday unavailable
Sunday unavailable
Colombia holiday unavailable
multi-slot explicit first selection
multi-slot explicit second selection
multi-slot ambiguous reply blocked
single-slot soft confirmation accepted
exact-hour clarification does not persist immediately
successful AppointmentRequest clears appointment_context
Swagger Validation Plan

After local tests are green, validate only through:

POST /test/message-stateful

Use fresh test phone numbers.

Required Swagger scenarios:

Tuesday happy path:
Quiero pedir una cita
para el martes
la de las 5
Wednesday single-slot path:
Quiero pedir una cita
para el miércoles
sí, esa franja
Multi-slot ambiguous path:
Quiero pedir una cita
para el martes
en la tarde
Exact-hour clarification path:
Quiero pedir una cita
para el miércoles
no se puede a las 4?

Expected safety result:

delivery_status = sending_skipped
no real WhatsApp sending
no real webhook usage
Closure Criteria

This phase is closed only when:

this SDD/spec is committed
implementation plan is clear
tests are defined before implementation
local tests pass
full suite passes
Swagger validation passes through /test/message-stateful
closure is documented
branch is ready to merge into main

