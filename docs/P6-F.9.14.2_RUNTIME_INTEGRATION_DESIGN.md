# P6-F.9.14.2 — Runtime Integration Design

## Status

DRAFT

## Purpose

This document defines the technical design for integrating `AppointmentRequestService` into the existing Elvira runtime flow.

This block is design-only.

No runtime implementation is done here.

---

## Design Goal

Integrate appointment request persistence into the current message-processing flow without changing patient-facing behavior yet.

The first runtime integration must be safe, deterministic, testable, and observable.

---

## Current Boundary

Already available:

- AppointmentRequest model
- AppointmentRequest lifecycle validator
- AppointmentRequest factory
- AppointmentRequestService
- AppointmentRequestRepository Protocol
- PostgresAppointmentRequestRepository
- Production `appointment_requests` table
- Runtime KB
- Patient state machine
- Interaction persistence
- WhatsApp sending safety flag

Not connected yet:

- AppointmentRequestService to runtime flow
- AppointmentRequest repository dependency injection
- source_interaction_id linkage
- Swagger/internal validation endpoint
- Google Sheets
- Telegram
- n8n

---

## Proposed Runtime Position

`AppointmentRequestService` should be called only after deterministic runtime processing has enough information.

Recommended position:

1. Parse WhatsApp/test payload.
2. Deduplicate message.
3. Load patient.
4. Classify intent.
5. Resolve appointment date/time context when applicable.
6. Apply patient state transition.
7. Generate and persist interaction log.
8. Call AppointmentRequestService if appointment persistence conditions are met.
9. Persist any appointment request result.
10. Generate or return patient-facing response.

Preferred option:

Persist the interaction first, then pass its ID as `source_interaction_id` into AppointmentRequestService.

Reason:

The appointment request should be traceable to the exact interaction that caused it.

---

## Integration Trigger

AppointmentRequestService must not run for every message.

It should run only when all required conditions are true:

- current or new patient state is appointment-related
- deterministic intent is appointment-related
- date has been resolved or explicitly supplied
- time window has been resolved or explicitly supplied
- the message represents an operational appointment request
- weekend/holiday/business-rule validation did not block the request
- the runtime has enough information to create or update a useful request

---

## Candidate Patient States

Initial candidate states:

- ST_CITA_FECHA
- ST_CITA_FRANJA
- ST_CITA_PENDIENTE
- ST_CITA_CONFIRMADA

Implementation must verify the exact state names in the current code before wiring.

---

## Candidate Intents

Initial candidate intents:

- cita
- fecha_cita
- hora_cita

Implementation must verify the exact intent names in the current classifier before wiring.

---

## Non-Creation Cases

Do not create appointment requests from messages that only ask for information.

Examples:

- service questions
- schedule questions
- price questions
- general greeting
- vague appointment intent without date/time
- emergency or medical advice scenarios
- opt-out messages

---

## Create vs Reuse Rule

Runtime must ask the repository/service whether there is an active request for the patient.

If an active request exists:

- reuse the same `id_solicitud`
- update the same request when appropriate
- do not create a duplicate

If only terminal requests exist:

- a new request may be created

Active states:

- nueva
- pendiente_datos
- pendiente_confirmacion
- confirmada
- reagendada

Terminal states:

- cancelada
- cerrada

---

## Request Status Mapping

Initial mapping proposal:

### Missing relevant operational data

Use:

`pendiente_datos`

When:

- date exists but time window is missing
- time window exists but service/address is still needed
- the request is not ready for doctor review

### Candidate request ready for human review

Use:

`pendiente_confirmacion`

When:

- date exists
- time window exists
- the patient has expressed a clear appointment request
- doctor must review before confirmation

### Confirmed request

Use:

`confirmada`

Only when:

- doctor/human decision confirms it
- not in this runtime integration block

### Rescheduled request

Use:

`reagendada`

Only when:

- an existing request is being rescheduled
- human or deterministic future process explicitly marks it as such

---

## No Automatic Appointment Confirmation

The runtime must not confirm real appointments automatically.

Elvira may collect appointment request information.

Elvira may say the request will be reviewed.

Elvira must not say that an appointment is confirmed unless a future doctor-confirmation flow explicitly updates the request.

---

## Dependency Injection Design

The runtime will need access to:

- AppointmentRequestService
- PostgresAppointmentRequestRepository
- database engine/session factory already used by the app

Design rule:

The repository should receive an injected SQLAlchemy Engine.

No global production engine import should be added inside the repository.

Recommended future factory/wiring point:

- existing app dependency/container module, if present
- otherwise a small explicit dependency builder near the current repository wiring

Implementation must inspect current project structure first.

---

## Data Input Needed by AppointmentRequestService

Runtime should build an internal payload with:

- telefono
- nombre_paciente
- intent_origen
- canal_origen = whatsapp
- fecha_solicitada
- franja_solicitada
- hora_solicitada_texto
- servicio_solicitado
- direccion_domicilio
- source_interaction_id
- created_by = system
- updated_by = system

Only available deterministic fields should be passed.

The LLM must not invent missing operational fields.

---

## Interaction Linkage

Preferred strategy:

1. Persist interaction.
2. Obtain interaction ID.
3. Create/update AppointmentRequest with `source_interaction_id`.

If the current interaction repository does not return an ID, the implementation must first inspect whether this can be added safely.

No schema changes should be made without a separate SPEC.

---

## Observability

Future runtime traces/logs should show:

- appointment request persistence attempted: yes/no
- reason if skipped
- created vs reused
- id_solicitud
- estado_solicitud
- source_interaction_id
- telefono

This may be added first to structured logs or LangSmith metadata in a later block.

---

## Validation Strategy

Before connecting to real WhatsApp runtime:

1. Add unit tests for the trigger/decision function.
2. Add tests proving vague messages do not create requests.
3. Add tests proving complete appointment info creates/reuses requests.
4. Add tests proving terminal requests do not block new ones.
5. Add tests proving active requests are reused.
6. Validate through test endpoint or existing stateful test endpoint.
7. Keep WhatsApp sending disabled.

---

## Internal Endpoint Decision

A dedicated internal endpoint may be useful before full runtime wiring.

Candidate:

`POST /test/appointment-request`

Pros:

- validates service/repository wiring safely
- avoids real WhatsApp sending
- allows Swagger testing
- easier production dry-run

Cons:

- adds temporary surface area
- must be clearly marked as test/internal
- should not become part of the public product API

Decision:

Do not implement yet.

First inspect existing `/test/message-stateful` flow to decide whether it is enough.

---

## Implementation Order After This Design

Recommended next blocks:

1. P6-F.9.14.3 — Runtime Flow Inspection
2. P6-F.9.14.4 — Appointment Persistence Decision Function SPEC
3. P6-F.9.14.5 — Decision Function Tests
4. P6-F.9.14.6 — Decision Function Implementation
5. P6-F.9.14.7 — Repository/Service Runtime Wiring Design
6. P6-F.9.14.8 — Safe Test Endpoint or Stateful Test Integration
7. P6-F.9.14.9 — Runtime Integration Tests
8. P6-F.9.14.10 — Runtime Integration Implementation

---

## Out of Scope

This design does not implement:

- runtime code changes
- DB schema changes
- Google Sheets sync
- Telegram notification
- n8n workflow
- WhatsApp sending activation
- doctor confirmation flow
- calendar integration
- therapy session tracking

