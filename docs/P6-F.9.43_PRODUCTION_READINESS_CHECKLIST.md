# P6-F.9.43 — Production Readiness Checklist / Controlled Activation Preparation

## Status

DRAFT / PRE-ACTIVATION ONLY

## Objective

Prepare the controlled production activation checklist before touching the real WhatsApp Cloud API webhook or enabling real outbound WhatsApp sending.

This phase does not activate production sending.

## Current Safety Baseline

- `WHATSAPP_SENDING_ENABLED=false`
- Real `/webhook` must not be changed yet.
- Real patients must not be contacted.
- `/test/message-stateful` remains the validated safe surface.
- AppointmentRequest persistence has been validated in P6-F.9.42.
- AppointmentRequest rows persist correctly in PostgreSQL.
- Patient state persists correctly as `ST_CITA_PENDIENTE`.
- `appointment_context` is cleared after successful persistence.
- Duplicate active requests are prevented.

## Activation Principle

Production activation must be controlled, reversible, and observable.

Do not activate real sending until all checklist items are reviewed.

## Pre-Activation Checklist

### 1. Environment Variables

Confirm production environment values without changing them:

- `WHATSAPP_SENDING_ENABLED=false`
- WhatsApp Cloud API token exists
- WhatsApp phone number ID exists
- WhatsApp verify token exists
- Database URL points to the intended production PostgreSQL
- OpenAI key exists
- LangSmith configuration exists if tracing is enabled
- KB runtime configuration is correct

No secrets should be committed to Git.

### 2. Database Readiness

Confirm required production tables exist:

- `patients`
- `interactions`
- `appointment_requests`
- KB tables used by runtime schedules/rules

Confirm AppointmentRequest contract:

- Active statuses:
  - `nueva`
  - `pendiente_datos`
  - `pendiente_confirmacion`
  - `confirmada`
  - `reagendada`
- Terminal statuses:
  - `cancelada`
  - `cerrada`

Confirm no invalid statuses are used:

- `pendiente`
- `contraoferta`
- `completada`

### 3. KB Runtime Readiness

Confirm production KB reflects the intended schedule:

- Monday, Tuesday, Thursday, Friday:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- Wednesday:
  - 3:00 p. m.–6:00 p. m.
- Saturday:
  - unavailable
- Sunday:
  - unavailable
- Colombia holidays:
  - unavailable unless explicitly overridden later

Confirm Elvira does not confirm final appointments.

Elvira only registers patient preference/request for human review.

### 4. Endpoint Safety

Before touching real WhatsApp traffic:

- Keep `/test/message-stateful` as validation endpoint.
- Do not enable real outbound sending.
- Do not run real patient tests.
- Do not connect campaigns.
- Do not add Google Sheets, Telegram, n8n, or Calendar in this block.

### 5. Webhook Readiness Review

Before activating real `/webhook`, review:

- duplicate message guard
- message ID handling
- patient lookup/upsert
- state persistence
- interaction logging
- appointment context capture/clear behavior
- AppointmentRequest persistence behavior
- safe response behavior when sending is disabled
- error handling and logs

### 6. Controlled Test Plan Before Real Sending

Run with `/test/message-stateful`:

#### Happy path — Wednesday single-slot

- `Quiero pedir una cita`
- `para el miercoles`
- `sí, esa franja`

Expected:

- `ST_CITA_PENDIENTE`
- `appointment_request != null`
- `estado_solicitud = pendiente_confirmacion`
- `appointment_context = null`
- no duplicate active requests

#### Multi-slot explicit selection

- `Quiero pedir una cita`
- `para el martes`
- `la de las 5`

Expected:

- `ST_CITA_PENDIENTE`
- `franja_solicitada = 5:00 p. m.–7:00 p. m.`
- `appointment_request != null`

#### Multi-slot ambiguous blocked

- `Quiero pedir una cita`
- `para el martes`
- `sí, esa franja`

Expected:

- no `AppointmentRequest`
- patient remains in slot-selection state
- no false “queda registrada” message

#### Weekend blocked

- `Quiero pedir una cita`
- `para el domingo`

Expected:

- unavailable date response
- no `AppointmentRequest`

#### Exact-hour clarification

- `Quiero pedir una cita`
- `para el miercoles`
- `se puede a las 4?`

Expected:

- explain franja policy
- do not persist immediately
- ask for confirmation of available franja

### 7. Observability Checklist

Before controlled activation, confirm access to:

- EasyPanel logs
- PostgreSQL / pgweb
- LangSmith traces if enabled
- WhatsApp Cloud API dashboard
- Git commit history
- environment variable panel

### 8. Rollback Plan

If controlled activation fails:

1. Set `WHATSAPP_SENDING_ENABLED=false`.
2. Verify app restarts with sending disabled.
3. Stop real outbound messages.
4. Inspect logs.
5. Inspect `interactions`.
6. Inspect `patients`.
7. Inspect `appointment_requests`.
8. Do not patch blindly.
9. Document failure mode.
10. Reproduce through `/test/message-stateful`.

### 9. Explicit Non-Goals

This block does not implement:

- Google Sheets handoff
- Telegram doctor notification
- n8n integration
- Calendar integration
- doctor confirmation automation
- campaign sending
- therapy package/session tracking
- real WhatsApp sending

## Closure Criteria

P6-F.9.43 can close when:

- This checklist exists.
- Production env values have been reviewed without exposing secrets.
- DB schema readiness has been checked.
- KB runtime readiness has been checked.
- `/test/message-stateful` controlled scenarios are revalidated if needed.
- No real WhatsApp sending has been enabled.
- `WHATSAPP_SENDING_ENABLED=false` remains unchanged.
- Working tree is clean after documentation commit.

## Next Block After Closure

P6-F.9.44 — Real Webhook Readiness Review

Purpose:

Review the real `/webhook` path before any controlled activation.

Still no real outbound sending unless explicitly opened as a separate controlled activation block.
