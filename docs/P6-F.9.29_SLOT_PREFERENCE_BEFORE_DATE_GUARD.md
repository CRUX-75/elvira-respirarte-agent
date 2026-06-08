# P6-F.9.29 — Slot Preference Before Date Guard

## Status

CLOSED / RED-THEN-GREEN / GREEN / READY TO COMMIT

## Reason

During P6-F.9.28 controlled real WhatsApp sending, a real conversational bug was found.

The patient was already inside the appointment flow:

- estado_actual = ST_CITA_FECHA

The patient then sent:

- Para la de las 5

Observed behavior:

- intent = general
- next_action = answer_general
- nuevo_estado = ST_CITA_FECHA
- Elvira answered with a new greeting: "Hola..."

This was safe from a persistence perspective, but incorrect conversationally.

The patient was not starting a new general conversation. They were expressing a slot/time preference before providing the missing appointment date.

## Expected Behavior

When:

- estado_actual = ST_CITA_FECHA
- the patient mentions a slot or hour preference without giving a date

Elvira must:

- classify the message as hora_cita
- remain in ST_CITA_FECHA
- not create AppointmentRequest
- not advance to ST_CITA_PENDIENTE
- not greet again
- ask for the missing day/date

## Approved Copy

For second slot preference:

Claro, con gusto. ¿Me indica por favor para qué día o fecha desea revisar la franja de 5:00 p. m. a 7:00 p. m.?

For first slot preference:

Claro, con gusto. ¿Me indica por favor para qué día o fecha desea revisar la franja de 3:00 p. m. a 5:00 p. m.?

## Implementation

Changed files:

- app/services/intent.py
- app/graph/transitions.py
- app/services/llm.py
- tests/test_intent.py
- tests/test_state_machine.py

### Intent Routing

Slot/hour preference expressions inside ST_CITA_FECHA now classify as:

- hora_cita

Examples:

- Para la de las 5
- Para la de las 3
- La de las 5

### State Transition

If:

- previous_state = ST_CITA_FECHA
- intent = hora_cita

Then:

- nuevo_estado = ST_CITA_FECHA
- next_action = ask_date_for_slot_preference
- state_reason = slot_preference_before_date_guard

### Response Layer

New response action:

- ask_date_for_slot_preference

This action asks for the missing date without greeting again.

## Tests

Added/updated tests:

- tests/test_intent.py
- tests/test_state_machine.py

Protected cases:

- Para la de las 5 in ST_CITA_FECHA
- Para la de las 3 in ST_CITA_FECHA
- La de las 5 in ST_CITA_FECHA

## Validation

Targeted tests:

GREEN

Full suite:

pytest -q

Result:

220 passed

## Safety Boundaries Preserved

Not touched:

- real /webhook activation logic
- WhatsApp Cloud API configuration
- WHATSAPP_SENDING_ENABLED
- EasyPanel environment
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- AppointmentRequest persistence rules
- therapy sessions module

## Production Follow-Up

Real sending remains disabled after P6-F.9.28 rollback.

Before another controlled real sending test, deploy this fix and verify through safe dry-run or controlled WhatsApp internal phone only.

## Conclusion

The bug found during controlled real sending has been fixed locally.

Elvira now keeps conversational continuity when a patient mentions a preferred slot before providing the appointment date.
