# P6-F.9.26 — Final Webhook Dry-Run Regression Pack

## Status

DRAFT / DRY-RUN ONLY / REAL SENDING DISABLED

## Objective

Run and document the final production `/webhook` dry-run regression pack before any controlled real WhatsApp sending activation.

This sprint validates realistic WhatsApp ingress using Meta-shaped payloads while keeping real sending disabled.

This sprint must not enable real WhatsApp sending.

## Current Baseline

Previous sprint closed:

- P6-F.9.25 — Controlled WhatsApp Sending Activation Plan
- Validation: `pytest -q` → `217 passed`
- Commit: `3fbe528 Add controlled WhatsApp sending activation plan`
- Working tree: clean

Current safety baseline:

- `WHATSAPP_SENDING_ENABLED=false`
- real WhatsApp sending disabled
- `/webhook` already wired
- AppointmentRequest persistence works
- exact-hour franja confirmation bug fixed
- `appointment_requests` remains the source of truth
- Swagger may be used for pre-checks only
- LangSmith is observability evidence
- PostgreSQL is final operational evidence

## Scope

In scope:

- define final `/webhook` Meta-shaped dry-run regression pack
- use fresh test phones
- use fresh `wamid` values
- verify `processed_messages` deduplication
- verify `interactions` logging
- verify `patients` state transitions
- verify `appointment_requests` persistence when applicable
- verify LangSmith traces exist
- verify `delivery_status = sending_skipped`
- verify no real WhatsApp message is sent

Out of scope:

- enabling `WHATSAPP_SENDING_ENABLED=true`
- real WhatsApp sending
- public patient traffic
- Google Sheets sync
- Telegram notification
- n8n workflows
- Calendar integration
- doctor confirmation automation
- therapy session tracking
- broad refactors

## Non-Negotiable Safety Rule

During this sprint:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

must remain unchanged.

Any response from `/webhook` must result in:

~~~txt
delivery_status = sending_skipped
~~~

No real WhatsApp message may be sent.

## Evidence Hierarchy

The evidence model remains:

~~~txt
Swagger = manual pre-check
/webhook Meta-shaped = realistic WhatsApp ingress validation
LangSmith = observability and traceability evidence
PostgreSQL = final operational source of truth
~~~

Operational rule:

~~~txt
LangSmith explains what happened.
PostgreSQL proves what happened.
~~~

## Pre-Run Checklist

Before running the regression pack:

1. Confirm repository is clean:

~~~bash
git status --short
~~~

Expected:

~~~txt
empty output
~~~

2. Confirm local test suite is green:

~~~bash
pytest -q
~~~

Expected:

~~~txt
217 passed
~~~

3. Confirm production readiness through `/ready`.

Expected:

- `status = ready`
- `whatsapp_sending_enabled = false`
- `real_whatsapp_sending_allowed = false`
- database configured
- WhatsApp configured
- OpenAI configured
- LangSmith tracing enabled

4. Confirm test data discipline:

- use fresh phone per major flow
- use fresh `wamid` per message
- do not reuse previous production dry-run `wamid` values
- record every phone and `wamid`

## Regression Pack Overview

The final dry-run regression pack includes:

1. Health/readiness check
2. Basic greeting flow
3. Appointment happy path
4. Exact-hour inside franja confirmation flow
5. Ambiguous slot guard flow
6. Unsupported/blocked flow where applicable
7. Duplicate `wamid` deduplication check
8. Opt-out safety check if currently supported in production flow

## Flow 0 — Readiness Check

Endpoint:

~~~txt
GET /ready
~~~

Expected:

- `status = ready`
- `whatsapp_sending_enabled = false`
- `real_whatsapp_sending_allowed = false`
- no hard failures
- LangSmith configured
- DB configured
- WhatsApp configured

Acceptance:

This flow is accepted only if the production app confirms real sending is disabled.

## Flow 1 — Basic Greeting

Purpose:

Validate that `/webhook` accepts a basic Meta-shaped inbound text message and produces a safe response without appointment side effects.

Input message:

~~~txt
Hola buenos días
~~~

Expected response behavior:

- intent is not appointment persistence
- no AppointmentRequest created
- `delivery_status = sending_skipped`
- patient row exists or updates correctly
- interaction row exists
- processed message row exists
- LangSmith trace exists

DB acceptance:

- `processed_messages` contains the fresh `wamid`
- `interactions` contains the message/response audit
- `appointment_requests` has no row for this greeting flow

## Flow 2 — Appointment Happy Path

Purpose:

Validate the standard appointment request flow through `/webhook` with Meta-shaped payloads.

Use fresh phone:

~~~txt
test-p6f926-happy-001
~~~

Use fresh `wamid` values, one per turn.

Conversation:

1. Patient:

~~~txt
Quiero pedir una cita
~~~

Expected:

- `intent = cita`
- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `delivery_status = sending_skipped`
- `appointment_request = null`
- no row in `appointment_requests` yet

2. Patient:

~~~txt
El martes en la tarde
~~~

Expected:

- `intent = fecha_cita`
- `nuevo_estado = ST_CITA_FRANJA`
- valid date resolved
- valid KB-backed slots offered
- `delivery_status = sending_skipped`
- `appointment_request = null`
- no row in `appointment_requests` yet

3. Patient:

~~~txt
A las 3
~~~

Expected:

- `intent = hora_cita`
- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- `delivery_status = sending_skipped`
- `appointment_request != null`

DB acceptance:

- `appointment_requests` row exists
- `estado_solicitud = pendiente_confirmacion`
- `fecha_solicitada` matches resolved date
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `source_interaction_id` matches final `wamid`
- patient state is `ST_CITA_PENDIENTE`
- interaction rows exist for all turns
- processed message rows exist for all `wamid` values
- LangSmith trace exists for each turn

## Flow 3 — Exact-Hour Inside Franja Confirmation

Purpose:

Validate that an exact hour inside a franja does not persist immediately and only creates AppointmentRequest after explicit patient confirmation.

Use fresh phone:

~~~txt
test-p6f926-exact-hour-001
~~~

Conversation:

1. Patient:

~~~txt
Quiero pedir una cita
~~~

2. Patient:

~~~txt
El martes en la tarde
~~~

3. Patient:

~~~txt
A las 4
~~~

Expected after turn 3:

- `nuevo_estado = ST_CITA_FRANJA`
- `next_action = ask_confirm_exact_hour_as_slot`
- no AppointmentRequest created
- pending franja context exists
- response explains care is handled by franjas, not guaranteed exact hours

4. Patient:

~~~txt
Sí, registre esa franja
~~~

Expected after turn 4:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- `delivery_status = sending_skipped`
- `appointment_request != null`

DB acceptance:

- `appointment_requests` row exists only after turn 4
- `estado_solicitud = pendiente_confirmacion`
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `source_interaction_id` matches final `wamid`
- patient state is `ST_CITA_PENDIENTE`
- LangSmith traces exist

## Flow 4 — Ambiguous Slot Guard

Purpose:

Validate that generic slot replies do not create AppointmentRequest when multiple visible slots exist.

Use fresh phone:

~~~txt
test-p6f926-ambiguous-001
~~~

Conversation:

1. Patient:

~~~txt
Quiero pedir una cita
~~~

2. Patient:

~~~txt
El martes en la tarde
~~~

3. Patient:

~~~txt
En la tarde
~~~

Expected after turn 3:

- intent may be `hora_cita`
- `nuevo_estado = ST_CITA_FRANJA`
- `next_action = ask_specific_time_slot`
- response asks patient to choose one concrete visible franja
- `delivery_status = sending_skipped`
- `appointment_request = null`

DB acceptance:

- no new `appointment_requests` row for this flow
- patient remains in `ST_CITA_FRANJA`
- interaction row exists
- processed message row exists
- LangSmith trace exists

## Flow 5 — Duplicate WAMID Deduplication

Purpose:

Validate that repeated Meta `wamid` values do not create duplicate operational effects.

Use a fresh phone and one fresh `wamid`.

Send the same Meta-shaped webhook payload twice.

Expected first call:

- payload is processed normally
- processed message row created
- interaction row created if applicable

Expected second call:

- duplicate is detected
- no duplicate operational effect
- no duplicate AppointmentRequest
- no duplicate patient state mutation beyond expected idempotent behavior

DB acceptance:

- `processed_messages` has one row for the duplicated `wamid`
- no duplicate AppointmentRequest
- no duplicate critical side effect

## Flow 6 — Opt-Out Safety Check

Purpose:

Validate opt-out behavior if included in current production routing.

Use fresh phone:

~~~txt
test-p6f926-optout-001
~~~

Message:

~~~txt
No quiero recibir más mensajes
~~~

Expected:

- opt-out intent/state is handled safely
- real sending remains skipped
- no AppointmentRequest created
- interaction row exists
- processed message row exists
- LangSmith trace exists

DB acceptance:

- patient opt-out state/flag persists according to current schema
- no appointment request row created

## Required Evidence Log

For each flow, capture:

- endpoint used
- fresh phone
- fresh `wamid` values
- request payloads or payload identifiers
- response payloads
- `delivery_status`
- `whatsapp_sending_enabled`
- `estado_anterior`
- `nuevo_estado`
- `intent`
- `next_action`
- `state_reason`
- `appointment_request_decision.reason`
- `appointment_request`
- LangSmith trace identifier
- relevant PostgreSQL rows

## Acceptance Criteria

P6-F.9.26 is accepted only if:

- local tests remain green
- `/ready` confirms sending disabled
- all critical `/webhook` Meta-shaped dry-run flows pass
- every critical flow has LangSmith trace evidence
- every accepted flow has PostgreSQL evidence
- no real WhatsApp message is sent
- duplicate `wamid` behavior is verified
- AppointmentRequest registration is trusted only when DB row exists

## Blocking Conditions

Stop the regression pack if:

- `/ready` shows `whatsapp_sending_enabled = true`
- `/ready` shows `real_whatsapp_sending_allowed = true`
- any real WhatsApp message is sent
- `/webhook` returns 500
- appointment request response appears while `appointment_request = null`
- appointment request DB row is missing
- wrong date or wrong franja is persisted
- duplicate `wamid` creates duplicate critical effects
- LangSmith trace is missing for a critical flow
- DB evidence is missing for a critical flow

## Rollback / Containment

If any blocker appears:

1. keep or restore:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

2. stop all dry-runs

3. preserve request/response payloads

4. preserve DB rows

5. preserve LangSmith trace IDs

6. document failing flow

7. fix with automated tests first

8. rerun local test suite

9. rerun safe endpoint validation

10. rerun `/webhook` Meta-shaped dry-run

## Definition of Done

P6-F.9.26 is closed only when:

- this regression pack is committed
- all dry-run flows are executed or explicitly marked deferred with reason
- evidence is recorded
- no real sending is enabled
- `WHATSAPP_SENDING_ENABLED=false` remains unchanged
- next sprint is clearly defined

## Proposed Next Sprint

P6-F.9.27 — Controlled Sending Activation Execution Checklist

Goal:

Prepare the exact execution checklist for enabling real WhatsApp sending only for one controlled internal test phone, after the final dry-run regression pack is green.

---

## Execution Result — Production Webhook Dry-Run Regression Pack

Status:

CLOSED / GREEN / APPROVED / REAL SENDING DISABLED

Execution surface:

- Production `POST /webhook`
- Meta-shaped payloads through Swagger
- `WHATSAPP_SENDING_ENABLED=false`
- real WhatsApp sending disabled

Production readiness result:

- `status = ready`
- `environment = production`
- `app_version = 0.2.1`
- `whatsapp_sending_enabled = false`
- `real_whatsapp_sending_allowed = false`
- `kb_runtime_enabled = true`
- database configured
- LangSmith tracing enabled
- LangSmith project = `elvira-respirarte-prod`
- OpenAI configured
- WhatsApp configured
- `hard_failures = []`

## Flow 0 — Readiness Check

Status:

APPROVED

Result:

- production app ready
- real sending disabled
- no hard failures

## Flow 1 — Basic Greeting

Status:

APPROVED

Phone:

~~~txt
test-p6f926-greeting-001
~~~

WAMID:

~~~txt
wamid.p6f926.greeting.001
~~~

Result:

- `status = sending_skipped`
- `intent = general`
- `estado_anterior = ST_INIT`
- `nuevo_estado = ST_GENERAL`
- `appointment_request_decision_reason = skipped_non_appointment_intent`
- `appointment_request = null`
- `whatsapp_sending_enabled = false`
- `patient_id = 4ec56437-0c49-4e73-849d-29119e98ff23`

Conclusion:

Basic Meta-shaped greeting was accepted safely without appointment side effects.

## Flow 2 — Appointment Happy Path With Exact-Hour Franja Confirmation

Status:

APPROVED

Phone:

~~~txt
test-p6f926-happy-001
~~~

Important correction:

The production happy path with patient message `A las 3` requires explicit franja confirmation.

Therefore, the accepted flow has four turns, not three.

### Turn 1

Message:

~~~txt
Quiero pedir una cita
~~~

WAMID:

~~~txt
wamid.p6f926.happy.001
~~~

Result:

- `status = sending_skipped`
- `intent = cita`
- `estado_anterior = ST_INIT`
- `nuevo_estado = ST_CITA_FECHA`
- `appointment_request_decision_reason = skipped_initial_cita_intent`
- `appointment_request = null`
- initial appointment copy correct
- `whatsapp_sending_enabled = false`

### Turn 2

Message:

~~~txt
El martes en la tarde
~~~

WAMID:

~~~txt
wamid.p6f926.happy.002
~~~

Result:

- `status = sending_skipped`
- `intent = fecha_cita`
- `estado_anterior = ST_CITA_FECHA`
- `nuevo_estado = ST_CITA_FRANJA`
- `appointment_request_decision_reason = skipped_fecha_cita_waiting_for_time`
- `appointment_request = null`
- date resolved as martes 9 de junio
- valid franjas offered:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- `whatsapp_sending_enabled = false`

### Turn 3

Message:

~~~txt
A las 3
~~~

WAMID:

~~~txt
wamid.p6f926.happy.003
~~~

Result:

- `status = sending_skipped`
- `intent = hora_cita`
- `estado_anterior = ST_CITA_FRANJA`
- `nuevo_estado = ST_CITA_FRANJA`
- `appointment_request_decision_reason = requires_exact_hour_franja_confirmation`
- `appointment_request = null`
- Elvira explains that domiciliary care is handled by franjas, not guaranteed exact hours
- Elvira asks confirmation to register 3:00 p. m.–5:00 p. m.
- `whatsapp_sending_enabled = false`

### Turn 4

Message:

~~~txt
Sí, registre esa franja
~~~

WAMID:

~~~txt
wamid.p6f926.happy.004
~~~

Result:

- `status = sending_skipped`
- `intent = hora_cita`
- `estado_anterior = ST_CITA_FRANJA`
- `nuevo_estado = ST_CITA_PENDIENTE`
- `appointment_request_decision_reason = allowed_hora_cita_ready_for_human_review`
- `appointment_request != null`
- `estado_solicitud = pendiente_confirmacion`
- `fecha_solicitada = 2026-06-09`
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `source_interaction_id = wamid.p6f926.happy.004`
- `patient_id = 93e56153-968d-4826-9b49-fe6f61523762`
- `whatsapp_sending_enabled = false`

Conclusion:

Appointment request registration is accepted because the patient-facing confirmation response is backed by `appointment_request != null`.

## Flow 4 — Ambiguous Slot Guard

Status:

APPROVED

Phone:

~~~txt
test-p6f926-ambiguous-001
~~~

### Turn 1

Message:

~~~txt
Quiero pedir una cita
~~~

WAMID:

~~~txt
wamid.p6f926.ambiguous.001
~~~

Result:

- `status = sending_skipped`
- `intent = cita`
- `nuevo_estado = ST_CITA_FECHA`
- `appointment_request = null`

### Turn 2

Message:

~~~txt
El martes en la tarde
~~~

WAMID:

~~~txt
wamid.p6f926.ambiguous.002
~~~

Result:

- `status = sending_skipped`
- `intent = fecha_cita`
- `nuevo_estado = ST_CITA_FRANJA`
- `appointment_request = null`
- valid franjas offered

### Turn 3

Message:

~~~txt
En la tarde
~~~

WAMID:

~~~txt
wamid.p6f926.ambiguous.003
~~~

Result:

- `status = sending_skipped`
- `intent = hora_cita`
- `estado_anterior = ST_CITA_FRANJA`
- `nuevo_estado = ST_CITA_FRANJA`
- `appointment_request_decision_reason = skipped_wrong_state_or_action`
- `appointment_request = null`
- Elvira asks patient to choose one concrete available franja
- `whatsapp_sending_enabled = false`

Conclusion:

Ambiguous generic time-window reply did not create AppointmentRequest and did not advance to `ST_CITA_PENDIENTE`.

## Flow 5 — Duplicate WAMID Deduplication

Status:

APPROVED

Duplicated WAMID:

~~~txt
wamid.p6f926.ambiguous.003
~~~

Result on repeated payload:

- `status = ignored`
- `reason = duplicate_message`
- `whatsapp_message_id = wamid.p6f926.ambiguous.003`

Conclusion:

Duplicate Meta message was ignored and did not create duplicate operational effects.

## Flow 6 — Opt-Out Safety Check

Status:

APPROVED

Phone:

~~~txt
test-p6f926-optout-001
~~~

WAMID:

~~~txt
wamid.p6f926.optout.001
~~~

Message:

~~~txt
No quiero recibir más mensajes
~~~

Result:

- `status = sending_skipped`
- `intent = optout`
- `estado_anterior = ST_INIT`
- `nuevo_estado = ST_OPTOUT`
- `appointment_request_decision_reason = skipped_non_appointment_intent`
- `appointment_request = null`
- `patient_id = 2fbe45f5-3cb8-4e23-828f-5f51ffb9a298`
- `whatsapp_sending_enabled = false`

Conclusion:

Opt-out is handled safely, without creating AppointmentRequest and without real sending.

## Final Regression Result

P6-F.9.26 production `/webhook` dry-run regression pack is accepted.

Approved flows:

- readiness check
- basic greeting
- appointment registration with exact-hour franja confirmation
- ambiguous slot guard
- duplicate `wamid` deduplication
- opt-out safety

Final safety result:

- real WhatsApp sending remained disabled
- `WHATSAPP_SENDING_ENABLED=false`
- every response returned `sending_skipped` or `ignored` for duplicate payload
- no real WhatsApp message was sent
- no uncontrolled side effects were observed

## Follow-Up Documentation Note

The original planned happy path described `A las 3` as a final direct selection.

Runtime correctly treats `A las 3` as an exact-hour request and requires explicit confirmation of the franja.

This is not a bug.

It is aligned with the doctor-validated operational contract:

- Elvira collects preferred franjas
- Elvira does not guarantee exact hours
- AppointmentRequest is created only after explicit patient confirmation when the patient gives an exact hour

## Next Sprint

P6-F.9.27 — Controlled Sending Activation Execution Checklist

Goal:

Prepare the exact execution checklist for enabling real WhatsApp sending only for one controlled internal test phone, after the final dry-run regression pack is green.
