# P6-F — Controlled Sending Activation Plan

## Status

Sprint: P6-F  
Phase: Pre-activation operational planning  
Current sending status: disabled  
Live WhatsApp sending must remain disabled until explicitly activated for one authorized test.

Current production readiness baseline:

- `/ready` status: ready
- environment: production
- WHATSAPP_SENDING_ENABLED=false
- KB_RUNTIME_ENABLED=true
- real_whatsapp_sending_allowed=false

## Non-negotiable Rules

- Do not activate `WHATSAPP_SENDING_ENABLED=true` yet.
- Do not connect or replace the Colombian Respirarte number yet.
- Do not connect Google Calendar real availability yet.
- Do not modify state machine logic, KB routing, or database schema unless a critical bug is found.
- All production validation must be done through browser, Swagger, EasyPanel logs, LangSmith, Meta dashboard, or local/VS Code terminal.
- Curl must not be assumed available inside EasyPanel Bash.

---

## P6-F Objective

Create a safe, reversible and auditable operational activation plan for WhatsApp real sending.

The activation must happen in a controlled way:

1. Validate WhatsApp Manager readiness.
2. Prepare Colombian Respirarte number checklist.
3. Define minimum required templates.
4. Validate EasyPanel environment variables.
5. Run final production dry-run with sending disabled.
6. Temporarily activate sending for one authorized test only.
7. Audit DB, LangSmith and Meta.
8. Roll back immediately to sending disabled.

---

## P6-F.1 — WhatsApp Manager Readiness Checklist

Before enabling real sending, validate in Meta WhatsApp Manager:

- Meta App is connected to the correct Business Manager.
- WhatsApp product is configured.
- Webhook callback URL points to production:
  - `https://elvira.genflowautomation.com/webhook`
- Webhook verify token is correctly configured.
- Required webhook fields are subscribed.
- Test number is still available for controlled testing.
- Production phone number migration has not been started yet.
- No ice breakers are configured for now.
- Templates section is accessible.
- Message templates can be created and submitted for approval.

Decision:

- Ice breakers remain disabled because Elvira is intended to behave as a controlled conversational assistant, not as a generic chatbot menu.

---

## P6-F.2 — Colombian Respirarte Number Checklist

The Colombian Respirarte number must not be connected yet.

Before migrating or adding the number, validate:

- The number is controlled by Dra. D'Aleman / Respirarte.
- The team has access to receive SMS or voice verification.
- The number is not actively registered in WhatsApp or WhatsApp Business App at migration time.
- The Business Manager is the correct one.
- The display name is ready for review.
- The production webhook is already stable.
- Rollback strategy is understood before replacing the test number.

Decision:

- Continue with the test number until the first controlled production sending test is completed successfully.
- The Colombian number migration belongs after the controlled sending test, not before.

---

## P6-F.3 — Minimum WhatsApp Templates

Minimum recommended templates before go-live:

### 1. Appointment Follow-up / Confirmation

Purpose:

- Follow up after a patient has requested an appointment.
- Confirm that the request was received.
- Avoid promising confirmed availability unless manually confirmed.

Suggested category:

- Utility

### 2. Appointment Reminder

Purpose:

- Remind the patient about an already confirmed appointment.
- Only after manual or future calendar-confirmed scheduling.

Suggested category:

- Utility

### 3. Administrative Recontact

Purpose:

- Recontact a patient when operationally necessary.
- Example: missing information, clarification, or follow-up.

Suggested category:

- Utility

### 4. Optional Service Information

Purpose:

- Send requested service information only when allowed by WhatsApp policy and patient context.

Suggested category:

- Utility or Marketing depending on final wording and use case.

Rules:

- No medical diagnosis.
- No urgency handling through templates.
- No confirmed availability unless confirmed by human or future calendar service.
- No aggressive promotional wording.
- No automated payment handling in Elvira.

---

## P6-F.5 — EasyPanel Environment Variables and /ready Validation

Before any controlled activation, validate these variables in EasyPanel:

- ENVIRONMENT=production
- WHATSAPP_SENDING_ENABLED=false
- KB_RUNTIME_ENABLED=true
- WHATSAPP_ACCESS_TOKEN configured
- WHATSAPP_PHONE_NUMBER_ID configured
- WHATSAPP_VERIFY_TOKEN configured
- OPENAI_API_KEY configured
- LANGSMITH_TRACING configured
- LANGSMITH_PROJECT configured
- DATABASE_URL configured

Expected `/ready` before activation:

- status=ready
- environment=production
- whatsapp_configured=true
- database_configured=true
- openai_configured=true
- langsmith_configured=true
- WHATSAPP_SENDING_ENABLED=false
- KB_RUNTIME_ENABLED=true
- real_whatsapp_sending_allowed=false

---

## P6-F.6 — Final Dry-run With Sending Disabled

Before activating real sending, run one final dry-run in production with sending disabled.

Validation method:

- Use browser or Swagger.
- Do not rely on curl inside EasyPanel Bash.

Test scenario:

- Patient in appointment flow.
- Message: "Mañana en la tarde"
- Expected behavior:
  - Elvira interprets the date using Colombia timezone.
  - Elvira does not claim confirmed availability.
  - Elvira does not say "disponemos de".
  - Elvira asks for the preferred hour or continues the appointment flow safely.
  - DB interaction is stored.
  - LangSmith trace is created.
  - WhatsApp real sending remains skipped.

Expected production state:

- WHATSAPP_SENDING_ENABLED=false
- real_whatsapp_sending_allowed=false
- no real WhatsApp message sent

---

## P6-F.7 — Documentation and Git Closure

Purpose:

Close the validated dry-run documentation state before preparing controlled real sending.

Status:

- P6-F.5 EasyPanel environment variables and `/ready` validation completed.
- P6-F.6 final production dry-run with `WHATSAPP_SENDING_ENABLED=false` completed.
- Production `/test/message-stateful` validated.
- Appointment flow validated:
  - `ST_INIT → ST_CITA_FECHA → ST_CITA_FRANJA → ST_CITA_PENDIENTE`
- Opt-out flow validated:
  - `ST_CITA_PENDIENTE → ST_OPTOUT`
- `delivery_status=sending_skipped` confirmed.
- Real WhatsApp sending remains disabled.
- No Colombian number migration has been executed.
- No Google Calendar integration has been activated.

Closure rule:

P6-F.7 is documentation and repository closure only.
It does not activate real WhatsApp sending.

---

## P6-F.8 — Controlled Real WhatsApp Sending Activation Checklist

This checklist is prepared but not executed yet. Real WhatsApp sending must not be activated until explicitly authorized during the controlled live test.

Activation window:

- One authorized test only.
- One known phone number only.
- One incoming WhatsApp message only.
- Immediate rollback after validation.

Activation steps:

1. Change EasyPanel variable:
   - WHATSAPP_SENDING_ENABLED=true

2. Redeploy production service.

3. Validate `/ready`:

Expected:

- status=ready
- WHATSAPP_SENDING_ENABLED=true
- real_whatsapp_sending_allowed=true

4. Send one test message from the authorized WhatsApp number.

5. Confirm:

- WhatsApp receives Elvira's response.
- DB stores interaction.
- processed_messages stores WhatsApp message ID.
- LangSmith trace is created.
- Meta dashboard shows message activity.

6. Immediately rollback:

- WHATSAPP_SENDING_ENABLED=false

7. Redeploy again.

8. Validate `/ready`:

Expected:

- WHATSAPP_SENDING_ENABLED=false
- real_whatsapp_sending_allowed=false

---

### P6-F.8.1 — Post-test Audit

After the single live test, audit:

### Database

Validate:

- patients table updated correctly.
- interactions table contains the message and response.
- processed_messages contains the WhatsApp message ID.
- opt_out remains false unless explicitly requested.
- state transition is correct.

### LangSmith

Validate:

- trace exists.
- intent is correct.
- estado_anterior and nuevo_estado are correct.
- kb_used value is expected.
- deterministic date context is present when relevant.
- no unsafe medical or availability claim appears.

### Meta / WhatsApp Manager

Validate:

- inbound message received.
- outbound message sent.
- no repeated or duplicate messages.
- no template issue caused unexpected behavior.
- no delivery error appears.

---

### P6-F.8.2 — Rollback Rule

Rollback must happen immediately after the single authorized live test.

Final expected production state:

- WHATSAPP_SENDING_ENABLED=false
- real_whatsapp_sending_allowed=false
- Production remains ready.
- No further real messages are sent automatically.

---

## P6-F Exit Criteria

P6-F can be considered complete when:

- WhatsApp Manager readiness checklist is documented.
- Colombian number migration checklist is documented.
- Minimum templates are defined.
- EasyPanel variables checklist is documented.
- Final dry-run with sending disabled is validated.
- Controlled one-message activation procedure is documented.
- Rollback procedure is documented.
- Audit procedure for DB, LangSmith and Meta is documented.

P6-F does not require leaving real sending enabled.


---

## P6-F.3 — WhatsApp Manager Readiness Verification

Manual verification completed in WhatsApp Manager.

Verified:

- WhatsApp Manager access confirmed.
- Message templates section accessible.
- Existing templates visible.
- Two templates currently active.
- German test phone number connected.
- German test phone number quality rating: high.
- Colombian Respirarte phone number is already listed in WhatsApp Manager.
- Colombian phone number status: not verified.

Pending:

- Colombian Respirarte number verification must be completed together with Dra. D'Aleman during a live call.
- Do not complete the Colombian number verification without direct coordination with Dra. D'Aleman.
- Do not replace the current connected test number before controlled sending validation is completed.

Decision:

- Continue P6-F using the currently connected German test number.
- Keep the Colombian number pending verification until the dedicated number activation step.


---

## Appendix A — Minimum WhatsApp Templates Review

Current WhatsApp Manager state:

- Two message templates are active.
- Existing templates include:
  - `flyer_servicios_respira`
  - `appointment_confirm...`

Decision for P6-F controlled sending:

- The first controlled live sending test must be user-initiated.
- No outbound template should be used during the first controlled activation.
- The authorized tester must send the first WhatsApp message to Elvira.
- Elvira should reply within the active 24-hour customer service window.
- Marketing templates must not be used for the first activation test.
- Appointment confirmation templates must not be used until the appointment confirmation workflow is explicitly implemented and validated.

Reason:

- P6-F validates real WhatsApp response sending, not outbound campaign/template behavior.
- Avoid mixing template approval, campaign delivery, and conversational safety in the same activation step.
- Keep the first live test reversible, minimal and auditable.

Template roadmap after P6-F:

- Review and adjust appointment confirmation template.
- Create or refine administrative follow-up template if needed.
- Create appointment reminder template only after the appointment workflow exists.
- Keep marketing templates separate from Elvira's medical/service conversation flow.


---

## P6-F.7.1 — Fix Colombian Appointment Time Preference Context

### Status

✅ Closed and validated in production with:

- `WHATSAPP_SENDING_ENABLED=false`
- Colombian Respirarte number untouched
- Google Calendar untouched
- Production dry-run only through `/test/message-stateful`

---

### Bug Detected

During production validation in LangSmith, the following conversational case failed:

**Previous state**

```txt
ST_CITA_FRANJA
Patient message

La de 5 de la tarde

Incorrect result before the fix

intent = general
next_action = answer_general
nuevo_estado = ST_CITA_FRANJA
kb_sources = kb_services + kb_schedules + kb_rules

The generated response incorrectly said something equivalent to:

Lamentablemente, no estamos operando hoy...

This was unsafe and conversationally incorrect because:

The patient was clearly selecting a preferred appointment time.
No fecha_solicitada existed for that message.
es_dia_disponible=false without a requested date must not be interpreted as “today is unavailable”.
The flow should have moved forward to appointment review, not answered as a general message.
Root Cause

The deterministic intent classifier already supported:

hora_cita
ST_CITA_FRANJA -> ST_CITA_PENDIENTE
confirm_appointment_request

However, app/services/intent.py did not yet recognize several natural Colombian appointment-time responses, including:

La de 5 de la tarde
A las cinco
Tipo 5
A eso de las 5
Cinco de la tarde
La de cinco

As a result, these messages fell through as:

intent = general

A secondary issue existed in the LLM date context builder:

When fecha_actual_colombia existed but fecha_solicitada was null,
the LLM could still receive:
es_dia_disponible=false
day-operational context
which could trigger unsafe wording such as:
“hoy no operamos”
“no hay atención hoy”
Fix Applied
1. Expanded Colombian natural-language time detection

Updated:

app/services/intent.py

Added deterministic pattern coverage for Colombian appointment-time preference expressions inside ST_CITA_FRANJA, including:

La de 5 de la tarde
La de cinco
A las cinco
Cinco de la tarde
Tipo 5
A eso de las 5

These messages are now classified as:

intent = hora_cita
2. Existing state machine path confirmed

No architectural change was required in:

app/graph/transitions.py

The existing deterministic transition was already correct:

intent = hora_cita
ST_CITA_FRANJA -> ST_CITA_PENDIENTE
next_action = confirm_appointment_request
3. KB routing validated for appointment-time preference

Added test coverage to confirm:

intent = hora_cita
estado_actual = ST_CITA_FRANJA

loads only:

kb_schedules
kb_rules

and explicitly excludes:

kb_services

Expected KB routing:

kb_sources = ["kb_schedules", "kb_rules"]
4. LLM guardrail added for missing requested date

Updated:

app/services/llm.py

New rule:

If:

fecha_solicitada is null

then the date context must not expose:

Día operativo según reglas internas: False

and must instead include an explicit safe instruction:

Do not interpret operational availability without an explicitly requested date.
Do not say that today is unavailable.
Do not say that Respirarte is not operating today.
If the flow is about appointment coordination, only register the preference or request the missing information.
Tests Added
Intent classification tests

Added coverage for:

La de 5 de la tarde
A las 5 pm
17:00
La segunda
La primera
A las cinco
Tipo 5
Como a las 5
Por ahí a las 5
A eso de las 5
Cinco de la tarde
La de cinco

Expected:

classify_intent(..., "ST_CITA_FRANJA") == "hora_cita"
State machine tests

Validated that appointment-time preferences produce:

intent = hora_cita
nuevo_estado = ST_CITA_PENDIENTE
next_action = confirm_appointment_request
KB routing test

Validated:

kb_sources = ["kb_schedules", "kb_rules"]

and:

kb_services not loaded
LLM date-context guardrail test

Validated that when:

fecha_solicitada = null
es_dia_disponible = false

the context does not expose operational-day false signals to the LLM and instead instructs it not to claim that “today is unavailable”.

Local Validation

Full local suite after the fix:

66 passed in 11.02s
Git Commit

Commit pushed to main:

9dc6424 — fix: detect Colombian appointment time preferences
Production Validation
/ready

Production readiness remained healthy:

{
  "status": "ready",
  "environment": "production",
  "whatsapp_sending_enabled": false,
  "kb_runtime_enabled": true,
  "hard_failures": []
}
/test/message-stateful

Production dry-run body:

{
  "telefono": "4917655660163",
  "nombre": "Nabit Mikan",
  "mensaje": "La de 5 de la tarde",
  "estado_actual": "ST_CITA_FRANJA",
  "opt_out": false
}

Validated production result:

intent = hora_cita
nuevo_estado = ST_CITA_PENDIENTE
next_action = confirm_appointment_request
kb_sources = ["kb_schedules", "kb_rules"]
delivery_status = sending_skipped
persisted_state = ST_CITA_PENDIENTE

Validated response:

Gracias. Dejo registrada su preferencia para esa franja.
La disponibilidad debe ser validada por la Dra. D'Aleman o el equipo de Respirarte antes de confirmar la cita.

The response was safe because it:

did not confirm real availability,
did not confirm a final appointment,
did not say “today is unavailable”,
did not load kb_services,
preserved the deterministic appointment flow.
Operational Conclusion

P6-F.7.1 is closed.

The Elvira production flow now correctly interprets natural Colombian appointment-time preferences during ST_CITA_FRANJA, including colloquial patient responses such as:

La de 5 de la tarde

The fix was:

deterministic,
covered by tests,
validated locally,
validated in production dry-run,
deployed with real WhatsApp sending still disabled.


---

## P6-F.7.2 — Colombian AM/PM Slot Label Normalization

### Objective

Normalize appointment slot labels from 24-hour internal display format to a patient-friendly Colombian `a. m. / p. m.` format.

The goal was to avoid exposing slot candidates such as:

```text
15:00–17:00
17:00–19:00
and instead use:

3:00 p. m.–5:00 p. m.
5:00 p. m.–7:00 p. m.

This keeps Elvira's appointment dialogue more natural for Colombian patients.

Root Cause

After P6-F.7.1, Elvira correctly interpreted natural Colombian appointment-time preferences such as:

La de las 5 me queda bien.

However, when offering candidate appointment windows, the deterministic calendar service still built slot labels using:

strftime("%H:%M")

which produced 24-hour labels such as:

15:00–17:00

These labels were then propagated through:

slots_candidatos
LLM date context
patient-facing appointment responses
Fix Applied

The slot label generation in:

app/services/calendar_service.py

was updated to use a dedicated formatting helper:

_format_patient_time(...)

This converts internal deterministic time(...) objects into patient-facing Colombian-style labels:

15:00 -> 3:00 p. m.
17:00 -> 5:00 p. m.
19:00 -> 7:00 p. m.

The underlying deterministic slot boundaries remain unchanged:

Monday / Tuesday / Thursday / Friday:
15:00–17:00
17:00–19:00
Wednesday:
15:00–17:00 only

Only the slot label representation changed.

Example Result

Before:

"slots_candidatos": [
  "15:00–17:00"
]

After:

"slots_candidatos": [
  "3:00 p. m.–5:00 p. m."
]
Tests Updated

Updated expectations in:

tests/test_calendar_service.py
tests/test_date_resolver.py
tests/test_llm_date_context.py

New expected slot labels:

3:00 p. m.–5:00 p. m.
5:00 p. m.–7:00 p. m.
Local Validation

Targeted validation:

15 passed in 1.99s

Full test suite:

66 passed in 12.19s
Git Commit

Commit pushed to main:

17ff5bd — fix: use Colombian am pm slot labels
Operational Conclusion

P6-F.7.2 is closed.

Elvira now:

interprets Colombian natural appointment-time preferences,
offers appointment slot candidates in patient-friendly a. m. / p. m. format,
keeps deterministic scheduling logic intact,
preserves full test coverage,
remains safe for production dry-runs with real WhatsApp sending still disabled.
