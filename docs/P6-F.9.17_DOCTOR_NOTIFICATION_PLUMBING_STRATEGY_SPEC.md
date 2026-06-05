# P6-F.9.17 — Doctor Notification Plumbing Strategy SPEC

## Status

DRAFT / SPEC

## Purpose

Define the safest and simplest strategy for notifying Dra. D'Aleman when a new AppointmentRequest is created.

This block does not implement the notification yet.

It only defines the architecture and boundaries.

## Current Architecture

The sealed architecture remains:

- FastAPI = validation, decision logic, transitions, audit boundary
- PostgreSQL = source of truth
- WhatsApp = patient channel
- Telegram or WhatsApp = doctor notification / command surface
- n8n = optional auxiliary plumbing only

## Problem

When Elvira creates an AppointmentRequest, Dra. D'Aleman needs to be notified so she can review the request.

A previous Telegram n8n workflow was deleted and has no backup.

This is not critical because n8n must not contain business-critical appointment logic.

## Core Rule

n8n must not decide anything.

n8n may only receive an already validated payload and transport it to a notification channel.

## Notification Trigger

A doctor notification may be triggered only after:

- AppointmentRequest persistence succeeds
- id_solicitud exists
- estado_solicitud is pendiente_confirmacion
- fecha_solicitada exists
- franja_solicitada exists
- telefono exists
- source_interaction_id exists

## Notification Payload

Minimum payload:

- id_solicitud
- nombre_paciente
- telefono
- fecha_solicitada
- franja_solicitada
- servicio_solicitado
- direccion_domicilio
- estado_solicitud
- source_interaction_id
- created_at

Optional payload:

- observaciones
- patient message excerpt
- appointment request URL or review link
- doctor action buttons if supported later

## Candidate Strategies

### Option A — FastAPI sends directly to Telegram

FastAPI calls Telegram Bot API directly after AppointmentRequest persistence.

Pros:

- fewer moving parts
- no n8n dependency
- easier to test
- clearer audit boundary
- logic stays in backend

Cons:

- requires Telegram Bot API token in backend environment
- backend owns notification delivery retry handling

### Option B — FastAPI triggers n8n webhook

FastAPI sends a validated payload to an n8n webhook.

n8n only formats and sends the Telegram message.

Pros:

- quick visual workflow
- easy formatting changes
- keeps notification plumbing outside backend

Cons:

- more moving parts
- n8n availability becomes part of notification path
- risk of future logic leakage into n8n
- deleted workflow already showed fragility

### Option C — FastAPI writes only to Google Sheets first

FastAPI writes the request to Google Sheets as human-visible inbox.

Doctor checks the sheet manually or receives notification later.

Pros:

- operationally simple
- visible audit layer
- no Telegram dependency initially

Cons:

- slower doctor awareness
- no immediate notification
- weaker UX for doctor review

## Recommended Strategy

Recommended direction:

Option A first, or Option B only if Telegram formatting/plumbing is intentionally kept outside backend.

Given the current project principles, the safest architecture is:

FastAPI creates AppointmentRequest
→ PostgreSQL stores source of truth
→ FastAPI calls a small DoctorNotificationService
→ DoctorNotificationService sends a notification through one adapter

Initial adapter options:

- TelegramDoctorNotificationAdapter
- N8nDoctorNotificationAdapter
- GoogleSheetsDoctorInboxAdapter

The service contract should remain independent of the transport.

## Proposed Internal Design

Create later:

app/services/doctor_notification_service.py

Possible interface:

notify_new_appointment_request(request: AppointmentRequest) -> DoctorNotificationResult

Result fields:

- success: bool
- channel: str
- external_message_id: str | None
- error: str | None

## Important Boundaries

This block must not implement:

- doctor approval
- doctor rejection
- appointment rescheduling
- patient WhatsApp confirmation
- automatic appointment confirmation
- n8n state transitions
- Calendar integration

## Acceptance Criteria

This SPEC is accepted when:

- notification strategy is documented
- n8n boundary is clear
- payload contract is documented
- first implementation direction is selected
- no runtime code has been changed

## Next Possible Blocks

After this SPEC:

1. P6-F.9.17.1 — Doctor Notification Payload Contract
2. P6-F.9.17.2 — DoctorNotificationService Contract
3. P6-F.9.17.3 — Telegram/N8n Adapter Decision
4. P6-F.9.17.4 — Tests RED
5. P6-F.9.17.5 — Minimal Implementation

