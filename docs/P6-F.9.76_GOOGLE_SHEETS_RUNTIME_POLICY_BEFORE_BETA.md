# P6-F.9.76 — Google Sheets Runtime Policy Before Beta

## Status

PLANNED

## Objective

Define the runtime policy for the Google Sheets human review inbox before any broader beta usage.

This phase decides whether Google Sheets should remain disabled by default, be enabled only during controlled validations, or be enabled for a doctor-facing beta process.

## Context

P6-F.9.75 validated that the Google Sheets human review inbox can receive AppointmentRequest rows in controlled runtime mode.

The validation confirmed:

- `/test/message-stateful` can create an AppointmentRequest.
- `human_review_inbox.adapter = google_sheets`
- `human_review_inbox.status = appended`
- `delivery_status = sending_skipped`
- Google Sheets received the row correctly.
- `GOOGLE_SHEETS_ENABLED=false` was restored after validation.

## Policy Decision

Default policy before beta:

`GOOGLE_SHEETS_ENABLED=false`

Reason:

Google Sheets is an auxiliary human-visible inbox, not the source of truth.

PostgreSQL remains the source of truth for AppointmentRequest lifecycle and auditability.

Google Sheets should only be enabled when there is a named controlled validation or a clearly defined doctor-facing operating process.

## Allowed Modes

### Mode 1 — Safe Development / Default

Environment:

- `GOOGLE_SHEETS_ENABLED=false`
- `WHATSAPP_SENDING_ENABLED=false`
- `KB_RUNTIME_ENABLED=true`

Use when:

- Developing locally
- Running automated tests
- Running Swagger tests that do not need Sheets
- Avoiding duplicate or noisy rows in the doctor-facing sheet

Expected behavior:

- AppointmentRequest may persist to PostgreSQL.
- Google Sheets writer is skipped.
- No human inbox row is created.

### Mode 2 — Controlled Sheets Validation

Environment:

- `GOOGLE_SHEETS_ENABLED=true`
- `WHATSAPP_SENDING_ENABLED=false`
- `KB_RUNTIME_ENABLED=true`

Use when:

- Validating Google Sheets runtime writing
- Running a named controlled phase
- Using test phone numbers only
- Operator manually observes the sheet

Expected behavior:

- AppointmentRequest persists to PostgreSQL.
- Google Sheets row is appended or updated.
- No WhatsApp message is sent.

### Mode 3 — Doctor-Facing Beta Inbox

Environment:

- `GOOGLE_SHEETS_ENABLED=true`
- `WHATSAPP_SENDING_ENABLED` must be decided by a separate named activation phase.
- `KB_RUNTIME_ENABLED=true`

Use only when:

- Dra. D'Aleman knows how to use the sheet.
- The sheet columns and manual process are explained.
- There is a defined review workflow.
- There is a fallback plan if Sheets fails.
- Patient-facing sending policy has been decided separately.

Expected behavior:

- AppointmentRequest persists to PostgreSQL.
- Google Sheets acts as visible human review inbox.
- Doctor can review requests manually.
- Google Sheets does not own lifecycle state.

## Boundaries

Google Sheets must not:

- Confirm appointments automatically.
- Override PostgreSQL as source of truth.
- Trigger patient messages directly.
- Replace backend validation.
- Become the appointment lifecycle owner.

Do not touch in this phase:

- Real WhatsApp sending
- Telegram
- n8n
- Calendar
- Doctor automation
- Campaigns
- Therapy session tracking

## Closure Criteria

P6-F.9.76 can be closed when:

- The runtime policy is documented.
- The default setting remains `GOOGLE_SHEETS_ENABLED=false`.
- The allowed activation modes are clear.
- The next beta step is named.
- No code change is required unless a documentation update is needed.
