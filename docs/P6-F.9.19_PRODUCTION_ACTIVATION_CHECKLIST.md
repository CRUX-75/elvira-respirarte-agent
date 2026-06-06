# P6-F.9.19 — Production Activation Checklist

## Status

DRAFT / CHECKLIST ONLY

## Objective

Prepare the final operational checklist before connecting or activating the official Respirarte Colombian WhatsApp number through WhatsApp Cloud API.

This checklist exists to prevent accidental production activation without verifying webhook readiness, environment flags, safety boundaries, monitoring, rollback, and human operational readiness.

## Current Baseline

- Branch: main
- Local tests: 214 passed
- README.md reconciled
- AI_CONTEXT.md reconciled
- Working tree clean
- Runtime code untouched in the previous reconciliation block
- Real `/webhook` behavior still not activated for patient traffic
- Real WhatsApp sending remains disabled
- `WHATSAPP_SENDING_ENABLED=false`
- `/test/message-stateful` is the validated dry-run endpoint
- Google Sheets, Telegram, n8n, and Calendar remain out of scope for the initial controlled MVP

## Production Safety Rule

Do not touch real `/webhook` behavior or enable `WHATSAPP_SENDING_ENABLED=true` until this checklist and the webhook readiness review are completed.

Elvira must never confirm appointments automatically.

Elvira may only register appointment requests for human review by Dra. D'Aleman.

---

# 1. Repository Readiness

## 1.1 Branch

- [ ] Current branch is `main`.

Validation command:

```bash
git branch --show-current

Expected:

main
1.2 Working Tree
 Working tree is clean.

Validation command:

git status --short

Expected:

No output means clean.

1.3 Tests
 Full local test suite passes.

Validation command:

pytest -q

Expected:

214 passed
1.4 Documentation Baseline
 README.md reflects current production MVP status.
 AI_CONTEXT.md reflects current working status.
 Both documents mention the current safety boundary:
/test/message-stateful validated
/webhook review pending
WHATSAPP_SENDING_ENABLED=false
Google Sheets / Telegram / n8n / Calendar out of initial scope

Suggested validation:

grep -n "214 passed" README.md AI_CONTEXT.md
grep -n "WHATSAPP_SENDING_ENABLED=false" README.md AI_CONTEXT.md
grep -n "P6-F.9.19" README.md AI_CONTEXT.md
2. Production Environment Readiness
2.1 Production Health
 Production /health responds correctly.

Browser or local validation:

https://elvira.genflowautomation.com/health

Expected:

{
  "status": "ok",
  "service": "elvira-respirarte-agent"
}
2.2 Production Readiness
 Production /ready returns ready status.

Browser or local validation:

https://elvira.genflowautomation.com/ready

Expected key values:

status = ready
environment = production
whatsapp_sending_enabled = false
kb_runtime_enabled = true
database configured = true
OpenAI configured = true
WhatsApp configured = true
LangSmith tracing enabled = true
hard_failures = []
real_whatsapp_sending_allowed = false
2.3 EasyPanel Environment Variables
 APP_ENV=production
 KB_RUNTIME_ENABLED=true
 WHATSAPP_SENDING_ENABLED=false
 DATABASE_URL configured
 OPENAI_API_KEY configured
 OPENAI_MODEL configured
 LANGSMITH_TRACING=true
 LANGSMITH_PROJECT=elvira-respirarte-prod
 WHATSAPP_VERIFY_TOKEN configured
 WHATSAPP_API_URL configured
 WHATSAPP_PHONE_NUMBER_ID configured
 WHATSAPP_TOKEN configured

Important:

Do not change WHATSAPP_SENDING_ENABLED during this checklist.

It must remain:

WHATSAPP_SENDING_ENABLED=false
3. Database Readiness
3.1 Required Tables
 patients exists.
 interactions exists.
 processed_messages exists.
 appointment_requests exists.
 kb_services exists.
 kb_schedules exists.
 kb_rules exists.

Validation method:

Use pgweb through EasyPanel.

Suggested SQL:

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
3.2 Appointment Requests Table
 appointment_requests exists.
 Primary key exists on id_solicitud.
 Valid status constraint exists.
 Valid channel constraint exists.
 Active lookup index exists.
 Phone lookup index exists.

Suggested SQL:

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'appointment_requests'
ORDER BY ordinal_position;

Suggested constraint check:

SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'appointment_requests';

Suggested index check:

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'appointment_requests';
3.3 Patients Appointment Context
 patients.appointment_context exists.
 Column type is jsonb.

Suggested SQL:

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'patients'
AND column_name = 'appointment_context';
3.4 Processed Messages Deduplication
 processed_messages table exists.
 whatsapp_message_id can be used for deduplication.
 Existing deduplication logic has been tested locally.

Do not manually delete production deduplication records unless performing a controlled test with known test IDs.

4. Knowledge Base Readiness
4.1 Services
 Active services exist in kb_services.
 Domiciliary respiratory therapy information is present.
 Services are aligned with Respirarte's real offerings.

Suggested SQL:

SELECT *
FROM kb_services
ORDER BY service_id;
4.2 Schedules
 kb_schedules reflects current rules.
 Afternoon domiciliary windows are correct.
 No Saturday domiciliary service is advertised.
 No Sunday service is advertised unless explicitly instructed by the doctor.

Suggested SQL:

SELECT *
FROM kb_schedules
ORDER BY schedule_id;

Expected business rule:

Domiciliary care is handled in afternoon franjas.
Elvira must not offer morning domiciliary appointments.
Elvira must not offer weekends or Colombian holidays.
4.3 Rules
 kb_rules includes operational safety rules.
 Price communication boundaries are correct.
 Urgency escalation rule exists.
 Appointment request disclaimer is present.

Suggested SQL:

SELECT *
FROM kb_rules
ORDER BY rule_id;
5. Dry-Run Readiness
5.1 Safe Endpoint
 /test/message-stateful remains available.
 It does not send real WhatsApp messages.
 It persists state and interactions.
 It can create AppointmentRequests safely with synthetic test IDs.

Production endpoint:

POST https://elvira.genflowautomation.com/test/message-stateful
5.2 Controlled Dry-Run Test Cases

Run through Swagger or controlled API client.

Case 1 — Greeting

Payload:

{
  "telefono": "test-p6f919-greeting",
  "mensaje": "Hola buenos días",
  "nombre": "Paciente Test P6F919"
}

Expected:

Natural greeting
No AppointmentRequest
delivery_status = sending_skipped
Case 2 — Initial Appointment Request

Payload:

{
  "telefono": "test-p6f919-cita",
  "mensaje": "Quiero pedir una cita",
  "nombre": "Paciente Test P6F919"
}

Expected:

intent = cita
nuevo_estado = ST_CITA_FECHA
next_action = ask_preferred_date
response explains afternoon domiciliary franjas
no AppointmentRequest yet
delivery_status = sending_skipped
Case 3 — Relative Date With Afternoon

Payload:

{
  "telefono": "test-p6f919-cita",
  "mensaje": "Mañana en la tarde",
  "nombre": "Paciente Test P6F919"
}

Expected:

Date resolved deterministically
Weekend/holiday blocked if applicable
If valid day:
nuevo_estado = ST_CITA_FRANJA
available afternoon slots offered
no AppointmentRequest yet
Case 4 — Ambiguous Slot Selection

Payload:

{
  "telefono": "test-p6f919-cita",
  "mensaje": "En la tarde",
  "nombre": "Paciente Test P6F919"
}

Expected when multiple slots exist:

remain in ST_CITA_FRANJA
next_action = ask_specific_time_slot
no AppointmentRequest
Elvira asks patient to choose a concrete slot
Case 5 — Concrete Slot Selection

Payload:

{
  "telefono": "test-p6f919-cita",
  "mensaje": "A las 3",
  "nombre": "Paciente Test P6F919"
}

Expected:

intent = hora_cita
nuevo_estado = ST_CITA_PENDIENTE
next_action = confirm_appointment_request
AppointmentRequest persisted
estado_solicitud = pendiente_confirmacion
delivery_status = sending_skipped
Elvira clearly says the request was registered, not confirmed
Case 6 — Opt-Out

Payload:

{
  "telefono": "test-p6f919-optout",
  "mensaje": "No quiero recibir más mensajes",
  "nombre": "Paciente Test P6F919"
}

Expected:

intent = optout
nuevo_estado = ST_OPTOUT
opt_out = true
no AppointmentRequest
future communication blocked or handled according to opt-out policy
6. Webhook Readiness Review

Important:

This section must be completed before real webhook activation.

6.1 GET /webhook Verification
 Confirm Meta webhook verification challenge works.
 hub.challenge is returned as raw text.
 Wrong verify token is rejected.

Expected endpoint:

GET /webhook

Validation should be done carefully with Meta developer tools or a controlled browser request.

6.2 POST /webhook Behavior Review

Before sending real patient traffic:

 Review current POST /webhook runtime behavior.
 Confirm it uses message ID deduplication.
 Confirm it loads patient state.
 Confirm it logs interactions.
 Confirm it respects WHATSAPP_SENDING_ENABLED=false.
 Confirm it does not send if sending flag is false.
 Confirm it never confirms appointments automatically.
 Confirm it handles unsupported payloads safely.
 Confirm it ignores duplicate WhatsApp message IDs.

Do not activate real patient traffic until this review is closed.

7. WhatsApp Cloud API Readiness
7.1 Meta Business Setup
 Meta Business account exists.
 WhatsApp Business Account exists.
 Official Respirarte Colombian number is available for Cloud API use.
 Number is not actively used in standard WhatsApp in a conflicting way.
 Business display name is approved or pending with known status.
 Payment/billing requirements are understood if needed.
7.2 App Configuration
 Meta App is configured.
 WhatsApp product is enabled.
 Correct Phone Number ID is copied to production env.
 Correct WABA ID is documented internally.
 Permanent or long-lived access token strategy is clear.
 Token is stored only in EasyPanel env vars.
 Token is not committed.
7.3 Webhook Subscription
 Webhook callback URL points to:
https://elvira.genflowautomation.com/webhook
 Verify token matches production WHATSAPP_VERIFY_TOKEN.
 Subscribed field includes:
messages

Do not complete this with real traffic until webhook readiness review is closed.

8. Controlled Sending Activation Plan

This section is not approval to activate sending.

It defines what must be true before activation.

Preconditions
 Sections 1–7 are complete.
 /ready confirms real_whatsapp_sending_allowed = false before activation.
 Latest dry-run sequence is green.
 Dra. D'Aleman understands Elvira registers requests but does not confirm appointments.
 Rollback path is clear.
 Monitoring path is clear.
 First real test phone number is controlled.
 No mass patient traffic is connected.
Activation Rule

Only after explicit approval:

WHATSAPP_SENDING_ENABLED=true

Activation must be done in EasyPanel environment variables.

After changing the flag:

 redeploy/restart service if required
 check /ready
 confirm whatsapp_sending_enabled = true
 confirm real_whatsapp_sending_allowed = true
 send one controlled inbound WhatsApp message from an approved test phone
 verify response received
 verify interaction persisted
 verify LangSmith trace exists
 verify no unexpected duplicate responses
9. Monitoring During Controlled Pilot
9.1 Logs
 EasyPanel logs visible.
 Errors can be reviewed quickly.
 WhatsApp send failures are visible.
9.2 Database
 interactions can be searched by phone and message ID.
 processed_messages can be searched by WhatsApp message ID.
 patients can be searched by phone.
 appointment_requests can be searched by phone and id_solicitud.
9.3 LangSmith
 Production traces appear in elvira-respirarte-prod.
 Traces include enough metadata to debug patient turns.
 Appointment flow traces can be found.
9.4 Human Review
 Dra. D'Aleman knows appointment requests are pending human confirmation.
 Dra. D'Aleman knows Elvira does not confirm appointments.
 Operational process for reviewing requests is clear.
 Manual follow-up channel is clear.
10. Rollback Plan

If anything unsafe happens:

10.1 Stop Sending

Set:

WHATSAPP_SENDING_ENABLED=false

Then restart/redeploy if required.

10.2 Disable Webhook Temporarily

If unsafe inbound traffic continues:

 Disable or unsubscribe Meta webhook.
 Keep database records for audit.
 Do not delete evidence before review.
10.3 Stop Service

If needed:

 Stop EasyPanel service temporarily.
10.4 Investigate

Use:

whatsapp_message_id
telefono
id_solicitud
LangSmith run
EasyPanel logs
interactions
processed_messages
patients
appointment_requests
10.5 Restore
 Redeploy previous stable commit if needed.
 Keep sending disabled until the issue is understood.
 Add regression test if a deterministic bug is found.
11. Explicit Non-Goals

This activation checklist does not include:

Google Sheets handoff
Telegram notifications
n8n orchestration
Calendar integration
automatic appointment confirmation
payment workflows
marketing campaigns
mass outbound messages
therapy package/session tracking
cancellation automation
rescheduling automation
12. Closure Criteria

This checklist can be marked closed when:

 Repository readiness is green.
 Production environment readiness is green.
 Database readiness is green.
 KB readiness is green.
 Controlled dry-runs are green.
 Webhook readiness review is complete.
 WhatsApp Cloud API configuration is verified.
 Rollback plan is clear.
 Human operational process is clear.
 No real sending has been activated accidentally.
 Decision is made whether to proceed to controlled sending activation.
Final Safety Statement

Until this checklist is closed, keep:

WHATSAPP_SENDING_ENABLED=false

and do not modify real /webhook behavior for patient traffic.

