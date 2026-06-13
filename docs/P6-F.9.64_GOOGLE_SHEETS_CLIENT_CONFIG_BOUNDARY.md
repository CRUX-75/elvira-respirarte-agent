# P6-F.9.64 — Google Sheets Client Config Boundary

## Status

SPEC / CONFIG BOUNDARY

## Objective

Prepare the safe configuration boundary for the future Google Sheets writer runtime integration.

This phase does not connect the writer to the appointment runtime yet.

## Scope

Add configuration fields required for Google Sheets integration:

- google_sheets_enabled
- google_sheets_spreadsheet_id
- google_sheets_solicitudes_cita_tab
- google_service_account_json

Add Google API dependencies if needed.

Validate that Google Sheets remains disabled by default.

## Safety Rule

GOOGLE_SHEETS_ENABLED must default to false.

The system must not write to Google Sheets unless explicitly enabled.

WHATSAPP_SENDING_ENABLED must remain false.

## Out Of Scope

Do not implement:

- runtime wiring
- automatic Sheets writes from /webhook
- doctor action reader
- patient notification sending
- Telegram
- n8n
- Calendar
- campaigns
- doctor confirmation automation

## Expected Environment Variables

GOOGLE_SHEETS_ENABLED=false
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SHEETS_SOLICITUDES_CITA_TAB=Solicitudes_Cita
GOOGLE_SERVICE_ACCOUNT_JSON=

## Closure Criteria

- Config fields exist.
- Defaults are safe.
- Tests prove Google Sheets is disabled by default.
- Targeted tests green.
- Full suite green.
- No runtime writes to Google Sheets.
