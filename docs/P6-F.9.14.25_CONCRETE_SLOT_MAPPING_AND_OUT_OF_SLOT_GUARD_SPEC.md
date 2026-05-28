# P6-F.9.14.25 — Concrete Slot Mapping & Out-of-Slot Guard SPEC

## Status

SPEC CREATED

## Problem

Production Swagger validation showed that when the patient says:

`se puede a las 5?`

after Elvira has offered:

- 3:00 p. m.–5:00 p. m.
- 5:00 p. m.–7:00 p. m.

the system persists:

`franja_solicitada = 3:00 p. m.–5:00 p. m.`

instead of:

`franja_solicitada = 5:00 p. m.–7:00 p. m.`

## Root Cause

The runtime decision currently falls back blindly to the first candidate slot:

`franja_solicitada = slots[0] if slots else None`

This is unsafe because the patient may have clearly selected the second visible slot.

## Objective

Implement deterministic slot mapping before AppointmentRequest persistence.

The system must map concrete patient expressions to one of the visible offered slots.

## Valid Slot Mapping

The following expressions must map to:

`3:00 p. m.–5:00 p. m.`

Examples:

- A las 3
- se puede a las 3?
- a las tres
- de 3 a 5
- la primera
- el primer horario
- la primera franja

The following expressions must map to:

`5:00 p. m.–7:00 p. m.`

Examples:

- A las 5
- se puede a las 5?
- a las cinco
- de 5 a 7
- la segunda
- el segundo horario
- la segunda franja

## Out-of-Slot Guard

Unsupported loose hours must not be accepted.

Examples:

- se puede a las 4?
- se puede a las 6?
- a las 2
- a las 7
- a las 10

Expected behavior:

- do not default to the first slot
- do not persist AppointmentRequest
- keep the flow in slot-selection mode
- ask the patient to choose one of the offered franjas

## Product Rule

The system works with visible appointment franjas, not arbitrary exact hours inside a franja.

Even if `4` is technically inside `3:00 p. m.–5:00 p. m.`, it must not be interpreted as a valid slot selection.

## Expected Copy

For unsupported loose hours, Elvira should answer:

`Por ahora solo puedo registrar su preferencia dentro de estas dos franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Cuál de las dos le queda mejor?`

## Implementation Direction

Add a deterministic helper near:

`app/services/appointment_request_runtime.py`

Possible helper:

`resolve_requested_slot_from_message(message, slots)`

The helper should return:

- selected slot string when mapping is valid
- None when the message is ambiguous or unsupported

Remove the blind fallback:

`franja_solicitada = slots[0] if slots else None`

## Tests First

Add RED tests in:

`tests/test_appointment_request_runtime_decision.py`

Test groups:

1. first slot concrete mapping
2. second slot concrete mapping
3. ordinal slot mapping
4. unsupported loose hours blocked
5. no fallback to first slot

## Safety Boundaries

Do not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

