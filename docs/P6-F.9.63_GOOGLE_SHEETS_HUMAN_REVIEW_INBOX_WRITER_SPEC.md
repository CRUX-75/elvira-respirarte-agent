# P6-F.9.63 — Google Sheets Human Review Inbox Writer

## Status

SPEC / PRE-IMPLEMENTATION

## Objective

Implement the first safe Google Sheets adapter that writes pending AppointmentRequests from PostgreSQL/backend runtime into the `Solicitudes_Cita` Google Sheet.

PostgreSQL remains the source of truth.

Google Sheets is only the human-facing inbox for Dra. D'Aleman.

## Scope

This phase implements only the writer side:

AppointmentRequest
→ Google Sheets row mapping
→ append row if id_solicitud does not exist
→ update row if id_solicitud already exists

## Out Of Scope

Do not implement:

- doctor action reader
- patient notification sending
- Telegram
- n8n
- Calendar
- campaigns
- therapy session tracking
- automatic doctor confirmation
- uncontrolled production activation

## Safety Baseline

WHATSAPP_SENDING_ENABLED must remain false.

GOOGLE_SHEETS_ENABLED must default to false.

The writer must not run unless explicitly enabled.

## Target Sheet

Spreadsheet:

Respirarte CRM

Tab:

Solicitudes_Cita

## Sheet Columns

- id_solicitud
- fecha_registro
- telefono
- nombre_paciente
- fecha_solicitada_texto
- franja_solicitada
- modalidad
- estado_solicitud
- observaciones_elvira
- interaction_id_origen
- direccion_domicilio
- servicio_solicitado
- fecha_confirmada
- franja_confirmada
- accion_doctora
- motivo_decision
- revisado_por
- fecha_revision
- sync_status
- last_sync_at
- sync_error

## Writer Contract

The writer receives an AppointmentRequest model.

It maps backend fields to the sheet columns.

If `id_solicitud` exists in the sheet:

- update the existing row

If `id_solicitud` does not exist:

- append a new row

## Backend-Owned Sheet Fields

The writer owns:

- id_solicitud
- fecha_registro
- telefono
- nombre_paciente
- fecha_solicitada_texto
- franja_solicitada
- modalidad
- estado_solicitud
- observaciones_elvira
- interaction_id_origen
- direccion_domicilio
- servicio_solicitado
- fecha_confirmada
- franja_confirmada
- sync_status
- last_sync_at
- sync_error

## Doctor-Owned Fields

The writer must not overwrite doctor-owned fields once they contain values:

- accion_doctora
- motivo_decision
- revisado_por
- fecha_revision

## Required Tests

Create tests proving:

1. AppointmentRequest maps to expected sheet row.
2. Missing optional fields become empty strings.
3. Existing doctor-owned values are preserved on update.
4. Existing row is updated by id_solicitud.
5. Missing row is appended.
6. Writer is skipped when GOOGLE_SHEETS_ENABLED=false.

## Recommended Implementation Files

- app/adapters/google_sheets_human_review_writer.py
- tests/test_google_sheets_human_review_writer.py

## Recommended Config Fields

- google_sheets_enabled
- google_sheets_spreadsheet_id
- google_sheets_solicitudes_cita_tab
- google_service_account_json

## Closure Criteria

- Spec exists.
- Tests added RED first.
- Minimal writer implemented.
- Targeted tests GREEN.
- Full suite GREEN.
- No production Google Sheets write unless explicitly enabled.
- Working tree clean.
