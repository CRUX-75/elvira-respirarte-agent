# P6-F.9.14.35 — Exact-Hour Franja Confirmation State Guard

## Status

SPEC CREATED

## Reason

The controlled Swagger dry-run P6-F.9.14.34 validated that exact-hour franja mapping and AppointmentRequest persistence blocking work correctly.

However, a state advancement bug was found.

When the patient asked:

`se puede a las 5?`

after Elvira had offered:

- 3:00 p. m.–5:00 p. m.
- 5:00 p. m.–7:00 p. m.

the runtime correctly produced:

- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request = null

But the endpoint still persisted:

- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- persisted_state = ST_CITA_PENDIENTE

This is unsafe because the patient has not explicitly confirmed that the proposed franja should be registered.

## Product Rule

When the patient asks for a loose exact hour that falls inside a visible KB-backed franja, Elvira must:

1. explain that care is handled by franjas, not guaranteed exact hours
2. propose the matching franja
3. ask the patient for explicit confirmation
4. not persist an AppointmentRequest yet
5. not advance to ST_CITA_PENDIENTE yet

## Required Runtime Behavior

When:

appointment_request_decision.reason == "requires_exact_hour_franja_confirmation"

Then before logging, interaction persistence, and patient state update, force:

- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_confirm_exact_hour_as_slot
- persisted_state = ST_CITA_FRANJA
- appointment_request = null

The response may still explain the exact-hour/franja rule and ask for confirmation.

## Required Context Behavior

The runtime should preserve the pending franja confirmation context so the next patient message can confirm it.

Recommended appointment_context fields:

- pending_exact_hour_franja
- pending_exact_hour_text
- pending_exact_hour_requires_confirmation

Example:

{
  "pending_exact_hour_franja": "5:00 p. m.–7:00 p. m.",
  "pending_exact_hour_text": "se puede a las 5?",
  "pending_exact_hour_requires_confirmation": true
}

## Out of Scope

Do not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

## Acceptance Criteria

A controlled `/test/message-stateful` flow:

1. Quiero pedir una cita
2. Para el lunes
3. se puede a las 5?

must return:

- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request = null
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_confirm_exact_hour_as_slot
- persisted_state = ST_CITA_FRANJA
- delivery_status = sending_skipped

It must not return:

- persisted_state = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- appointment_request created
