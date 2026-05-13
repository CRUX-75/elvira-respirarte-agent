# P6-F-5 Dry-Run Validation

## Objective

Validate production dry-run behavior using the current test WhatsApp number while real sending remains disabled.

## Environment

- Environment: production
- App version: 0.2.1
- WhatsApp sending enabled: false
- KB runtime enabled: true
- LangSmith project: elvira-respirarte-prod
- Test number: current WhatsApp test number

## Test message

"Hola buenas, podria saber con quien hablo? Y que servicios ofrecen"

## Result

- Intent: servicios
- Previous state: ST_CITA_FRANJA
- New state: ST_CITA_FRANJA
- Next action: answer_services
- KB used: true
- KB sources: kb_services
- Delivery status: sending_skipped
- WhatsApp message ID: stored
- LangSmith trace: visible in elvira-respirarte-prod

## Decision

P6-F-5 dry-run validation is approved for the current test number.

Real sending remains disabled.


---

# P6-F.8 Production Dry-Run Validation

## Objective

Validate the new appointment request containment logic in production while real WhatsApp sending remains disabled.

This validation confirms that Elvira:

- preserves stateful appointment flow
- resolves relative dates into absolute patient-facing dates
- presents valid afternoon preference windows
- blocks non-operational Sunday requests
- no longer misclassifies `El domingo` as a generic schedule question inside the appointment flow

## Environment

- Environment: production
- App version: 0.2.1
- WhatsApp sending enabled: false
- KB runtime enabled: true
- LangSmith project: `elvira-respirarte-prod`
- Test endpoint: `/test/message-stateful`
- Runtime DB state: PostgreSQL production persistence active

## Validation 1 — Open appointment flow

### Input

```json
{
  "telefono": "573001112673",
  "mensaje": "Quiero pedir una cita",
  "nombre": "Paciente Prueba",
  "estado_actual": "ST_INIT",
  "opt_out": false
}
Result
Previous state: ST_GENERAL
New state: ST_CITA_FECHA
Intent: cita
Next action: ask_preferred_date
Persisted state: ST_CITA_FECHA
Delivery status: sending_skipped
Response
Claro, con gusto le ayudamos a coordinar la cita. ¿Para qué día le gustaría agendarla?
Validation 2 — Relative date request: Mañana
Input
{
  "telefono": "573001112673",
  "mensaje": "Mañana",
  "nombre": "Paciente Prueba",
  "estado_actual": "ST_INIT",
  "opt_out": false
}
Result
Previous state: ST_CITA_FECHA
New state: ST_CITA_FRANJA
Intent: fecha_cita
Next action: ask_preferred_time
fecha_solicitada: 2026-05-14
fecha_solicitada_texto: jueves 14 de mayo
is_weekend: false
is_colombia_holiday: false
Candidate slots:
3:00 p. m.–5:00 p. m.
5:00 p. m.–7:00 p. m.
Persisted state: ST_CITA_FRANJA
Delivery status: sending_skipped
Response
Perfecto, se refiere a mañana, jueves 14 de mayo. La doctora solo atiende consultas domiciliarias en la tarde. Para ese día tengo disponibles entre 3:00 p. m. y 5:00 p. m. o entre 5:00 p. m. y 7:00 p. m. ¿Cuál le sirve mejor?
Validation 3 — Sunday request bugfix: El domingo
Observed issue before fix

Inside ST_CITA_FECHA, the message:

El domingo

was incorrectly classified as:

Intent: horarios
Next action: answer_schedule

This prevented the contained appointment-date response from executing.

Fix applied

The contextual appointment-date classifier was updated so that weekday references with or without the article el, including domingo, are classified as fecha_cita inside appointment date states.

Production validation after fix
Input
{
  "telefono": "573001112674",
  "mensaje": "El domingo",
  "nombre": "Paciente Domingo",
  "estado_actual": "ST_INIT",
  "opt_out": false
}
Result
Previous state: ST_CITA_FECHA
New state: ST_CITA_FRANJA
Intent: fecha_cita
Next action: ask_preferred_time
fecha_solicitada: 2026-05-17
fecha_solicitada_texto: domingo 17 de mayo
is_weekend: true
is_colombia_holiday: false
Candidate slots: none
Persisted state: ST_CITA_FRANJA
Delivery status: sending_skipped
Response
Se refiere a domingo 17 de mayo. Ese día no se atienden consultas. ¿Le gustaría indicarme otro día entre semana?
Production KB cleanup verified after P6-F.8

The production runtime KB was cleaned in PostgreSQL after validation:

HOR-05 Teleconsulta removed
HOR-03 Saturday note simplified
RULE-003 teleconsulta removed
RULE-007 appointment_confirmation removed
RULE-008 appointment_slot_policy updated to present candidate preference windows without confirming the appointment
Decision

P6-F.8 production dry-run validation is approved.

The appointment request containment layer is production-validated with real sending still disabled.

Real WhatsApp sending remains blocked until the next operational handoff layer is completed and validated:

appointment request persistence
Solicitudes_Cita
human review by Dra. D'Aleman
