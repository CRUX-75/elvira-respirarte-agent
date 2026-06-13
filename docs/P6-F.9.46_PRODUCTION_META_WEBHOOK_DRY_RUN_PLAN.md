# P6-F.9.46 — Production Meta Webhook Dry-Run Plan

## Status

PLANNED

## Objective

Prepare a controlled production dry-run to validate that Meta can deliver a real inbound WhatsApp webhook event to the production `/webhook` endpoint while keeping outbound WhatsApp sending disabled.

This phase validates real production ingress only.

It does not activate outbound WhatsApp sending.

## Safety Baseline

Mandatory safety rules:

- `WHATSAPP_SENDING_ENABLED=false`
- Do not enable real outbound WhatsApp sending.
- Do not contact real patients.
- Do not run campaigns.
- Do not add Google Sheets.
- Do not add Telegram.
- Do not add n8n workflows.
- Do not add Calendar integration.
- Do not add doctor confirmation automation.
- Do not change runtime code unless a real blocker is found.

Real outbound WhatsApp sending remains out of scope.

## Existing Documentation Reviewed

This phase intentionally builds on the existing production readiness and webhook dry-run documentation instead of duplicating it.

Relevant existing docs:

- `docs/P6-F.9.25_CONTROLLED_WHATSAPP_SENDING_ACTIVATION_PLAN.md`
- `docs/P6-F.9.26_FINAL_WEBHOOK_DRY_RUN_REGRESSION_PACK.md`
- `docs/P6-F.9.43_PRODUCTION_READINESS_CHECKLIST.md`

P6-F.9.46 is narrower than those documents.

Its purpose is only to plan the first real Meta-to-production inbound webhook dry-run with sending disabled.

## Scope

This phase covers:

1. Confirming production safety configuration.
2. Confirming Meta can reach production `/webhook`.
3. Receiving one controlled inbound webhook event from Meta.
4. Validating logs.
5. Validating database side effects.
6. Confirming `delivery_status=sending_skipped`.
7. Confirming no outbound WhatsApp send occurred.
8. Defining stop conditions and rollback.
9. Documenting the final result.

## Out of Scope

Do not implement or activate:

- `WHATSAPP_SENDING_ENABLED=true`
- uncontrolled real patient testing
- Google Sheets adapter
- Telegram notification flow
- n8n automation
- Calendar integration
- doctor confirmation automation
- campaigns
- therapy/session package tracking

## Preconditions

Before executing the dry-run, confirm:

- Production deployment is live.
- Production `/webhook` endpoint is reachable.
- Meta webhook configuration points to the production endpoint.
- Meta webhook verification is already passing or can be revalidated.
- `WHATSAPP_SENDING_ENABLED=false` in production.
- Production database is connected.
- Production logs are accessible through EasyPanel.
- WhatsApp Cloud API credentials are present, but sending remains disabled by feature flag.
- Test message will come from a controlled internal/test number only.
- No real patient is used.

## Expected Inbound Test

Use one controlled inbound WhatsApp text message.

Recommended first message:

~~~text
Hola, prueba controlada
~~~

This first dry-run should not start an appointment flow.

The first goal is only to prove safe inbound delivery, parsing, persistence, deduplication, and skipped sending.

## Expected Meta Payload Type

The webhook should receive a real Meta-shaped WhatsApp payload containing:

- `object = whatsapp_business_account`
- `entry`
- `changes`
- `value.messages`
- text message body
- sender phone number
- contact profile name if available
- real Meta `wamid`
- timestamp
- message type `text`

Status notifications must continue to be ignored safely.

Unsupported message types must continue to be ignored safely.

Duplicate `wamid` values must not create duplicate operational effects.

## Execution Plan

### 1. Confirm safety flag in production

Confirm in EasyPanel environment variables:

~~~text
WHATSAPP_SENDING_ENABLED=false
~~~

If this is not false, stop immediately.

### 2. Open production logs

Open EasyPanel logs before sending the test message.

Confirm:

- no startup errors
- no webhook error loop
- no send attempts
- app is healthy

### 3. Send one controlled inbound WhatsApp message

From the internal test phone, send:

~~~text
Hola, prueba controlada
~~~

Do not use a real patient phone.

Do not start an appointment flow in this first test.

### 4. Validate logs

Expected production evidence:

- `/webhook` receives the event.
- Payload extraction succeeds.
- Message type is accepted as text.
- `telefono` is extracted.
- `mensaje` is extracted.
- real `whatsapp_message_id` is preserved.
- patient is loaded or created.
- processing completes without 500.
- outbound sending is skipped.

Expected safety evidence:

~~~text
delivery_status=sending_skipped
whatsapp_sending_enabled=false
~~~

### 5. Validate PostgreSQL

Run read-only checks in pgweb.

Suggested queries:

~~~sql
SELECT telefono, estado_actual, updated_at
FROM patients
ORDER BY updated_at DESC
LIMIT 5;

SELECT telefono, mensaje_usuario, delivery_status, created_at
FROM interactions
ORDER BY created_at DESC
LIMIT 5;

SELECT whatsapp_message_id, processed_at
FROM processed_messages
ORDER BY processed_at DESC
LIMIT 5;

SELECT id_solicitud, telefono, estado_solicitud, fecha_solicitada, franja_solicitada, created_at
FROM appointment_requests
ORDER BY created_at DESC
LIMIT 5;
~~~

Expected result for the simple greeting:

- patient row exists or was reused
- interaction row exists
- `delivery_status=sending_skipped`
- real Meta `wamid` appears in `processed_messages`
- no new AppointmentRequest is created from a simple greeting

### 6. Confirm no outbound WhatsApp send

Confirm all of the following:

- `WHATSAPP_SENDING_ENABLED=false`
- logs show sending skipped
- no WhatsApp send request was attempted
- no automated WhatsApp reply was received by the test phone
- no unexpected send appears in Meta dashboard
- no send failure appears in logs

## Stop Conditions

Stop immediately if:

- `WHATSAPP_SENDING_ENABLED` is not false
- `/webhook` returns 500
- Meta retries repeatedly
- duplicate `wamid` creates duplicate effects
- outbound WhatsApp sending is attempted
- an automated WhatsApp reply is received
- a real patient is contacted
- AppointmentRequest is created from a simple greeting
- logs show unexpected runtime errors

## Rollback

If anything unsafe happens:

1. Keep or reset `WHATSAPP_SENDING_ENABLED=false`.
2. Disable/pause Meta webhook delivery if needed.
3. Stop all further tests.
4. Review EasyPanel logs.
5. Review latest PostgreSQL rows.
6. Document the failure.
7. Do not continue activation until the root cause is fixed and locally tested.

## Optional Follow-Up

Only after the simple inbound dry-run is successful, a separate controlled appointment dry-run may be planned.

Suggested future block:

`P6-F.9.47 — Controlled Production Appointment Dry-Run With Test Number And Sending Disabled`

That future block may validate:

1. `Quiero pedir una cita`
2. `para el miércoles`
3. `sí, esa franja`

Expected future appointment result:

- `appointment_request != null`
- `estado_solicitud=pendiente_confirmacion`
- `delivery_status=sending_skipped`
- no outbound WhatsApp message sent
- Elvira does not confirm the appointment

## Closure Criteria

P6-F.9.46 can be closed only when:

- production receives a real Meta webhook event
- payload is parsed correctly
- patient/interactions/processed_messages evidence is confirmed
- `delivery_status=sending_skipped` is confirmed
- no outbound WhatsApp message is sent
- no real patient is contacted
- no AppointmentRequest is created from the simple greeting
- logs show no critical errors
- result is documented in `AI_CONTEXT.md`
- working tree is clean after commit

## Closure Note Template

~~~md
## P6-F.9.46 Closure Note — Production Meta Webhook Dry-Run

Status:

CLOSED / PRODUCTION INBOUND META WEBHOOK VALIDATED / SENDING DISABLED

Validated:

- Real Meta webhook reached production `/webhook`.
- Payload was parsed correctly.
- Patient row was created or reused.
- Interaction was saved.
- Real Meta `wamid` was marked as processed.
- `delivery_status=sending_skipped` confirmed.
- `WHATSAPP_SENDING_ENABLED=false` confirmed.
- No outbound WhatsApp message was sent.
- No real patient was contacted.
- No AppointmentRequest was created from the simple greeting.

Conclusion:

Production inbound webhook reception is validated with sending disabled.

Next recommended block:

P6-F.9.47 — Controlled Production Appointment Dry-Run With Test Number And Sending Disabled
~~~
