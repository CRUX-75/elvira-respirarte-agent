# P6-F.9.14.45 — Controlled Swagger Unavailable Date Dry-Run

## Status

CLOSED / GREEN / PRODUCTION VALIDATED

## Objective

Validate in production through `POST /test/message-stateful` only that an unavailable resolved appointment date does not advance the patient to slot selection.

Real `/webhook` was not touched.

Real WhatsApp sending remained disabled.

## Endpoint

POST /test/message-stateful

## Test Patient

telefono:

test-p6f91445a

nombre:

Paciente Test Unavailable Date

## Sequence Validated

1. Quiero pedir una cita
2. para el lunes

## Production Context

fecha_actual_colombia:

2026-06-01

The phrase `para el lunes` resolved to:

2026-06-08

That date is a Colombia holiday:

Corpus Christi

## Result — Step 1

Input:

Quiero pedir una cita

Validated:

- intent = cita
- nuevo_estado = ST_CITA_FECHA
- next_action = ask_preferred_date
- persisted_state = ST_CITA_FECHA
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = skipped_initial_cita_intent
- appointment_request = null
- delivery_status = sending_skipped

Validated response:

Claro, con muchísimo gusto. Le cuento que las atenciones domiciliarias se manejan solamente en la tarde, normalmente en dos franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Para qué día le gustaría agendar su cita?

## Result — Step 2

Input:

para el lunes

Validated:

- intent = fecha_cita
- fecha_solicitada = 2026-06-08
- fecha_solicitada_texto = lunes 8 de junio
- dia_semana_solicitado = lunes
- is_weekend = false
- is_colombia_holiday = true
- colombia_holiday_name = Corpus Christi
- es_dia_disponible = false
- slots_candidatos = []
- nuevo_estado = ST_CITA_FECHA
- next_action = ask_preferred_date
- state_reason = unavailable_date_guard
- persisted_state = ST_CITA_FECHA
- appointment_request_decision.should_persist = false
- appointment_request = null
- delivery_status = sending_skipped

Validated response:

Se refiere a lunes 8 de junio. Ese día no se atienden consultas porque corresponde al festivo de Corpus Christi. ¿Le gustaría indicarme otro día entre semana?

## Conclusion

P6-F.9.14.44 is validated in production through the safe stateful test endpoint.

Unavailable resolved dates no longer advance to:

- ST_CITA_FRANJA
- ask_preferred_time

Instead, the system correctly remains in:

- ST_CITA_FECHA
- ask_preferred_date
- unavailable_date_guard

No AppointmentRequest is created.

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
