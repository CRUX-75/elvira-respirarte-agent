# P6-F.9.24 — Production MVP Activation SDD

## Status

DRAFT / READY FOR REVIEW

## Objective

Prepare the controlled production activation roadmap for the Elvira / Respirarte MVP after the exact-hour franja confirmation persistence bug was fixed and verified through:

- local automated tests
- deployed `/webhook` Meta-shaped dry-run
- PostgreSQL `appointment_requests` DB evidence

This sprint does not activate real WhatsApp sending yet.

## Current Baseline

P6-F.9.23 is closed:

- exact-hour franja confirmation persists AppointmentRequest correctly
- `/webhook` Meta-shaped flow passed
- `WHATSAPP_SENDING_ENABLED=false`
- PostgreSQL row verified in `appointment_requests`
- Elvira only says the request was received when `appointment_request != null`

Current validation baseline:

- `pytest -q` → `216 passed`

## Scope

This sprint prepares MVP production activation.

In scope:

- review current production readiness
- define controlled activation checklist
- define first real pilot boundaries
- define rollback rules
- define monitoring rules
- confirm required E2E validation gates before enabling real sending

Out of scope:

- Google Sheets sync
- Telegram notification
- n8n workflows
- Calendar integration
- doctor confirmation automation
- therapy session tracking
- uncontrolled WhatsApp sending
- broad refactors

## Safety Rule

`WHATSAPP_SENDING_ENABLED=false` remains active during this sprint.

No real WhatsApp sending is allowed until a later explicitly approved controlled sending activation sprint.

## Production Readiness Checklist

Before real sending can be considered, the following must be confirmed:

1. `/ready` returns:
   - `status = ready`
   - `whatsapp_sending_enabled = false`
   - `real_whatsapp_sending_allowed = false`

2. `/webhook` accepts Meta-shaped payloads.

3. `processed_messages` deduplication protects repeated `wamid` values.

4. `interactions` stores enough audit information:
   - user message
   - Elvira response
   - intent
   - previous state
   - new state
   - next_action
   - state_reason
   - delivery_status

5. `appointment_requests` remains the source of truth for appointment requests.

6. The appointment request flow has at least one full passing E2E validation:
   - fresh phone
   - fresh `wamid` per turn
   - final `appointment_request != null`
   - correct PostgreSQL row

## Conversational E2E Acceptance Rule

For any production conversation flow:

A response is not trusted unless the expected DB effect exists.

For appointment requests:

~~~txt
appointment_request != null
and appointment_requests contains the correct row in PostgreSQL
~~~

A response such as:

~~~txt
Hemos recibido su solicitud...
~~~

is valid only when:

~~~txt
appointment_request != null
and appointment_requests.estado_solicitud = pendiente_confirmacion
~~~

## Required E2E Evidence

Every accepted production-readiness conversation must capture:

- endpoint used
- test phone
- fresh `wamid` values
- request payloads
- response payloads
- `WHATSAPP_SENDING_ENABLED` value
- `delivery_status`
- `estado_anterior`
- `nuevo_estado`
- `intent`
- `next_action`
- `appointment_request_decision.reason`
- `appointment_request`
- PostgreSQL `appointment_requests` row
- `source_interaction_id` matching the final `wamid`

## Blocking Conditions

Real sending must not be enabled if any of the following happens:

- Elvira says the request was received but `appointment_request = null`
- the PostgreSQL `appointment_requests` row is missing
- the appointment request row has the wrong date
- the appointment request row has the wrong franja
- duplicate `wamid` values create duplicate operational effects
- `/webhook` sends a real WhatsApp message while `WHATSAPP_SENDING_ENABLED=false`
- Elvira confirms final appointment availability automatically
- Elvira promises an exact hour inside a franja
- the patient reaches `ST_CITA_PENDIENTE` without a valid persisted AppointmentRequest

## Pilot Boundaries

The first real production pilot must be limited.

Allowed:

- one dedicated Respirarte WhatsApp Cloud API number
- one or a very small number of controlled test phones
- controlled patient-style test conversations
- manual DB verification after each test flow
- immediate rollback by disabling sending

Not allowed:

- public patient traffic
- mass messaging
- marketing campaigns
- doctor confirmation automation
- Google Sheets operational dependency
- Telegram dependency
- n8n dependency
- Calendar dependency

## Rollback Rules

If a critical issue appears:

1. keep or restore `WHATSAPP_SENDING_ENABLED=false`
2. stop real testing immediately
3. preserve request/response payloads
4. preserve DB evidence
5. document the failing flow
6. fix with automated tests first
7. rerun `pytest -q`
8. rerun `/test/message-stateful`
9. rerun `/webhook` Meta-shaped dry-run
10. verify PostgreSQL effect again

## Acceptance Criteria

This sprint is accepted only if it produces a clear controlled production activation plan.

The plan must define:

- what can be activated
- what must remain disabled
- which test phone(s) are allowed
- how to verify successful real message sending later
- how to stop sending immediately
- how to validate DB effects after real conversations
- how to monitor failed delivery or failed persistence

## Proposed Next Sprint After This

P6-F.9.25 — Controlled WhatsApp Sending Activation Plan

Goal:

Prepare the exact technical and operational steps to enable real WhatsApp sending for a very small controlled pilot.

This future sprint may decide when and how to change:

~~~txt
WHATSAPP_SENDING_ENABLED=true
~~~

But P6-F.9.24 must not enable it.

## Definition of Done

P6-F.9.24 is closed only when:

- this SDD is committed
- the production MVP activation roadmap is explicit
- `WHATSAPP_SENDING_ENABLED=false` remains unchanged
- E2E acceptance requires DB evidence
- rollback rules are documented
- the next sprint is clearly defined
