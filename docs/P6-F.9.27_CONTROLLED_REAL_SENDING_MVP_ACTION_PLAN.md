# P6-F.9.27 — Controlled Real Sending MVP Action Plan

## Status

DRAFT / MVP ACTION PLAN / CONTROLLED REAL SENDING PREP

## Objective

Prepare the concrete MVP action plan to move Elvira / Respirarte from successful production webhook dry-runs to the first controlled real WhatsApp sending test.

This sprint prepares the execution path for real sending with one internal controlled phone only.

It must not open public patient traffic.

## Current Baseline

Latest closed sprint:

P6-F.9.26 — Final Webhook Dry-Run Regression Pack

Status:

CLOSED / GREEN / COMMITTED / PRODUCTION WEBHOOK DRY-RUN REGRESSION APPROVED / REAL SENDING DISABLED

Validated:

- production `/ready` GREEN
- production `POST /webhook` accepts Meta-shaped payloads
- WhatsApp `messages` webhook subscription is active
- App is Live in Meta
- real WhatsApp inbound has already been tested previously with the German number
- `WHATSAPP_SENDING_ENABLED=false`
- `real_whatsapp_sending_allowed=false`
- LangSmith tracing enabled
- PostgreSQL operational persistence validated
- duplicate `wamid` deduplication validated
- opt-out validated
- appointment request persistence validated

Latest local validation:

~~~txt
pytest -q → 217 passed
~~~

## Important Current Reality

Infrastructure is already more advanced than originally assumed.

Confirmed by Meta configuration:

- Respirarte-WA-bot app exists
- App mode is Live
- WhatsApp product is configured
- Webhook subscription for `messages` is active
- API version v25.0 is selected
- Templates exist and are active
- German WhatsApp number is connected
- Colombian number exists in WABA but may still need verification / final readiness confirmation

Therefore, the next real milestone is no longer more dry-run planning.

The next real milestone is controlled real sending with strict rollback.

## MVP Principle

The MVP does not need Google Sheets, Telegram, n8n, Calendar, or doctor automation yet.

The first MVP production goal is:

~~~txt
A controlled patient-style WhatsApp conversation reaches Elvira,
Elvira replies through WhatsApp,
DB state is persisted,
LangSmith trace exists,
AppointmentRequest is created only when valid,
and rollback remains immediate.
~~~

## Scope

In scope:

- controlled real sending activation
- one internal test phone only
- one WhatsApp number only
- one short greeting test
- one appointment registration test
- DB verification
- LangSmith verification
- rollback to disabled sending

Out of scope:

- public patient traffic
- real patient testing
- mass messaging
- marketing campaigns
- Google Sheets sync
- Telegram notification
- n8n workflows
- Calendar integration
- doctor confirmation automation
- therapy sessions module
- broad refactors

## Number Strategy

There are two possible paths.

### Option A — German Number First

Use the already connected German WhatsApp number for the first controlled real sending test.

Recommended if:

- German number is already fully connected
- webhook inbound is already known to work
- fastest safe path is desired

Purpose:

Validate backend sending behavior end-to-end before involving the Colombian Respirarte number.

### Option B — Colombian Number First

Use the Colombian Respirarte number only if it is fully verified / connected in WhatsApp Manager.

Required before using it:

- number status must not be `Nicht verifiziert`
- number must be able to receive inbound WhatsApp messages through Cloud API
- webhook must receive real inbound events
- credentials and phone_number_id must match the Colombian number

Recommendation:

If Colombian number is still not verified, do not block MVP engineering on it.

Run first controlled sending test with the connected German number, then repeat later with the Colombian number after verification.

## Safety Rule

Before controlled sending execution:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

During controlled sending execution:

~~~txt
WHATSAPP_SENDING_ENABLED=true
~~~

is allowed only temporarily and only for the controlled test.

After the controlled test:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

must be restored unless a later sprint explicitly approves keeping it on.

## Controlled Test Phone

Only one internal phone may be used.

Before activation, document:

- test phone owner
- test phone number
- selected WhatsApp business number
- start time
- rollback method
- expected flow

No unknown patient phones.

No public links.

No public launch.

## Pre-Activation Checklist

Before setting `WHATSAPP_SENDING_ENABLED=true`, confirm:

1. Local repo is clean:

~~~bash
git status --short
~~~

2. Local tests are green:

~~~bash
pytest -q
~~~

Expected:

~~~txt
217 passed
~~~

3. Production `/ready` shows:

- `status = ready`
- `whatsapp_sending_enabled = false`
- `real_whatsapp_sending_allowed = false`
- `hard_failures = []`
- DB configured
- WhatsApp configured
- LangSmith configured

4. Selected WhatsApp number is known:

- German number or Colombian number
- correct `WHATSAPP_PHONE_NUMBER_ID`
- correct token
- webhook `messages` subscribed

5. Rollback is ready:

- know where to set `WHATSAPP_SENDING_ENABLED=false`
- know how to redeploy/restart
- know how to confirm `/ready` after rollback

## Execution Plan — First Controlled Real Sending Test

### Step 1 — Confirm Disabled Baseline

Call production `/ready`.

Expected:

~~~txt
whatsapp_sending_enabled = false
real_whatsapp_sending_allowed = false
~~~

### Step 2 — Enable Sending Temporarily

Set production environment:

~~~txt
WHATSAPP_SENDING_ENABLED=true
~~~

Redeploy or restart the app according to the production platform.

### Step 3 — Confirm Enabled State

Call production `/ready`.

Expected:

~~~txt
whatsapp_sending_enabled = true
real_whatsapp_sending_allowed = true
~~~

If `/ready` does not show both true, stop.

### Step 4 — Send First Real WhatsApp Message

From the internal controlled phone, send:

~~~txt
Hola buenos días
~~~

Expected:

- Elvira replies in WhatsApp
- no AppointmentRequest is created
- `intent = general`
- interaction row exists
- processed message row exists
- patient row exists/updates
- LangSmith trace exists

### Step 5 — Verify Evidence

Verify:

- WhatsApp reply received on phone
- production logs have no 500
- LangSmith trace exists
- `processed_messages` contains real `wamid`
- `interactions` contains real inbound/outbound audit
- `patients` state updated
- no `appointment_requests` row created for greeting

### Step 6 — Run Controlled Appointment Flow

Only if Step 4 is green.

Conversation:

~~~txt
Quiero pedir una cita
El martes en la tarde
A las 3
Sí, registre esa franja
~~~

Expected final result:

- Elvira replies through WhatsApp
- `appointment_request != null`
- `estado_solicitud = pendiente_confirmacion`
- correct `fecha_solicitada`
- correct `franja_solicitada`
- `source_interaction_id` matches final real `wamid`
- LangSmith traces exist
- no exact hour is guaranteed
- patient-facing confirmation appears only after DB persistence

### Step 7 — Disable Sending Again

After the controlled test, restore:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

Redeploy/restart.

### Step 8 — Confirm Rollback

Call `/ready`.

Expected:

~~~txt
whatsapp_sending_enabled = false
real_whatsapp_sending_allowed = false
~~~

## Acceptance Criteria

The controlled real sending MVP test is accepted only if:

- real WhatsApp response is received by the internal phone
- no uncontrolled phone receives a message
- `/ready` correctly reflects enabled state during the test
- `/ready` correctly reflects disabled state after rollback
- no 500 errors occur
- LangSmith traces exist
- DB evidence exists
- appointment request is created only after valid confirmation
- `WHATSAPP_SENDING_ENABLED=false` is restored after the test unless explicitly approved otherwise

## Hard Stop Conditions

Stop immediately and rollback if:

- Elvira sends to an unexpected phone
- `/webhook` returns 500
- WhatsApp reply is sent but DB logging fails
- appointment confirmation response appears while `appointment_request = null`
- wrong date or wrong franja is persisted
- duplicate `wamid` creates duplicate effects
- LangSmith tracing is missing
- `/ready` does not reflect the expected sending flag
- any real patient contacts the number unexpectedly

## MVP Implementation Roadmap

### Sprint P6-F.9.28 — First Controlled Real Sending Test

Execute the first real sending test with one internal phone.

Recommended path:

Use the already connected German number first if the Colombian number is not fully verified.

### Sprint P6-F.9.29 — Colombian Number Verification / Switch

Complete and validate the Colombian Respirarte number.

Repeat controlled inbound and sending tests with the Colombian number.

### Sprint P6-F.9.30 — Controlled MVP Pilot With Dra. D'Aleman

Only after the Colombian number is stable:

- one or two controlled patient-style test conversations
- no public launch
- no marketing
- manual doctor review only
- no automation of doctor confirmation

### Sprint P6-F.9.31 — Human Review Inbox Decision

Decide whether the first human-visible inbox is:

- PostgreSQL/admin view
- Google Sheets adapter
- another minimal operational surface

Do not introduce Google Sheets before controlled sending is proven stable.

## Current Decision

Proceed to first controlled real sending activation preparation.

Do not create more broad documentation before testing real sending.

Next chat should start directly with:

P6-F.9.28 — First Controlled Real Sending Test

