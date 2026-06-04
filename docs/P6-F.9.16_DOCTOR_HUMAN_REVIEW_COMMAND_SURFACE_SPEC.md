# P6-F.9.16 — Doctor Human Review Command Surface

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


---

## P6-F.9.16.1 — DoctorDecision Contract Design

## Purpose

Define the internal decision record created when the doctor acts on an AppointmentRequest through the human review command surface.

DoctorDecision is an audit object.

It does not replace AppointmentRequest.

It records who decided, what action was requested, against which appointment request, and with which validated result.

## Core Rule

DoctorDecision records human intent and audit metadata.

AppointmentRequest remains the operational object whose lifecycle is transitioned by AppointmentRequestService.

## Initial Decision Actions

Valid doctor actions:

- confirm
- propose_reschedule
- cancel

## Proposed DoctorDecision Fields

- id_decision
- id_solicitud
- action
- actor_type
- actor_id
- actor_display_name
- decision_source
- decision_payload
- previous_estado_solicitud
- resulting_estado_solicitud
- idempotency_key
- created_at

## Field Meaning

### id_decision

Unique identifier for the human decision record.

### id_solicitud

AppointmentRequest ID affected by the decision.

### action

Doctor action requested through the command surface.

Allowed values:

- confirm
- propose_reschedule
- cancel

### actor_type

Who performed the action.

Initial allowed value:

- doctor

Future possible values:

- admin
- system

### actor_id

Stable identifier of the actor.

For Telegram, this may later map to the Telegram user ID or an internal doctor ID.

### actor_display_name

Human-readable actor name.

Example:

- Dra. D'Aleman

### decision_source

Where the decision came from.

Initial allowed value:

- telegram

Future possible values:

- internal_admin
- manual_backend

### decision_payload

Structured JSON payload with action-specific data.

Examples:

For confirm:

```json
{
  "confirmed_date": "2026-05-29",
  "confirmed_slot": "5:00 p. m.–7:00 p. m."
}
For propose_reschedule:

{
  "proposed_date": "2026-05-30",
  "proposed_slot": "3:00 p. m.–5:00 p. m.",
  "reason": "La doctora no tiene disponibilidad en la franja solicitada."
}

For cancel:

{
  "reason": "No hay disponibilidad para esa solicitud."
}
previous_estado_solicitud

AppointmentRequest status before applying the decision.

resulting_estado_solicitud

AppointmentRequest status after applying the decision.

Expected initial mappings:

confirm -> confirmada
propose_reschedule -> pendiente_confirmacion
cancel -> cancelada
idempotency_key

Deterministic key used to prevent duplicate processing of the same doctor action.

created_at

Timestamp when the decision was recorded.

Validation Rules

The backend must validate:

id_solicitud exists
AppointmentRequest is in a valid state for doctor review
action is allowed
action payload is valid for the selected action
actor is authorized
callback/action token is valid
action is idempotent
lifecycle transition is valid
Invalid Cases

The backend must reject:

unknown id_solicitud
terminal AppointmentRequest records
duplicated callback actions
malformed callback payloads
unsigned or expired action tokens
unauthorized actors
invalid lifecycle transitions
Out of Scope For This Sub-Block
Database table implementation
Telegram webhook implementation
real Telegram bot sending
WhatsApp template sending
Google Sheets sync
n8n orchestration


---

## P6-F.9.16.2 — Telegram Command Surface Contract

## Purpose

Define the Telegram-facing command surface used by the doctor to review AppointmentRequest records.

Telegram is only the human command interface.

It must not contain business logic, lifecycle rules, patient communication rules, or appointment validation logic.

## Core Rule

Telegram displays review information and sends signed doctor actions back to FastAPI.

FastAPI validates and executes the action.

## Telegram Message Purpose

The Telegram message should help the doctor quickly understand:

- who requested the appointment
- when the patient requested the appointment
- which time window was selected
- what service was requested, if available
- what address was provided, if available
- the current request status
- which actions are available

## Proposed Telegram Message Format

Example:

```text
Nueva solicitud de cita

Paciente: María Pérez
Teléfono: +57XXXXXXXXXX
Fecha solicitada: viernes 29 de mayo
Franja solicitada: 5:00 p. m.–7:00 p. m.
Servicio: Terapia respiratoria domiciliaria
Dirección: Pendiente / no informada
Estado: pendiente_confirmacion

Acción requerida:
Revise la solicitud y seleccione una opción.
Initial Telegram Buttons

The first version should expose three actions:

Confirmar
Proponer alternativa
Cancelar
Button Semantics
Confirmar

Doctor accepts the appointment request.

Expected backend action:

confirm

Expected AppointmentRequest transition:

pendiente_confirmacion -> confirmada
Proponer alternativa

Doctor cannot accept the requested date or slot and wants to propose another option.

Expected backend action:

propose_reschedule

Expected AppointmentRequest transition:

pendiente_confirmacion -> pendiente_confirmacion

The same id_solicitud must be preserved.

Cancelar

Doctor rejects or cancels the appointment request.

Expected backend action:

cancel

Expected AppointmentRequest transition:

pendiente_confirmacion -> cancelada
Callback Payload Requirement

Telegram callback payloads are limited in size.

Therefore, callback data must be compact.

Callback data must not contain full business data.

It should contain only:

action
id_solicitud reference or compact token reference
signed validation token or token lookup reference
Candidate Callback Payload Shapes
Option A — Compact Signed Payload
dr:{action}:{id_solicitud}:{signature}

Example:

dr:confirm:SOL-123:abc123
Option B — Token Reference
dr:{token_id}

Example:

dr:tok_8f3a91

The backend resolves token_id to:

id_solicitud
action
actor permissions
expiration
idempotency key
Preferred Direction

Use a token reference approach if callback payload size becomes a risk.

Use compact signed payload only if the generated payload can reliably stay within Telegram callback limits.

Final decision will be made before implementation.

Backend Callback Requirements

When a Telegram callback reaches FastAPI, the backend must:

Parse the callback payload.
Validate token or signature.
Validate actor authorization.
Validate id_solicitud exists.
Validate AppointmentRequest current state.
Validate action is allowed.
Validate idempotency.
Apply lifecycle transition through AppointmentRequestService.
Record DoctorDecision.
Return a Telegram-safe confirmation response.
Telegram Confirmation Feedback

After the doctor clicks a button, Telegram should receive a short confirmation message.

Examples:

For confirm:

Solicitud confirmada correctamente.

For propose_reschedule:

Alternativa registrada para esta solicitud.

For cancel:

Solicitud cancelada correctamente.

For rejected/duplicate action:

Esta acción ya fue procesada o ya no está disponible.
Security Requirements

Telegram callbacks must not be trusted blindly.

The backend must protect against:

forged callback payloads
expired actions
duplicated clicks
unauthorized Telegram users
callbacks for terminal AppointmentRequest records
modified id_solicitud values
replay attacks
Out of Scope For This Sub-Block
Telegram bot implementation
Telegram webhook route implementation
token/signature implementation
DoctorDecision database table
WhatsApp template sending
Google Sheets sync
n8n orchestration

