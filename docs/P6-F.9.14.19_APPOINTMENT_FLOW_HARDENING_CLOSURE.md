# P6-F.9.14.19 — Appointment Flow Hardening: Relative Dates, Time Windows & Clarification Guards

## Status

CLOSED / RED-THEN-GREEN / GREEN

## Validation

Targeted validation:

```bash
pytest tests/test_date_resolver.py tests/test_intent.py tests/test_state_machine.py -q

Result:

43 passed

Full suite validation:

pytest -q

Result:

196 passed
Problem

Production Swagger validation showed that the appointment flow could advance too aggressively when the patient used relative date and time-window phrases.

Unsafe example:

Maniana en la tarde

Observed risk:

intent could be routed incorrectly
fecha_solicitada could remain null
the flow could move to ST_CITA_FRANJA without a resolved date
responses could include vague wording such as "la fecha indicada"

This was unsafe because Elvira could enter an operational appointment state without a deterministic appointment date.

Implemented Hardening
1. Relative date typo support

The deterministic date resolver now supports patient typo/transliteration variants such as:

mañana
manana
maniana
pasado mañana
pasado manana
pasado maniana

Important distinction:

Maniana en la tarde

is treated as tomorrow + afternoon.

But:

En la maniana

is treated as morning time window without a date.

It must not be interpreted as tomorrow.

2. Intent routing hardening

The intent classifier now keeps appointment clarification questions inside appointment context.

Examples:

Cual fecha indicada?
Cuál fecha indicada?
Qué fecha indicada?
No entendí
Qué quiere decir?

These are routed as appointment-date context instead of falling back to general.

3. State guard against missing fecha_solicitada

A deterministic guard was added in the graph date resolution node.

If:

intent == fecha_cita
nuevo_estado == ST_CITA_FRANJA
fecha_solicitada is missing

then the flow is forced back to:

nuevo_estado = ST_CITA_FECHA
next_action = ask_preferred_date
state_reason = missing_fecha_solicitada_guard

This prevents the system from entering ST_CITA_FRANJA without a resolved date.

4. Safer response wording

The response layer no longer falls back to the unsafe wording:

la fecha indicada

The ask_preferred_date response now clarifies:

Claro, me refiero a la fecha de la cita. ¿Para qué día le gustaría agendarla?

This avoids vague references when no deterministic date exists.

Files Changed
app/services/date_resolver.py
app/services/intent.py
app/graph/nodes.py
app/services/llm.py
tests/test_date_resolver.py
tests/test_intent.py
tests/test_state_machine.py
Safety Boundaries Preserved

Still not touched:

POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
Calendar
doctor confirmation automation
therapy/session package tracking
Conclusion

P6-F.9.14.19 closes the unsafe appointment-flow gap where relative-date typos, time-window-only phrases, and clarification questions could cause ambiguous or premature appointment state transitions.

The appointment flow is now harder to break before moving toward further runtime/production validation.
