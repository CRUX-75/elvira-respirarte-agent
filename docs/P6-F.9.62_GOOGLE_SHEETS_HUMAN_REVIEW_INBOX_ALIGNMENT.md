# P6-F.9.62 — Google Sheets Human Review Inbox Alignment

## Status

SPEC / ALIGNMENT ONLY

## Objective

Align the existing Google Sheets tab `Solicitudes_Cita` with the Human Review workflow.

Elvira registers appointment requests.
PostgreSQL remains the source of truth.
Google Sheets acts as the human-facing review inbox for Dra. D'Aleman.

This phase does not implement code yet.

## Existing Google Sheet

Spreadsheet:

Respirarte CRM

Tab:

Solicitudes_Cita

## Core Workflow

Patient WhatsApp message
→ Elvira appointment flow
→ AppointmentRequest persisted in PostgreSQL
→ status = pendiente_confirmacion
→ request is synced to Google Sheets
→ Dra. D'Aleman reviews the row
→ Dra. D'Aleman selects an action
→ backend reads the action in a later phase
→ HumanReviewService applies the state transition
→ PostgreSQL is updated
→ future patient notification remains out of scope

## Source Of Truth Rule

PostgreSQL remains the source of truth.

Google Sheets must not own:

- appointment lifecycle logic
- status transition logic
- validation rules
- duplicate prevention
- patient notification sending
- scheduling truth

Google Sheets is only a visual operational inbox.

## Final Sheet Columns

The `Solicitudes_Cita` tab must contain these columns:

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

## Backend-Owned Columns

These columns are written by Elvira/backend and should not be edited manually by the doctor:

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
- sync_status
- last_sync_at
- sync_error

## Doctor-Owned Columns

These columns may be edited by Dra. D'Aleman:

- accion_doctora
- fecha_confirmada
- franja_confirmada
- motivo_decision
- revisado_por
- fecha_revision

## Important Status Rule

The doctor should not manually edit `estado_solicitud`.

`estado_solicitud` is displayed for visibility only.

The doctor should choose an action in `accion_doctora`.

The backend will later translate that action into a validated HumanReviewAction and apply it through HumanReviewService.

## Allowed Doctor Actions

The allowed values for `accion_doctora` are:

- aprobar
- rechazar
- pedir_datos
- proponer_alternativa
- reagendar
- cerrar

## Backend Action Mapping

- aprobar -> confirm
- rechazar -> cancel
- pedir_datos -> request_missing_data
- proponer_alternativa -> propose_alternative
- reagendar -> reschedule
- cerrar -> close

## Writer Adapter Scope

The first implementation phase should only write pending AppointmentRequests to Google Sheets.

Trigger condition:

- AppointmentRequest exists in PostgreSQL
- estado_solicitud = pendiente_confirmacion
- request was created or updated by Elvira

The writer must be idempotent:

- if id_solicitud already exists in Sheets, update the row
- if id_solicitud does not exist in Sheets, append a new row

## Reader Adapter Scope

The reader is a later phase.

It should read only rows where:

- accion_doctora is not empty
- sync_status = pendiente

Then it should:

- build HumanReviewAction
- call HumanReviewService.apply_action(...)
- update PostgreSQL
- mark sync_status = procesado or error
- write sync_error when needed

## Safety Boundaries

Do not send WhatsApp messages in this phase.

Do not enable:

- patient notification sending
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- campaigns
- therapy session tracking

WHATSAPP_SENDING_ENABLED must remain false unless a later named controlled phase explicitly changes it.

## Out Of Scope

- Sending messages to patients after doctor review
- Calendar event creation
- Telegram notifications
- n8n workflows
- automatic doctor confirmation
- full admin dashboard
- uncontrolled production activation

## Recommended Next Phase

P6-F.9.63 — Google Sheets Human Review Inbox Writer

Purpose:

Implement the first safe adapter that writes pending AppointmentRequests from PostgreSQL to the `Solicitudes_Cita` sheet while PostgreSQL remains the source of truth.
