# P6-F.9.16 — Doctor Human Review Command Surface

## Status

SPEC DRAFT

## Objective

Define the human-in-the-loop command surface for doctor review of AppointmentRequest records created by Elvira.

This block designs the architecture and contract only.

No real WhatsApp sending, Telegram callbacks, Google Sheets sync, Calendar integration, or n8n orchestration will be implemented in this block unless explicitly opened in a later sub-block.

## Core Principle

Telegram is a command surface, not business logic.

FastAPI owns:

- validation
- lifecycle transitions
- state consistency
- audit logging
- idempotency
- patient communication orchestration

PostgreSQL remains the source of truth.

## Current Runtime Context

Elvira can already create AppointmentRequest records with:

- estado_solicitud = pendiente_confirmacion
- fecha_solicitada
- franja_solicitada
- telefono
- nombre_paciente
- source_interaction_id

The patient is informed that the request was received and will be confirmed later.

Doctor review is not implemented yet.

## Target Flow

1. AppointmentRequest is created.
2. DoctorHandoffService emits a review task.
3. TelegramNotificationAdapter sends a structured message to the doctor.
4. Doctor chooses an action.
5. Telegram callback reaches FastAPI.
6. Backend validates the action.
7. AppointmentRequestService applies the lifecycle transition.
8. Decision is logged.
9. Future block sends WhatsApp template to patient.

## Initial Doctor Actions

- confirm
- propose_reschedule
- cancel

## Out of Scope

- WhatsApp real sending activation
- WhatsApp patient template sending
- Google Calendar
- n8n orchestration
- therapy/session package tracking
- automatic doctor decision
- replacing PostgreSQL as source of truth

