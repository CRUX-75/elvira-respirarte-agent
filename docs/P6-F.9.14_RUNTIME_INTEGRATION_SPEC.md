# P6-F.9.14 — Runtime Integration SPEC

## Status

DRAFT

## Purpose

This document defines how `AppointmentRequestService` will be integrated into the current Elvira / Respirarte runtime flow.

This phase is specification-only.

No runtime code is implemented in this block.

---

## Current Production State

The production database already contains the `appointment_requests` table.

The table was created through a controlled production migration using pgweb via EasyPanel.

The production application remained healthy after the migration.

Current production behavior is unchanged:

- AppointmentRequestService is not connected to the runtime flow yet.
- WhatsApp sending remains disabled.
- Google Sheets is not connected.
- Telegram is not connected.
- n8n is not involved.
- No Swagger endpoint exists yet for appointment requests.

---

## Architectural Rule

The system keeps the existing architecture principle:

El canal transporta.  
El workflow controla.  
La KB informa.  
El modelo redacta.  
La state machine protege.  
El log permite auditar.

For appointment requests, this means:

- WhatsApp transports patient messages.
- The Python workflow controls the appointment request lifecycle.
- The KB informs service, schedule, and rule context.
- The LLM only drafts the patient-facing wording.
- The state machine protects valid transitions.
- PostgreSQL logs and persists the operational request.

---

## Source of Truth

`appointment_requests` in PostgreSQL is the source of truth for appointment request persistence.

Google Sheets will be added later only as a human-visible operational inbox.

Telegram may be added later only as an auxiliary notification layer.

n8n must not own appointment request state, validation, lifecycle, or persistence.

---

## Runtime Integration Goal

The goal is to connect `AppointmentRequestService` to the existing message processing flow only after the state machine has enough deterministic information to create or reuse an appointment request safely.

The integration must avoid creating incomplete, duplicated, or speculative requests.

---

## Proposed Integration Point

`AppointmentRequestService` should run after these runtime steps:

1. WhatsApp webhook payload is parsed.
2. Message is deduplicated through `processed_messages`.
3. Patient state is loaded.
4. Text is sanitized.
5. Intent is classified deterministically.
6. State transition is calculated.
7. Appointment-relevant extracted fields are available.
8. Interaction persistence has enough context to provide or later link `source_interaction_id`.

The service must not run before deterministic classification and state transition.

---

## Appointment Request Creation Conditions

A new appointment request may be created only when the runtime has enough minimum information.

Minimum required conditions:

- Patient phone number exists.
- Patient is in an appointment-related flow.
- Intent/state transition indicates a real appointment request, not a generic question.
- Requested date has been resolved deterministically.
- Requested time window or patient time preference exists.
- The request is not blocked by weekend/holiday/business-rule validation.
- The system is not merely answering schedule/service information.
- There is no existing active request for the same patient that should be reused.

A request must not be created from vague messages such as:

- "Quiero una cita"
- "Tienen horarios?"
- "Cuánto cuesta?"
- "Mañana?"
- "En la tarde?"

Those messages may move the conversation state forward, but should not necessarily create a persisted appointment request until enough appointment details exist.

---

## Appointment Request Reuse Conditions

If `find_active_by_telefono(telefono)` returns an active request, the runtime must reuse that request instead of creating a duplicate.

Active states:

- nueva
- pendiente_datos
- pendiente_confirmacion
- confirmada
- reagendada

Terminal states do not block a new request:

- cancelada
- cerrada

The service must preserve `id_solicitud` during:

- contraoffers
- rescheduling
- lifecycle transitions
- doctor/patient negotiation

---

## Patient States Participating in Runtime Integration

The initial integration should be limited to appointment-related patient states.

Candidate states:

- ST_CITA_FECHA
- ST_CITA_FRANJA
- ST_CITA_PENDIENTE
- ST_CITA_CONFIRMADA

The exact mapping must be verified against the current state machine before implementation.

Out of scope for this first integration:

- payment states
- generic service questions
- emergency/urgency handling
- opt-out handling
- therapy package/session tracking

---

## Intent Participation

Candidate intents that may participate:

- cita
- fecha_cita
- hora_cita

The runtime must distinguish between:

1. Appointment information gathering.
2. Candidate slot proposal.
3. Actual appointment request persistence.

Not every appointment-related intent should create a request.

---

## Avoiding Incomplete Requests

The runtime must not persist a request unless the request has enough operational value for doctor review.

At minimum, the persisted request should contain:

- telefono
- nombre_paciente, if available
- estado_solicitud
- intent_origen
- canal_origen = whatsapp
- fecha_solicitada
- franja_solicitada or hora_solicitada_texto
- servicio_solicitado, if available
- direccion_domicilio, if available
- source_interaction_id, when available
- created_by = system
- updated_by = system

If service or address is missing, the request may still be valid only if the lifecycle status clearly indicates `pendiente_datos`.

---

## Relationship With State Machine

The state machine remains the deterministic authority for patient conversation state.

`AppointmentRequestService` must not replace the state machine.

The expected relationship is:

1. State machine determines patient state transition.
2. Runtime derives whether appointment request persistence is appropriate.
3. AppointmentRequestService creates/reuses/updates request.
4. Runtime persists interaction and patient state.
5. LLM drafts patient-facing response using deterministic context.

The service may receive state-derived input, but it must not decide patient state transitions.

---

## Relationship With Interaction Log

Every appointment request should be traceable to the patient conversation.

Preferred model:

- Persist interaction first.
- Use the created interaction ID as `source_interaction_id`.
- Then create/update AppointmentRequest.

Alternative model if current flow makes that difficult:

- Create/update AppointmentRequest first with `source_interaction_id = null`.
- Persist interaction.
- Update AppointmentRequest with `source_interaction_id`.

The implementation design must choose one option after reviewing the current runtime flow.

No guesswork.

---

## Relationship With LangSmith

Runtime integration should later be validated through LangSmith traces.

The trace should make visible:

- intent
- previous patient state
- new patient state
- whether appointment request persistence was attempted
- whether an existing request was reused
- id_solicitud when created/reused
- appointment request status after operation
- safety boundaries applied

No LangSmith changes are required in this SPEC block.

---

## Relationship With Google Sheets

Google Sheets is out of scope for this block.

No Google Sheets adapter should be created yet.

Future direction:

PostgreSQL appointment_requests
→ Google Sheets operational inbox sync
→ doctor review

Google Sheets must not become the source of truth.

---

## Relationship With Telegram

Telegram notification is out of scope for this block.

Future direction:

AppointmentRequest created or updated
→ optional Telegram notification to doctor
→ doctor reviews request
→ future manual/controlled decision flow

Telegram must not own request state.

---

## Relationship With n8n

n8n is out of scope for this block.

n8n may only be used later as an auxiliary notification or formatting layer.

n8n must not control:

- appointment request creation
- appointment request update
- appointment request state
- validation rules
- lifecycle transitions
- persistence rules

---

## Relationship With WhatsApp Sending

No WhatsApp sending changes are allowed in this block.

`WHATSAPP_SENDING_ENABLED` must remain false during validation unless a later controlled sending block explicitly changes it.

The first integration must be validated through dry-run endpoints or Swagger-style internal testing, not uncontrolled real WhatsApp sending.

---

## Swagger / Internal Endpoint Consideration

Before connecting AppointmentRequestService to the real message runtime, it may be useful to create an internal test endpoint.

Possible endpoint:

`POST /test/appointment-request`

Purpose:

- exercise AppointmentRequestService safely
- create/reuse/update appointment requests in the production-like app layer
- validate repository wiring
- validate DB persistence
- validate response payload
- avoid real WhatsApp sending

This endpoint is not approved yet.

It should be evaluated in the design block after this SPEC.

---

## Safety Requirements

Runtime integration must preserve these guarantees:

- No duplicate active appointment requests for the same patient.
- Terminal requests do not block new requests.
- Incomplete messages do not create operational noise.
- LLM never decides whether to create, update, or confirm a request.
- No real appointment is confirmed automatically.
- No real availability is claimed automatically.
- Doctor remains the human decision-maker.
- WhatsApp sending remains controlled by environment flag.
- Runtime behavior can be tested without sending real WhatsApp messages.

---

## Out of Scope

This SPEC does not implement:

- runtime wiring
- repository dependency injection
- Google Sheets sync
- Telegram notification
- n8n workflow
- appointment confirmation automation
- calendar integration
- therapy session package tracking
- remaining sessions tracking
- Swagger endpoint
- production deployment
- WhatsApp sending activation

---

## Next Block

P6-F.9.14.2 — Runtime Integration Design

The next block should inspect the current runtime flow and decide:

- exact integration function/file
- whether interaction is persisted before or after AppointmentRequestService
- required dependency injection pattern
- exact input DTO or internal structure
- exact tests to write before implementation
- whether an internal Swagger endpoint should come before real runtime wiring

