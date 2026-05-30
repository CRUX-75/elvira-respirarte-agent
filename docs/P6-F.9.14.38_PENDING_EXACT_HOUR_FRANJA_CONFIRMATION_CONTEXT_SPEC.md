# P6-F.9.14.38 — Pending Exact-Hour Franja Confirmation Context

## Status

SPEC CREATED

## Reason

P6-F.9.14.37 showed that after Elvira asks the patient to confirm a franja derived from an exact-hour question, the next patient reply `si` is classified as general.

Observed production behavior:

1. Patient asks: `se puede a las 5?`
2. Runtime correctly returns:
   - nuevo_estado = ST_CITA_FRANJA
   - next_action = ask_confirm_exact_hour_as_slot
   - appointment_request_decision.reason = requires_exact_hour_franja_confirmation
   - appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
   - appointment_request = null
3. Patient replies: `si`
4. Runtime incorrectly returns:
   - intent = general
   - next_action = answer_general
   - appointment_request_decision.reason = skipped_non_appointment_intent
   - appointment_request = null

## Root Cause

The system does not persist pending exact-hour confirmation context.

The existing `appointment_context` only stores:

- fecha_solicitada
- fecha_solicitada_texto
- slots_candidatos
- availability flags

It does not store:

- pending_exact_hour_franja
- pending_exact_hour_text
- pending_exact_hour_requires_confirmation

Therefore the next patient reply cannot be interpreted deterministically as confirmation of the proposed franja.

## Product Rule

When Elvira asks:

`¿Desea que registremos su solicitud para esa franja?`

and the patient replies affirmatively, the system must treat that reply as confirmation of the pending franja, not as a generic message.

## Required Context Shape

When the decision reason is:

`requires_exact_hour_franja_confirmation`

the runtime must persist appointment context containing:

{
  "fecha_solicitada": "2026-06-01",
  "fecha_solicitada_texto": "lunes 1 de junio",
  "slots_candidatos": [
    "3:00 p. m.–5:00 p. m.",
    "5:00 p. m.–7:00 p. m."
  ],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null,
  "pending_exact_hour_franja": "5:00 p. m.–7:00 p. m.",
  "pending_exact_hour_text": "se puede a las 5?",
  "pending_exact_hour_requires_confirmation": true
}

## Required Confirmation Behavior

When:

- patient estado_actual == ST_CITA_FRANJA
- appointment_context.pending_exact_hour_requires_confirmation == true
- appointment_context.pending_exact_hour_franja is present
- patient message is an affirmative confirmation

Examples:

- si
- sí
- claro
- de acuerdo
- listo
- está bien
- esta bien
- correcto

Then the runtime must force the current state to:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- fecha_solicitada = appointment_context.fecha_solicitada
- franja_solicitada/context slot = appointment_context.pending_exact_hour_franja

And AppointmentRequest persistence must be allowed.

## Required Persistence Behavior

After affirmative confirmation:

- appointment_request_decision.should_persist = true
- appointment_request_decision.fecha_solicitada = stored fecha_solicitada
- appointment_request_decision.franja_solicitada = stored pending_exact_hour_franja
- appointment_request should be created
- persisted_state = ST_CITA_PENDIENTE
- appointment_context should be cleared after persistence

## Out of Scope

Do not touch:

- real POST /webhook
- WhatsApp sending
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
4. si

must end with:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- appointment_request_decision.should_persist = true
- appointment_request_decision.fecha_solicitada = 2026-06-01
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request != null
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.franja_solicitada = 5:00 p. m.–7:00 p. m.
- persisted_state = ST_CITA_PENDIENTE
- delivery_status = sending_skipped
