# P6-F.9.14.46 — Post-Unavailable-Date Recovery Flow Dry-Run

## Status

CLOSED / GREEN / PRODUCTION VALIDATED

## Objective

Validate in production through `POST /test/message-stateful` only that after an unavailable appointment date is rejected, the patient can continue with a valid date and complete the request flow.

Real `/webhook` was not touched.

Real WhatsApp sending remained disabled.

## Endpoint

POST /test/message-stateful

## Test Patient

telefono:

test-p6f91446a

nombre:

Paciente Test Recovery Flow

## Production Context

fecha_actual_colombia:

2026-06-01

## Sequence Validated

1. Quiero pedir una cita
2. para el lunes
3. entonces para el martes
4. a las 3
5. si

## Result — Step 1

Input:

Quiero pedir una cita

Validated:

- intent = cita
- nuevo_estado = ST_CITA_FECHA
- next_action = ask_preferred_date
- persisted_state = ST_CITA_FECHA
- appointment_request = null
- delivery_status = sending_skipped

## Result — Step 2

Input:

para el lunes

Resolved date:

- fecha_solicitada = 2026-06-08
- fecha_solicitada_texto = lunes 8 de junio
- dia_semana_solicitado = lunes
- is_colombia_holiday = true
- colombia_holiday_name = Corpus Christi
- es_dia_disponible = false
- slots_candidatos = []

Validated behavior:

- intent = fecha_cita
- nuevo_estado = ST_CITA_FECHA
- next_action = ask_preferred_date
- state_reason = unavailable_date_guard
- persisted_state = ST_CITA_FECHA
- appointment_request = null
- delivery_status = sending_skipped

Validated response:

Se refiere a lunes 8 de junio. Ese día no se atienden consultas porque corresponde al festivo de Corpus Christi. ¿Le gustaría indicarme otro día entre semana?

## Result — Step 3

Input:

entonces para el martes

Resolved date:

- fecha_solicitada = 2026-06-02
- fecha_solicitada_texto = martes 2 de junio
- dia_semana_solicitado = martes
- is_weekend = false
- is_colombia_holiday = false
- es_dia_disponible = true
- slots_candidatos:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.

Validated behavior:

- intent = fecha_cita
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_preferred_time
- persisted_state = ST_CITA_FRANJA
- appointment_request = null
- delivery_status = sending_skipped

Conclusion:

The patient is not stuck after the unavailable date guard. A new valid date continues the appointment flow correctly.

## Result — Step 4

Input:

a las 3

Validated behavior:

- intent = hora_cita
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_confirm_exact_hour_as_slot
- state_reason = requires_exact_hour_franja_confirmation
- fecha_solicitada = 2026-06-02
- franja_solicitada = null
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 3:00 p. m.–5:00 p. m.
- appointment_request = null
- persisted_state = ST_CITA_FRANJA

Validated response:

Con gusto. Le cuento que la atención se maneja por franjas horarias y no es posible garantizar una hora exacta dentro del bloque. Para esa hora, la franja correspondiente sería de 3:00 p. m. a 5:00 p. m.. ¿Desea que registremos su solicitud para esa franja?

Known minor copy issue:

There is a double period after `p. m..`.

This is not blocking and can be handled in a later copy polish microblock.

## Result — Step 5

Input:

si

Validated behavior:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- state_reason = confirmed_pending_exact_hour_franja
- fecha_solicitada = 2026-06-02
- fecha_solicitada_texto = martes 2 de junio
- franja_solicitada = 3:00 p. m.–5:00 p. m.
- appointment_request_decision.should_persist = true
- appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review
- appointment_request_decision.estado_solicitud = pendiente_confirmacion
- appointment_request created
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.fecha_solicitada = 2026-06-02
- appointment_request.franja_solicitada = 3:00 p. m.–5:00 p. m.
- persisted_state = ST_CITA_PENDIENTE
- delivery_status = sending_skipped

Validated response:

Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.

## Conclusion

The post-unavailable-date recovery flow is production validated.

The system correctly handles:

1. unavailable resolved date
2. recovery with a valid date
3. slot offering
4. exact-hour-to-franja confirmation
5. final AppointmentRequest persistence for human review

## Safety Boundaries Preserved

Not touched:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking
