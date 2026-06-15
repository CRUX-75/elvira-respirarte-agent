# P6-F.9.75 — Controlled Google Sheets Contract Validation

## Status

PLANNED

## Objective

Validate in controlled mode that the Google Sheets human review inbox writer can append and update `Solicitudes_Cita` rows using the expanded AppointmentRequest contract.

The validation must confirm that the following new operational fields are mapped correctly:

- `tipo_cita`
- `eps`
- `barrio`
- `edad_paciente`
- `notas_clinicas_breves`

## Context

P6-F.9.74 confirmed production PostgreSQL alignment for the expanded Human Review Inbox operational fields.

The production `appointment_requests` table now includes:

- `tipo_cita` text nullable
- `eps` text nullable
- `barrio` text nullable
- `edad_paciente` integer nullable
- `notas_clinicas_breves` text nullable

## Scope

This phase validates the Google Sheets writer contract only.

Validation must include:

1. Controlled append with the expanded fields.
2. Controlled update of the same `id_solicitud`.
3. Confirmation that doctor-owned columns are preserved during update.
4. Confirmation that backend-owned expanded fields are written correctly.
5. Confirmation that Google Sheets remains an auxiliary human-visible inbox.
6. Confirmation that PostgreSQL remains the source of truth.

## Out of Scope

Do not touch:

- Real WhatsApp sending
- Real patient activation
- Telegram
- n8n
- Calendar
- Doctor confirmation automation
- Patient-facing missing-data automation
- Campaigns
- Webhook activation
- Default enabling of Google Sheets

## Safety Baseline

- `WHATSAPP_SENDING_ENABLED=false`
- `GOOGLE_SHEETS_ENABLED=false` by default
- `KB_RUNTIME_ENABLED=true`

Google Sheets may only be enabled temporarily for this named controlled validation block.

## Expected Validation Evidence

Append validation:

- A controlled test `AppointmentRequest` is written to Google Sheets.
- Result is `appended`.
- The row contains the expanded operational fields.

Update validation:

- The same controlled `id_solicitud` is written again with changed values.
- Result is `updated`.
- The existing row is updated instead of duplicated.
- Doctor-owned fields are preserved.

## Closure Criteria

P6-F.9.75 can be closed only when:

- Targeted Google Sheets writer tests are GREEN.
- The controlled append/update validation succeeds.
- The expanded fields are visually or programmatically confirmed in Google Sheets.
- `GOOGLE_SHEETS_ENABLED=false` is restored after validation.
- `WHATSAPP_SENDING_ENABLED=false` remains unchanged.
- No real patient flow is touched.
- The result is documented in `AI_CONTEXT.md`.
- The working tree is clean.
