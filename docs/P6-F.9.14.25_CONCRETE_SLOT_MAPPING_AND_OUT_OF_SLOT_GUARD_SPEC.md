# P6-F.9.14.25 — Concrete Slot Mapping & Out-of-Slot Guard SPEC

## Status

SPEC CREATED

## Problem

Production Swagger dry-run showed that a concrete patient message:

`se puede a las 5?`

was persisted with the wrong slot:

Observed:

`franja_solicitada = 3:00 p. m.–5:00 p. m.`

Expected:

`franja_solicitada = 5:00 p. m.–7:00 p. m.`

## Root cause

The current AppointmentRequest persistence decision uses the first candidate slot as fallback:

`franja_solicitada = slots[0] if slots else None`

This is unsafe when multiple candidate slots exist.

## Required behavior

When multiple candidate slots exist, the system must map concrete patient selections to the correct offered slot.

### Valid first-slot selections

These should map to:

`3:00 p. m.–5:00 p. m.`

Examples:

- `A las 3`
- `se puede a las 3?`
- `a las tres`
- `de 3 a 5`
- `la primera`
- `el primer horario`

### Valid second-slot selections

These should map to:

`5:00 p. m.–7:00 p. m.`

Examples:

- `A las 5`
- `se puede a las 5?`
- `a las cinco`
- `de 5 a 7`
- `la segunda`
- `el segundo horario`

## Out-of-slot guard

If the patient gives another specific hour that is not one of the offered slot starts or slot labels, the system must not persist an AppointmentRequest.

Examples:

- `se puede a las 4?`
- `se puede a las 6?`
- `a las 2`
- `a las 7`
- `a las 10`

Expected behavior:

- do not persist AppointmentRequest
- return a deterministic skip reason
- keep the flow asking the patient to choose one of the offered concrete franjas

## Important product decision

Even if a time like `4` is inside the `3:00 p. m.–5:00 p. m.` range, it must not be interpreted as a valid selection.

The patient must choose one of the visible offered franjas, not a loose hour inside the range.

## Scope

This block focuses on deterministic persistence decision and slot mapping.

Do not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

## Expected implementation direction

Create a deterministic helper near AppointmentRequest runtime decision logic.

Possible helper:

`resolve_requested_slot_from_message(message, slots)`

Expected outcomes:

- selected slot string when the message clearly maps to an offered slot
- `None` when the message is unclear, unsupported, or outside offered slots

AppointmentRequest persistence must not default blindly to `slots[0]` when multiple slots exist.

