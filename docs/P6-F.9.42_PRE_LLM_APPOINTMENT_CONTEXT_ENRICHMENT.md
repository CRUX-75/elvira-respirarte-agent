# P6-F.9.42 — Pre-LLM Appointment Context Enrichment Architecture

## Status

PLANNED / SDD FIRST / NO RUNTIME CHANGES YET

## Context

During Swagger `/test/message-stateful` validation after P6-F.9.41, several appointment-flow bugs appeared around date, slot, and confirmation handling.

The most important finding is architectural:

> Appointment context is currently not consistently available before the conversational action is finalized.

This creates contradictions where deterministic context exists in the response payload, but the selected `next_action` and final user-facing response behave as if that context did not exist.

Example observed:

```json
{
  "mensaje_original": "quiero reservar una cita para el miercoles",
  "intent": "cita",
  "nuevo_estado": "ST_CITA_FECHA",
  "next_action": "ask_preferred_date",
  "fecha_solicitada": "2026-06-10",
  "fecha_solicitada_texto": "miércoles 10 de junio",
  "slots_candidatos": ["3:00 p. m.–5:00 p. m."]
}

This is invalid because Elvira already knows the requested date and available slot, but still asks the patient for the date again.

Diagnosis

This is not primarily a memory problem.

The issue is pipeline ordering:

Message arrives
→ patient state loaded
→ intent / state transition decides next_action
→ date/context may be resolved
→ LLM writes response
→ post-hoc guards try to repair context-specific cases
→ persistence decision runs

This causes the state machine and response layer to make decisions before having the full appointment context.

Desired Architecture

Appointment context must be enriched before the state machine finalizes next_action and before the LLM receives the state.

Target flow:

/webhook receives message
→ load patient state
→ load active appointment context
→ merge appointment context into ElviraState
→ sanitize input
→ resolve deterministic context:
    - requested date
    - requested date text
    - weekday
    - availability
    - candidate slots
    - exact-hour intent if present
    - matched slot/franja if exact hour falls inside a candidate slot
→ classify intent using enriched state
→ state machine decides next_state + next_action
→ appointment_request_decision runs from final state/action
→ LLM receives complete final state
→ response is generated
→ new context is captured
→ state/context/appointment request are persisted
→ response returned
Core Principle

The LLM must not decide or repair appointment state.

The LLM should only verbalize a final, already-consistent state.

Bugs Observed
BUG-1 — Embedded date ignored in initial appointment message

Patient:

quiero reservar una cita para el miercoles

System resolved:

fecha_solicitada = 2026-06-10
fecha_solicitada_texto = miércoles 10 de junio
slots_candidatos = ["3:00 p. m.–5:00 p. m."]

But response asked:

¿Para qué día le gustaría agendar su cita?

Invalid.

BUG-2 — Valid exact hour inside available slot triggers repetitive franja clarification

Patient, after date was selected:

A las 3

System had:

slots_candidatos = ["3:00 p. m.–5:00 p. m."]

But response asked again to choose a franja and did not persist an AppointmentRequest.

Invalid.

BUG-3 — Natural confirmation loses appointment context

Patient:

sí, regístrela

while in ST_CITA_FRANJA.

System classified it as general, responded as if no date existed, and did not persist.

Invalid if there is a valid pending appointment context.

BUG-4 — Post-hoc guards are accumulating

Current flow relies on special-case guards after state/action decisions. This makes the system difficult to reason about and increases regression risk.

State Invariants

These invariants must be enforced by tests.

INV-1

If fecha_solicitada != null and es_dia_disponible == true, final next_action must not be ask_preferred_date.

INV-2

If intent == cita and the current message contains a valid requested date, the flow must advance directly to time/slot handling.

INV-3

If estado_actual == ST_CITA_FRANJA, fecha_solicitada != null, slots_candidatos is not empty, and the patient gives an exact hour inside one candidate slot, the system must map that hour to the matching franja and persist an AppointmentRequest.

INV-4

If there is only one candidate slot and the patient gives a natural confirmation such as sí, ok, me sirve, or regístrela, the system must persist the request instead of restarting the date flow.

INV-5

The LLM must never receive a contradictory final state such as:

next_action = ask_preferred_date
fecha_solicitada != null
slots_candidatos not empty
INV-6

If fecha_solicitada resolves to weekend or Colombian holiday, the system must keep ST_CITA_FECHA, set next_action=ask_preferred_date, and not offer slots.

Scope

Allowed files for initial audit and implementation:

app/main.py
app/graph/state.py
app/graph/nodes.py
app/services/date_resolver.py
app/services/llm.py
app/services/appointment_request_service.py
tests/test_state_machine.py
tests/test_llm_date_context.py
tests/test_appointment_request_service.py
tests/test_main.py or endpoint/stateful tests if present
AI_CONTEXT.md
Out of Scope

Do not touch:

WhatsApp real sending
Production DB data
Google Sheets
Telegram
n8n
Calendar
Campaigns
Colombian production number
Doctor confirmation automation
Therapy sessions module

WHATSAPP_SENDING_ENABLED must remain false.

Debugging Plan
Phase A — Pipeline Audit

Run:

grep -R "appointment_context\|load.*context\|restore.*context\|node_resolve_date_context\|node_transition_state\|process_message\|appointment_request_decision\|ask_preferred_date\|ask_preferred_time\|generate.*response\|llm" -n app tests

Then inspect:

sed -n '1,280p' app/main.py
sed -n '1,340p' app/graph/nodes.py
sed -n '1,280p' app/graph/state.py

Goal:

Find the exact order of:

state loading
context restoration
date resolution
intent classification
state transition
LLM response generation
appointment request decision
state persistence
Phase B — Contract Tests

Before runtime refactor, add tests proving the broken contracts:

Initial appointment message with embedded date must not ask for date again.
Exact hour inside candidate slot must persist AppointmentRequest.
Natural confirmation in ST_CITA_FRANJA with single slot must persist.
No final state contradiction: ask_preferred_date with resolved valid date.
Phase C — Pipeline Refactor

Move appointment/date/hour context enrichment before final next_action decision.

Preferred direction:

load previous state/context
→ enrich current state with previous appointment context
→ resolve current message deterministic context
→ classify intent
→ transition state using enriched context
→ decide appointment request persistence
→ LLM response
→ persist
Phase D — Remove or De-emphasize Post-Hoc Guards

Only after tests are green.

Do not remove guards blindly. First prove that the enriched pipeline makes them unnecessary.

Acceptance Criteria

The block is complete only when all of the following pass:

Automated tests
pytest -q
Conversational E2E validation through /test/message-stateful
Flow 1 — Embedded date
Paciente: quiero reservar una cita para el miercoles

Expected:

fecha_solicitada = 2026-06-10
fecha_solicitada_texto = miércoles 10 de junio
nuevo_estado != ST_CITA_FECHA if the date is available
next_action != ask_preferred_date
response does not ask "¿Para qué día?"
Flow 2 — Date then exact hour
Paciente: Quiero pedir una cita
Paciente: El miércoles
Paciente: A las 3

Expected:

"A las 3" maps to "3:00 p. m.–5:00 p. m."
nuevo_estado = ST_CITA_PENDIENTE
next_action = confirm_appointment_request
appointment_request_decision.should_persist = true
appointment_request != null
Flow 3 — Natural confirmation
Paciente: Quiero pedir una cita
Paciente: El miércoles
Paciente: sí, regístrela

Expected if there is one candidate slot:

appointment_request_decision.should_persist = true
appointment_request != null
Flow 4 — Weekend / holiday guard
Paciente: Quiero pedir una cita para el domingo

Expected:

nuevo_estado = ST_CITA_FECHA
next_action = ask_preferred_date
appointment_request = null
slots_candidatos = []
Notes

This block is architectural. Avoid fixing only the visible copy.

The main goal is to make the appointment flow deterministic, predictable, and testable before the LLM writes the final message.
