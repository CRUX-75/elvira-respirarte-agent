# P6-F.9.25 — Controlled WhatsApp Sending Activation Plan

## Status

DRAFT / PLANNING ONLY / REAL SENDING STILL DISABLED

## Objective

Prepare the exact technical and operational plan for enabling real WhatsApp sending in a very small controlled pilot for Elvira / Respirarte.

This sprint does not enable real WhatsApp sending by itself.

## Current Baseline

Previous sprint closed:

- P6-F.9.24 — Production MVP Activation SDD
- Validation: `pytest -q` → `217 passed`
- Commit: `7e0da8d Add production MVP activation SDD`
- Working tree: clean

Current safety baseline:

- `WHATSAPP_SENDING_ENABLED=false`
- `/webhook` Meta-shaped dry-run passed in previous sprint context
- AppointmentRequest persistence verified in PostgreSQL
- Elvira must only say the appointment request was received when `appointment_request != null`
- `appointment_requests` remains the source of truth for appointment requests

## Scope

This sprint prepares a controlled sending activation plan.

In scope:

- define exact activation prerequisites
- define allowed test phones
- define production environment checks
- define controlled sending steps
- define rollback procedure
- define E2E validation evidence
- define monitoring requirements
- define stopping conditions
- define the correct role of Swagger
- define the correct role of LangSmith
- define PostgreSQL as final operational evidence

Out of scope:

- enabling `WHATSAPP_SENDING_ENABLED=true`
- public patient traffic
- Google Sheets sync
- Telegram notification
- n8n workflows
- Calendar integration
- doctor confirmation automation
- therapy session tracking
- marketing messages
- mass messaging

## Non-Negotiable Safety Rule

Real WhatsApp sending may only be enabled in a later execution sprint after this plan is reviewed and accepted.

Until then:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

must remain unchanged.

## Evidence Hierarchy

Production readiness must use a layered evidence model.

The hierarchy is:

~~~txt
Swagger = manual inspection and safe pre-check surface
/webhook Meta-shaped = realistic WhatsApp ingress validation
LangSmith = observability and traceability evidence
PostgreSQL = final operational source of truth
~~~

Operational rule:

~~~txt
LangSmith explains what happened.
PostgreSQL proves what happened.
~~~

A flow is not accepted only because Swagger looks correct.

A flow is not accepted only because LangSmith shows a reasonable trace.

A flow is accepted only when the expected PostgreSQL effect exists.

For appointment requests, that means:

~~~txt
appointment_request != null
and appointment_requests contains the correct row in PostgreSQL
~~~

## Swagger Role

Swagger may be used as a manual inspection and pre-check surface.

Allowed Swagger usage:

- inspect `/health`
- inspect `/ready`
- call `/test/message-stateful`
- inspect safe dry-run responses
- verify `WHATSAPP_SENDING_ENABLED=false`
- verify response payload shape before realistic webhook validation

Swagger must not be treated as final production readiness evidence.

Reason:

Swagger does not fully simulate Meta / WhatsApp Cloud API behavior.

Swagger does not prove:

- real Meta-shaped payload compatibility
- fresh `wamid` handling
- deduplication behavior under `/webhook`
- real WhatsApp delivery
- full production ingress behavior

Final readiness before real sending requires:

- `/webhook` Meta-shaped payload validation
- fresh `wamid` values
- fresh test phone per flow when needed
- PostgreSQL evidence

## LangSmith Role

LangSmith must be used as production observability evidence for controlled pilot flows.

For every critical E2E flow, the operator must verify that a LangSmith trace exists and contains enough information to inspect:

- intent
- previous state
- new state
- next_action
- state_reason
- KB/runtime context usage when applicable
- errors or exceptions
- approximate latency
- model/tool behavior when relevant

LangSmith is not the final acceptance source of truth.

Reason:

LangSmith can explain how the system reasoned or moved through the flow, but it does not replace operational persistence.

A trace may look correct while the DB effect is missing.

Therefore:

~~~txt
No PostgreSQL effect = no accepted conversational flow.
~~~

## PostgreSQL Role

PostgreSQL is the final operational source of truth.

For controlled production readiness, the following tables must be considered as evidence depending on the flow:

- `patients`
- `interactions`
- `processed_messages`
- `appointment_requests`

For appointment registration flows, the critical table is:

- `appointment_requests`

A patient-facing response such as:

~~~txt
Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.
~~~

is valid only when:

~~~txt
appointment_request != null
and appointment_requests.estado_solicitud = pendiente_confirmacion
~~~

## Activation Prerequisites

Before enabling real sending, all of the following must be true:

1. Repository is clean.

2. Full local test suite passes:

~~~txt
pytest -q
~~~

3. Production `/ready` confirms:

- `status = ready`
- `whatsapp_sending_enabled = false`
- `real_whatsapp_sending_allowed = false`
- database configured
- WhatsApp configured
- OpenAI configured
- LangSmith tracing enabled

4. `/webhook` Meta-shaped dry-run passes with:

- fresh test phone
- fresh `wamid` values
- `delivery_status = sending_skipped`
- no real message sent
- correct patient state transitions
- correct interaction logging
- correct AppointmentRequest persistence when applicable

5. LangSmith trace exists for each critical dry-run flow.

6. PostgreSQL evidence exists for appointment flow:

- `appointment_request != null`
- row exists in `appointment_requests`
- `estado_solicitud = pendiente_confirmacion`
- correct `fecha_solicitada`
- correct `franja_solicitada`
- `source_interaction_id` matches final `wamid`

## Allowed Pilot Boundary

The first controlled sending pilot is limited to:

- one official Respirarte WhatsApp Cloud API number
- one internal controlled recipient phone
- patient-style test messages only
- manual observation after each message
- immediate rollback available

Not allowed:

- real patient traffic
- public launch
- bulk messaging
- marketing templates
- automated doctor confirmation
- uncontrolled inbound testing from unknown phones

## Controlled Sending Execution Plan

The future execution sprint must follow this exact order:

1. Confirm current production readiness through `/ready`.

2. Confirm current production environment still has:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

3. Run one final Swagger pre-check for `/ready`.

4. Run one final `/webhook` Meta-shaped dry-run with sending disabled.

5. Verify LangSmith trace for the dry-run.

6. Verify PostgreSQL effect for the dry-run.

7. Select one controlled recipient phone.

8. Enable real sending only for the controlled pilot environment.

9. Confirm `/ready` reflects:

~~~txt
whatsapp_sending_enabled = true
real_whatsapp_sending_allowed = true
~~~

10. Send one inbound test message from the controlled phone.

11. Verify:

- real WhatsApp response received
- `interactions` row created
- `processed_messages` row created
- patient state updated
- LangSmith trace exists
- no duplicate processing

12. Continue with one full appointment request test flow.

13. Verify PostgreSQL `appointment_requests` row.

14. Stop and review before any broader testing.

## Required Pilot Conversation

The first real sending pilot must validate this flow:

1. Patient says:

~~~txt
Quiero pedir una cita
~~~

Expected:

- Elvira responds with initial appointment copy
- state moves to `ST_CITA_FECHA`
- no AppointmentRequest created yet
- LangSmith trace exists
- DB state transition is visible

2. Patient says:

~~~txt
El martes en la tarde
~~~

Expected:

- date resolves deterministically
- valid KB-backed franjas are offered
- state moves to `ST_CITA_FRANJA`
- no AppointmentRequest created yet
- LangSmith trace exists
- patient context/state is persisted as expected

3. Patient says:

~~~txt
A las 3
~~~

Expected:

- state moves to `ST_CITA_PENDIENTE`
- response says request was received
- `appointment_request != null`
- PostgreSQL row exists
- `estado_solicitud = pendiente_confirmacion`
- `source_interaction_id` matches final real `wamid`
- LangSmith trace exists

## Required Evidence Before Closing Real Sending Pilot

The future real sending execution sprint must capture:

- production `/ready` before activation
- Swagger `/ready` pre-check result
- exact env flag change
- production `/ready` after activation
- real inbound payload or Meta delivery evidence
- response payload
- WhatsApp message actually received on controlled phone
- `interactions` DB row
- `processed_messages` DB row
- `patients` DB state
- `appointment_requests` DB row when appointment request is registered
- LangSmith trace link or trace identifier
- rollback confirmation if sending is disabled again

## Rollback Plan

If anything fails:

1. immediately restore:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

2. restart/redeploy app if required

3. confirm `/ready` shows:

~~~txt
whatsapp_sending_enabled = false
real_whatsapp_sending_allowed = false
~~~

4. stop all real tests

5. preserve logs and DB evidence

6. preserve LangSmith trace identifiers

7. document failing flow

8. fix with automated tests first

9. rerun local suite

10. rerun `/test/message-stateful`

11. rerun `/webhook` Meta-shaped dry-run

12. verify PostgreSQL effect again

13. do not reactivate sending until the bug is closed

## Hard Stop Conditions

Stop immediately if:

- Elvira sends a message to an uncontrolled phone
- duplicate `wamid` creates duplicate processing
- appointment request response appears while `appointment_request = null`
- appointment request is missing in PostgreSQL
- wrong date or wrong franja is persisted
- Elvira confirms real availability automatically
- Elvira promises an exact hour inside a franja
- any 500 error appears in `/webhook`
- LangSmith evidence is missing for a critical flow
- DB evidence is missing for a critical flow

## Definition of Done

P6-F.9.25 is closed only when:

- this activation plan is committed
- `WHATSAPP_SENDING_ENABLED=false` remains unchanged
- no real sending has been enabled
- Swagger role is documented
- LangSmith role is documented
- PostgreSQL remains documented as final operational source of truth
- pilot boundary is explicit
- rollback path is explicit
- required DB evidence is explicit
- next sprint is clearly defined

## Proposed Next Sprint

P6-F.9.26 — Final Webhook Dry-Run Regression Pack

Goal:

Run the final production `/webhook` dry-run regression pack with Meta-shaped payloads, fresh phones, fresh `wamid` values, LangSmith traces, and PostgreSQL evidence before any real sending activation.
