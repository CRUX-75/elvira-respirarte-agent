# P6-F.8 — Appointment Request Containment & Human Handoff

## Status

**Implemented and production-validated on 2026-05-13**

Current baseline after this block:

- `76 passed`
- Production validated with `WHATSAPP_SENDING_ENABLED=false`
- Stateful Swagger validation completed
- Runtime KB cleaned in PostgreSQL production
- Appointment flow remains human-reviewed, not calendar-automated

---

## 1. Why P6-F.8 was opened

Before this block, Elvira could still produce weak or misleading appointment responses in situations such as:

- “Mañana”
- “Pasado mañana en la mañana”
- a requested date landing on a Saturday or Sunday
- a requested date landing on a Colombian public holiday
- a patient expressing a morning preference when the Dra. D’Aleman only attends domiciliary consultations in the afternoon

The main risk was conversational overreach, for example:

- implying that availability could be reviewed for a non-operational day
- not repeating the resolved real date back to the patient
- offering language too close to scheduling or confirmation
- allowing the flow to drift toward a calendar-style automation that does not match Respirarte’s current business model

---

## 2. Product decision sealed in P6-F.8

### 2.1 Elvira does not schedule appointments

Elvira does **not**:

- confirm appointments
- reserve slots
- reject requests on behalf of the Dra. D’Aleman
- cancel appointments
- reschedule appointments
- manage a real clinical calendar
- claim real appointment availability

Elvira’s role is narrower and more reliable:

1. understand the patient’s appointment intent
2. resolve the requested date deterministically
3. validate whether that date is operationally admissible
4. present permitted afternoon slot preferences when applicable
5. prepare a clean appointment request for human review in the next subphase

---

## 3. Current business model reflected in the system

Respirarte is not operating today as a fully automated clinic with an open live calendar.

The real model is:

- Dra. D’Aleman attends patients in limited domiciliary afternoon windows
- the patient expresses a preferred date and time window
- the request must later be reviewed by the doctor
- only the doctor confirms the appointment

Therefore, the correct architecture for the current phase is:

```text
Patient WhatsApp message
        ↓
Elvira validates date and appointment preference
        ↓
Structured appointment request
        ↓
Google Sheets / Solicitudes_Cita  [next implementation block]
        ↓
Telegram notification to Dra. D’Aleman  [next implementation block]
        ↓
Doctor reviews and confirms or rejects manually
4. Calendar integration decision
4.1 No external calendar integration in the current phase

P6-F.8 resolves the earlier calendar dilemma.

Respirarte does not need Google Calendar, calendar booking APIs, or automated availability synchronization at this stage.

The current flow is better served by:

a structured Solicitudes_Cita operational table
a lightweight human approval path
later Telegram handoff for doctor review

This keeps the system lean and aligned with the real workflow.

4.2 What remains from the earlier calendar work

The internal appointment slot logic remains useful as deterministic business logic. It helps Elvira present the visible preference windows currently allowed by Respirarte.

This is not a real agenda and does not confirm availability.

5. Deterministic appointment containment implemented
5.1 Resolved date fields

The date resolver now enriches the flow with:

fecha_solicitada
fecha_solicitada_texto
dia_semana_solicitado
is_weekend
is_colombia_holiday
colombia_holiday_name
es_dia_disponible
slots_candidatos
5.2 Relative date handling

Elvira now resolves and repeats relative dates in patient-facing language.

Examples:

Paciente:
Quiero cita mañana.

Elvira:
Perfecto, se refiere a mañana, jueves 14 de mayo.
Paciente:
Pasado mañana en la mañana.

Elvira:
Perfecto, se refiere a pasado mañana, viernes 15 de mayo.

This avoids ambiguity and ensures the patient and the system are referring to the same absolute date.

6. Weekend and Colombian holiday handling
6.1 Weekends

The resolver deterministically flags Saturdays and Sundays.

Example:

Paciente:
El domingo.

Elvira:
Se refiere a domingo 17 de mayo. Ese día no se atienden consultas. ¿Le gustaría indicarme otro día entre semana?
6.2 Colombian public holidays 2026

The resolver now includes the official Colombian public holidays required for the 2026 appointment containment rules.

When a requested date matches a Colombian public holiday:

is_colombia_holiday = true
slots_candidatos = []
es_dia_disponible = false

Example:

Paciente:
Mañana.

If tomorrow is the holiday of Ascensión de Jesús:

Elvira:
Se refiere a mañana, lunes 18 de mayo. Ese día no se atienden consultas porque corresponde al festivo de Ascensión de Jesús. ¿Le gustaría indicarme otro día entre semana?
7. Afternoon appointment preference language

Respirarte currently supports domiciliary afternoon consultation windows.

7.1 Visible patient-facing slot preferences

For Monday, Tuesday, Thursday and Friday:

3:00 p. m. – 5:00 p. m.
5:00 p. m. – 7:00 p. m.

For Wednesday:

3:00 p. m. – 5:00 p. m.
7.2 Current valid response pattern

For a valid operational date, Elvira responds naturally and formally:

Perfecto, se refiere a mañana, jueves 14 de mayo. La doctora solo atiende consultas domiciliarias en la tarde. Para ese día tengo disponibles entre 3:00 p. m. y 5:00 p. m. o entre 5:00 p. m. y 7:00 p. m. ¿Cuál le sirve mejor?

This wording was intentionally selected because:

it sounds more natural than a generic robotic clarification
it gives the patient concrete options
it preserves the distinction between preference capture and appointment confirmation
it avoids implying that Elvira has confirmed a real booking
8. Formal patient treatment

A guardrail was reaffirmed and must remain stable:

Elvira addresses the patient in formal Spanish using usted, never tú.

Examples:

se refiere
¿Le gustaría...?
¿Cuál le sirve mejor?
La Dra. D’Aleman le confirmará la cita.
9. Booking-flow classifier correction

During production Swagger validation, a bug was detected:

9.1 Bug observed

Within ST_CITA_FECHA, the message:

El domingo

was incorrectly classified as:

intent = horarios

instead of:

intent = fecha_cita
9.2 Root cause

The contextual date pattern list recognized:

lunes
martes
miércoles
jueves
viernes
sábado

but did not adequately cover:

domingo
weekday mentions with or without the article el
9.3 Fix implemented

The date-context classifier was expanded so that, inside appointment date states, weekday mentions such as:

domingo
el domingo
lunes
el lunes

are treated as fecha_cita.

9.4 Production result after fix

Validated in Swagger:

"El domingo"

now produces:

intent = fecha_cita
nuevo_estado = ST_CITA_FRANJA
next_action = ask_preferred_time

and the expected contained response:

Se refiere a domingo 17 de mayo. Ese día no se atienden consultas. ¿Le gustaría indicarme otro día entre semana?
10. Knowledge Base cleanup completed

The production runtime KB was cleaned in PostgreSQL after P6-F.8 validation.

10.1 Removed obsolete schedule entry

Deleted:

HOR-05 Teleconsulta

Teleconsulta is not part of the current lean appointment request flow.

10.2 Updated schedule note

Updated:

HOR-03 Saturday note

Final version:

Sin servicio domiciliario los sábados.
10.3 Removed obsolete appointment rule

Deleted:

RULE-007 appointment_confirmation

This rule contained the outdated traffic / schedule-variability disclaimer that is no longer part of Elvira’s appointment request flow.

10.4 Removed obsolete teleconsultation rule

Deleted:

RULE-003 teleconsulta
10.5 Updated slot policy rule

Updated:

RULE-008 appointment_slot_policy

Current allowed action:

Presentar franjas candidatas sin confirmar cita

The rule now states that Elvira may present visible preference windows but does not confirm the appointment.

11. Test and production validation evidence
11.1 Test status

Final local baseline:

76 passed
11.2 Main behaviors covered

Tests now cover:

human-readable resolved relative dates
Sunday blocking
holiday blocking
Pasado mañana en la mañana
state propagation of new resolver fields
full graph flow from process_message
contextual bugfix for El domingo
11.3 Production validation completed

Validated through:

/ready
/test/message-stateful
production PostgreSQL runtime KB inspection via pgweb

Important production safety state:

WHATSAPP_SENDING_ENABLED=false
12. Next implementation block

The next logical block after P6-F.8 appointment containment is:

P6-F.9 — Appointment Request Persistence & Human Review Handoff

Expected scope:

define Solicitudes_Cita
register structured appointment requests only when:
date is valid
a supported slot preference has been selected
prepare Telegram notification to Dra. D’Aleman
keep the doctor as the final confirmer of the appointment

No real calendar integration is required for this phase.

13. Future scalability

The current architecture remains appropriate for future scale.

If Respirarte later evolves into a larger clinical operation with:

Dra. D’Aleman working full time
multiple specialists
higher appointment volume
operational staff
more formal patient follow-up

then the system can scale toward:

a real appointment database
provider availability tables
service-duration rules
operational queues
a clinical scheduling engine
Chatwoot or another inbox layer for human support and assignment
structured approval / rejection workflows
eventually a full internal scheduling platform

The current design does not block that future.

It deliberately avoids over-automation now while preserving a clean path to more robust clinical operations later.

14. Design principle reaffirmed

P6-F.8 reinforces an important product and architecture principle:

Not everything that can be automated should be automated immediately.

For Respirarte at this stage:

automation should structure
deterministic logic should protect
the LLM should phrase
the doctor should decide

This keeps the system useful, safe and aligned with the actual business.
