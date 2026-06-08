# P6-F.9.28 — First Controlled Real Sending Test

## Status

PLANNED / READY FOR CONTROLLED EXECUTION

## Objective

Run the first controlled real WhatsApp sending test for Elvira / Respirarte.

The goal is to temporarily enable real WhatsApp sending only for one internal controlled phone number, validate real delivery, PostgreSQL evidence, LangSmith trace, and then immediately roll back real sending to disabled.

## Current Baseline

Repository: elvira-respirarte-agent  
Branch: main  
Expected working tree: clean  

Previous sprint:

P6-F.9.26 — Final Webhook Dry-Run Regression Pack

Status:

CLOSED / GREEN / COMMITTED / PRODUCTION WEBHOOK DRY-RUN REGRESSION APPROVED / REAL SENDING DISABLED

Prepared sprint document:

docs/P6-F.9.27_CONTROLLED_REAL_SENDING_MVP_ACTION_PLAN.md

Latest expected local validation:

pytest -q

Expected result:

217 passed

## Safety Rule

WHATSAPP_SENDING_ENABLED=false remains the default production safety baseline.

WHATSAPP_SENDING_ENABLED=true may only be enabled temporarily for this controlled sprint and must be rolled back immediately after the test.

## Strict Scope

This sprint only covers:

- one internal controlled WhatsApp phone
- real inbound webhook message
- real outbound WhatsApp response
- PostgreSQL evidence
- LangSmith trace evidence
- rollback to WHATSAPP_SENDING_ENABLED=false

## Explicitly Out of Scope

Do not touch:

- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy sessions module
- campaigns / marketing
- public traffic
- real patients

## Preconditions

Before enabling real sending, confirm:

- local test suite is green
- production `/ready` is healthy
- production currently reports `whatsapp_sending_enabled=false`
- WhatsApp Cloud API configuration is complete
- webhook is subscribed to `messages`
- Meta App is Live
- API version is v25.0
- templates are active
- test phone is internal and controlled
- no patient/public traffic is active

## Controlled Test Phone

Use only one internal controlled phone number.

Do not publish the number publicly.

Do not invite real patients.

Do not run campaigns.

## Test Sequence A — Basic Real Response

Send from the internal phone:

Hola buenos días

Expected result:

- Meta sends inbound message to `/webhook`
- backend processes message
- Elvira returns a real WhatsApp response
- PostgreSQL persists processed message / interaction evidence
- LangSmith trace exists
- no AppointmentRequest is created unless the message enters appointment flow
- no unexpected state transition occurs

## Test Sequence B — Controlled Appointment Flow

Only if Test Sequence A is green, run:

1. Quiero pedir una cita
2. Para mañana en la tarde
3. La primera franja

Expected result:

- Elvira asks for date/franja correctly
- date is resolved deterministically
- available KB-backed slots are offered
- concrete slot selection is mapped correctly
- AppointmentRequest is created in PostgreSQL
- AppointmentRequest status remains pending human review
- Elvira does not confirm the appointment
- Elvira sends the approved terminal message:
  "Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención."

## Required Evidence

Capture:

- `/ready` before activation
- EasyPanel deployment/env evidence before activation
- real WhatsApp inbound message
- real WhatsApp outbound response
- PostgreSQL evidence for patient/interactions/processed_messages
- PostgreSQL evidence for appointment_requests if Test Sequence B is executed
- LangSmith trace URL or trace identifier
- `/ready` after rollback showing `whatsapp_sending_enabled=false`

## Rollback

Immediately after the controlled test:

Set:

WHATSAPP_SENDING_ENABLED=false

Redeploy/restart production app if required by EasyPanel.

Then confirm via `/ready`:

- whatsapp_sending_enabled=false
- real_whatsapp_sending_allowed=false

## Acceptance Criteria

This sprint is GREEN only if:

- real sending works for the internal controlled phone
- no patient/public traffic is involved
- PostgreSQL contains the expected evidence
- LangSmith trace exists
- appointment flow, if tested, creates the correct AppointmentRequest
- Elvira does not confirm appointments automatically
- rollback to WHATSAPP_SENDING_ENABLED=false is completed and verified

## Failure Handling

If any error occurs:

1. Immediately set WHATSAPP_SENDING_ENABLED=false
2. Redeploy/restart if needed
3. Confirm `/ready`
4. Preserve logs
5. Document the failure
6. Do not continue additional real tests until the issue is fixed

## Final Rule

LangSmith explains.

PostgreSQL proves.

WhatsApp confirms delivery.

Rollback closes the sprint.
