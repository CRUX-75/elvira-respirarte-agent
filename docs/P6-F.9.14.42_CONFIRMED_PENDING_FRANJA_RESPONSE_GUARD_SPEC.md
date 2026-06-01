# P6-F.9.14.42 — Confirmed Pending Franja Response Guard

## Status

SPEC CREATED

## Reason

P6-F.9.14.41 validated that explicit confirmation after an exact-hour franja clarification now works technically.

Flow validated:

1. `Quiero pedir una cita`
2. `para maniana`
3. `se puede a las 3?`
4. `si`

Technical result:

- `si` was correctly interpreted as confirmation of the pending exact-hour franja.
- `intent = hora_cita`
- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- `state_reason = confirmed_pending_exact_hour_franja`
- `appointment_request_decision.should_persist = true`
- `appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review`
- `appointment_request` was created correctly.
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `persisted_state = ST_CITA_PENDIENTE`

However, the final response was wrong.

Observed response:

`Hola, qué gusto saludarle. ¿En qué le podemos ayudar hoy en Respirarte?`

## Root Cause

The response was likely generated before deterministic pending-franja confirmation correction.

Sequence:

1. `process_message` initially treats `si` as general.
2. A generic greeting response is generated.
3. `apply_pending_exact_hour_confirmation_to_state(...)` later corrects the state.
4. AppointmentRequest persistence succeeds.
5. `result.respuesta` remains the old generic response.

## Product Rule

When the patient explicitly confirms a pending exact-hour franja and the system creates the AppointmentRequest, Elvira must send the doctor-approved terminal message.

Approved response:

`Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

## Required Runtime Behavior

When:

- `appointment_request_decision.should_persist is True`
- `result.state_reason == "confirmed_pending_exact_hour_franja"`

then before `logged_response`, `save_interaction()`, and response return, force:

- `result.respuesta = "Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención."`

## Acceptance Criteria

The controlled `/test/message-stateful` flow:

1. `Quiero pedir una cita`
2. `para maniana`
3. `se puede a las 3?`
4. `si`

must end with:

- `appointment_request_decision.should_persist = true`
- `appointment_request != null`
- `persisted_state = ST_CITA_PENDIENTE`
- `respuesta = Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

It must not return:

- `Hola, qué gusto saludarle...`
- `¿En qué le podemos ayudar hoy...?`

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
