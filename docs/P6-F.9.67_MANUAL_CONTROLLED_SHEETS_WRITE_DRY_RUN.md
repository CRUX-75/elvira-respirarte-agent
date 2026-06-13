# P6-F.9.67 — Manual Controlled Sheets Write Dry-Run

## Status

PLANNED / MANUAL ONLY

## Objective

Validate a controlled manual Google Sheets write through the existing Google Sheets adapter/factory path.

This phase must prove that the human review inbox writer can write one controlled AppointmentRequest row into Google Sheets without connecting the writer to `/webhook`, automatic runtime persistence, doctor action reading, Telegram, n8n, Calendar, or WhatsApp sending.

## Safety Baseline

- `WHATSAPP_SENDING_ENABLED=false`
- No real patient activation.
- No automatic Google Sheets write from patient conversations.
- No `/webhook` wiring.
- No runtime wiring after AppointmentRequest persistence yet.
- No doctor action reader.
- No Telegram.
- No n8n.
- No Calendar.
- No campaigns.

## Source of Truth Rule

PostgreSQL remains the source of truth.

Google Sheets is only a human-visible operational inbox adapter.

This dry-run must not make Google Sheets the lifecycle owner of AppointmentRequest.

## Scope

This phase may include:

- A manual script or controlled command to instantiate the writer through the factory.
- A controlled test AppointmentRequest object.
- One explicit manual upsert into the configured Google Sheet.
- Validation that the row appears in the `Solicitudes_Cita` tab.
- Validation that repeated upsert updates the same row instead of duplicating it.

## Out of Scope

This phase must not include:

- `/webhook` integration.
- Automatic write after AppointmentRequest persistence.
- Doctor action reader.
- Patient notifications.
- WhatsApp sending changes.
- Telegram notification.
- n8n workflow.
- Calendar integration.
- Campaigns.
- Real patient traffic.

## Required Environment Variables

The manual dry-run requires:

- `GOOGLE_SHEETS_ENABLED=true`
- `GOOGLE_SHEETS_SPREADSHEET_ID=<target spreadsheet id>`
- `GOOGLE_SHEETS_SOLICITUDES_CITA_TAB=Solicitudes_Cita`
- `GOOGLE_SERVICE_ACCOUNT_JSON=<service account json>`

## Expected Behavior

If config is incomplete:

- Factory returns `None`.
- No Google Sheets API client is created.
- No write is attempted.

If config is complete:

- Factory returns `GoogleSheetsHumanReviewWriter`.
- Manual dry-run writes one controlled row.
- Manual repeated run updates the same row by `id_solicitud`.
- Doctor-owned columns are preserved if already filled.

## Validation Plan

1. Confirm repo is clean.
2. Confirm full suite is GREEN before manual script.
3. Create a manual script under `scripts/`.
4. Run script with Google Sheets disabled and confirm no write happens.
5. Run script with Google Sheets enabled and real credentials configured locally or in controlled environment.
6. Verify the row appears in the configured sheet.
7. Run script again and verify the row is updated, not duplicated.
8. Keep `WHATSAPP_SENDING_ENABLED=false`.
9. Do not connect this to runtime.

## Closure Criteria

P6-F.9.67 can be closed only when:

- Manual script exists.
- Disabled-config path is safe.
- Enabled-config path writes one controlled request.
- Repeated run does not create duplicates.
- Full suite remains GREEN.
- Documentation is updated.
- Working tree is clean.

