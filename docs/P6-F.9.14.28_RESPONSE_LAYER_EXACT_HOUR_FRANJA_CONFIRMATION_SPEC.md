# P6-F.9.14.28 — Response-layer Exact-Hour Franja Confirmation

## Status

SPEC CREATED

## Reason

P6-F.9.14.27 introduced a runtime guard for loose exact-hour requests inside a visible KB-backed franja.

When a patient says something like:

- se puede a las 3?
- se puede a las 5?
- a las 6

and that exact hour falls inside a visible KB_Horarios franja, the system must not persist an AppointmentRequest immediately.

The runtime now returns:

- reason = requires_exact_hour_franja_confirmation
- should_persist = False
- franja_solicitada = corresponding KB-backed franja

The missing part is response-layer handling.

## Goal

Elvira must explain, in formal usted tone, that attention is handled by time windows / franjas and that an exact hour inside the block cannot be guaranteed.

Elvira must propose the corresponding KB-backed franja and ask the patient to confirm whether they want to register the request for that franja.

## Expected response behavior

For franja:

3:00 p. m.–5:00 p. m.

Example response:

Con gusto. Le cuento que la atención se maneja por franjas horarias y no es posible garantizar una hora exacta dentro del bloque. Para esa hora, la franja correspondiente sería de 3:00 p. m. a 5:00 p. m. ¿Desea que registremos su solicitud para esa franja?

For franja:

5:00 p. m.–7:00 p. m.

Example response:

Con gusto. Le cuento que la atención se maneja por franjas horarias y no es posible garantizar una hora exacta dentro del bloque. Para esa hora, la franja correspondiente sería de 5:00 p. m. a 7:00 p. m. ¿Desea que registremos su solicitud para esa franja?

## Required constraints

Elvira must not:

- confirm real availability
- say the appointment is scheduled
- say the doctor has approved the time
- persist AppointmentRequest during the clarification turn
- promise an exact hour inside the franja
- hardcode only one franja

Elvira must:

- use formal usted tone
- use the franja returned by runtime / KB
- ask for explicit confirmation
- remain in ST_CITA_FRANJA until confirmation
- preserve the existing architecture boundaries

## Scope

In scope:

- response-layer handling for requires_exact_hour_franja_confirmation
- tests protecting patient-facing copy
- minimal wiring if needed so /test/message-stateful returns the correct response

Out of scope:

- real POST /webhook
- real WhatsApp sending
- Google Sheets adapter
- Doctor WhatsApp Notification Adapter
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

## Validation target

Run targeted tests first, then full suite:

pytest tests/test_stateful_appointment_context_carryover.py tests/test_stateful_appointment_request_wiring.py tests/test_state_machine.py -q
pytest -q

Expected full suite:

206+ passed
