# P6-F.9.14.23 — Slot Selection Precision Guard SPEC

## Status

SPEC CREATED

## Problem

After Elvira offers multiple concrete appointment slots, a generic patient reply such as:

- En la tarde
- Por la tarde
- Tarde

must not automatically select the first available slot.

This is unsafe because the patient has not chosen a concrete slot.

## Example unsafe flow

Elvira offers:

- 3:00 p. m.–5:00 p. m.
- 5:00 p. m.–7:00 p. m.

Patient replies:

En la tarde

Current risk:

The system may interpret this as `hora_cita`, move to `ST_CITA_PENDIENTE`, and persist an AppointmentRequest using the first slot.

## Desired behavior

When the patient is in `ST_CITA_FRANJA`, multiple candidate slots exist, and the patient reply is generic afternoon wording, the system must:

- remain in `ST_CITA_FRANJA`
- not move to `ST_CITA_PENDIENTE`
- not use `confirm_appointment_request`
- not persist an AppointmentRequest
- ask the patient to choose one of the concrete offered slots

## Generic ambiguous slot replies

The first guard covers:

- en la tarde
- por la tarde
- tarde

These are ambiguous when multiple afternoon slots exist.

## Valid concrete selections

The system may continue to accept concrete selections such as:

- A las 3
- A las 5
- De 3 a 5
- De 5 a 7
- La primera
- La segunda
- El primer horario
- El segundo horario

Concrete slot selection behavior may remain as currently implemented if already working.

## Boundary

This block must not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

## Implementation direction

Prefer a deterministic guard close to state transition / graph node behavior.

The intent classifier may still classify generic afternoon wording in `ST_CITA_FRANJA` as `hora_cita`.

However, the state machine or graph layer must prevent advancing to `ST_CITA_PENDIENTE` when the reply is ambiguous and multiple slots exist.

## Expected response behavior

Elvira should ask something similar to:

Para continuar, por favor elija una de las franjas disponibles: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Cuál le queda mejor?

The exact copy can be protected in tests if implemented deterministically.

## Validation target

Add RED tests first for:

1. `En la tarde` in `ST_CITA_FRANJA` with two slots stays in `ST_CITA_FRANJA`.
2. `En la tarde` with two slots does not set `next_action = confirm_appointment_request`.
3. `En la tarde` with two slots does not allow AppointmentRequest persistence.
4. Concrete selection such as `A las 3` still reaches `ST_CITA_PENDIENTE`.
5. Existing full suite remains green.

