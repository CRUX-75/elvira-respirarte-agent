# P6-F.9.14.7 — Repository/Service Runtime Wiring Design

## Status

DRAFT

## Purpose

This document defines how the runtime will later wire the appointment request persistence decision to `AppointmentRequestService`.

This block is design-only.

No runtime implementation is done here.

---

## Background

The following blocks are already closed:

- P6-F.9.14.3 — Runtime Flow Inspection
- P6-F.9.14.4 — Appointment Persistence Decision Function SPEC
- P6-F.9.14.5 — Decision Function Tests
- P6-F.9.14.6 — Decision Function Implementation

Current validation baseline:

- 165 passed

The pure decision function now exists:

`app/services/appointment_request_runtime.py`

Function:

`decide_appointment_request_persistence(...)`

The function decides whether runtime appointment request persistence should be attempted.

It does not touch the database.

---

## Design Goal

Wire appointment request persistence into the runtime in a safe, staged way.

First target:

`POST /test/message-stateful`

Reason:

- It already performs realistic stateful processing.
- It already persists interactions.
- It never sends real WhatsApp messages.
- It is suitable for Swagger validation.
- It generates a synthetic `whatsapp_message_id`.

Real WhatsApp webhook wiring must come later.

---

## Existing Runtime Flow To Preserve

The `/test/message-stateful` flow currently does:

1. Receives `IncomingMessage`.
2. Gets or creates patient.
3. Reads current patient state.
4. Builds `stateful_message`.
5. Runs `traced_process_message(process_message, stateful_message)`.
6. Generates synthetic `whatsapp_message_id`.
7. Sets `delivery_status = sending_skipped`.
8. Saves interaction.
9. Updates patient state.
10. Updates patient last message.
11. Returns result metadata.

The first wiring should preserve this behavior.

Appointment request persistence must be additive.

---

## Proposed First Wiring Position

In `/test/message-stateful`, the decision should run after:

`result = traced_process_message(process_message, stateful_message)`

and after:

`whatsapp_message_id = f"test-stateful-{uuid4()}"`

Reason:

The decision function needs:

- final `ElviraState`
- telefono
- nombre
- source_interaction_id

For the first integration:

`source_interaction_id = whatsapp_message_id`

---

## Proposed First Runtime Sequence

Target sequence for `/test/message-stateful`:

1. Process message through LangGraph.
2. Generate synthetic `whatsapp_message_id`.
3. Run `decide_appointment_request_persistence(...)`.
4. If decision says skip:
   - do not call AppointmentRequestService
   - include decision metadata in test response
5. If decision says persist:
   - build or reuse AppointmentRequest through `AppointmentRequestService`
   - persist via `PostgresAppointmentRequestRepository`
   - include appointment request metadata in test response
6. Save interaction.
7. Update patient state.
8. Update patient last message.
9. Return response.

Important:

If appointment request persistence fails in the test endpoint, it may return an explicit error because this is a validation endpoint.

For the real webhook later, failure-handling may need a softer strategy to avoid breaking core patient flow.

---

## Dependency Wiring

The runtime wiring will need:

- SQLAlchemy engine from `app.db.session`
- `PostgresAppointmentRequestRepository`
- `AppointmentRequestService`

Recommended imports for future implementation:

```python
from app.db.session import engine
from app.repositories.postgres_appointment_request_repository import (
    PostgresAppointmentRequestRepository,
)
from app.services.appointment_request_service import AppointmentRequestService
from app.services.appointment_request_runtime import (
    decide_appointment_request_persistence,
)

Recommended construction:

appointment_request_repository = PostgresAppointmentRequestRepository(engine)
appointment_request_service = AppointmentRequestService(
    repository=appointment_request_repository
)

This should be done in a small helper function, not repeatedly inline inside endpoint logic.

Proposed Helper Function

Candidate file:

app/services/appointment_request_runtime.py

Candidate function:

build_appointment_request_service(engine)

Alternative candidate file:

app/dependencies.py

Current recommendation:

Keep a small helper close to the runtime appointment request logic for now.

Reason:

avoids creating a broader dependency layer prematurely
keeps this integration local and understandable
can be refactored later if more services need shared wiring
Service Call Shape

The exact AppointmentRequestService public method names must be verified before implementation.

Expected service responsibility:

create a new request if no active request exists
reuse active request if present
preserve id_solicitud
apply lifecycle validation
persist through repository

The runtime must not manually decide duplicate prevention.

That belongs to the service/repository layer.

Runtime Data Mapping

Decision output should be mapped into AppointmentRequestService input.

Initial mapping:

telefono → request telefono
nombre_paciente → request nombre_paciente
intent_origen → request intent_origen
canal_origen → request canal_origen
estado_solicitud → request estado_solicitud
fecha_solicitada → request fecha_solicitada
franja_solicitada → request franja_solicitada
hora_solicitada_texto → request hora_solicitada_texto
servicio_solicitado → request servicio_solicitado
direccion_domicilio → request direccion_domicilio
source_interaction_id → request source_interaction_id

Fields not available deterministically must stay None.

The LLM response must not be parsed to invent operational fields.

Response Metadata For Test Endpoint

When wired into /test/message-stateful, the response should include appointment request decision metadata.

Proposed response fields:

response["appointment_request_decision"] = {
    "should_persist": decision.should_persist,
    "reason": decision.reason,
}

If persistence is skipped:

response["appointment_request"] = None

If persistence succeeds:

response["appointment_request"] = {
    "id_solicitud": request.id_solicitud,
    "estado_solicitud": request.estado_solicitud,
    "source_interaction_id": request.source_interaction_id,
}

This allows Swagger validation without reading the database manually every time.

Safety Boundaries

The first wiring must not:

touch real WhatsApp sending
change WHATSAPP_SENDING_ENABLED
connect Google Sheets
send Telegram notifications
invoke n8n
confirm appointments automatically
claim real doctor availability
change patient state rules
make LLM decide persistence
create requests for cita or fecha_cita
Failure Handling For Test Endpoint

For /test/message-stateful, a persistence failure may return:

{
  "status": "error",
  "reason": "appointment_request_persistence_failed",
  ...
}

This is acceptable because the endpoint is a dry-run validation surface.

However, the implementation should be careful not to corrupt patient state if appointment request persistence fails.

Recommended first behavior:

run appointment persistence before patient state update
if appointment persistence fails, return error
do not update patient state in the failed test flow

This mirrors the existing safety principle used for WhatsApp send failures in the real webhook.

Failure Handling For Real Webhook Later

Real webhook behavior is out of scope for the first wiring.

Later design must decide whether appointment request persistence failure should:

block patient state update, or
log the failure and continue the conversation

This must be handled in a separate SPEC before touching /webhook.

Testing Strategy

Next block should write tests before implementation.

Candidate test file:

tests/test_message_stateful_appointment_request_wiring.py

Possible tests:

/test/message-stateful returns skip decision for general message.
/test/message-stateful returns skip decision for cita.
/test/message-stateful returns skip decision for fecha_cita.
/test/message-stateful creates or reuses request for hora_cita ready state.
Response includes appointment_request_decision.
Response includes appointment request metadata when persisted.
Synthetic whatsapp_message_id is used as source_interaction_id.
Patient state still updates correctly when persistence succeeds.
Patient state does not update if appointment request persistence fails.

The exact testing approach must inspect existing FastAPI test client patterns before implementation.

Implementation Order

Recommended next blocks:

Inspect AppointmentRequestService method signatures.
Inspect existing FastAPI endpoint tests.
Write failing tests for /test/message-stateful appointment request metadata.
Add minimal service wiring helper.
Wire only /test/message-stateful.
Run targeted tests.
Run full suite.
Document result.
Out of Scope

This design does not implement:

runtime wiring
tests
service helper
real webhook integration
Google Sheets
Telegram
n8n
WhatsApp sending changes
doctor confirmation flow
calendar integration
therapy package/session tracking
Next Block

P6-F.9.14.8 — Stateful Test Endpoint Wiring Tests

Goal:

Write failing tests for appointment request decision/service metadata in /test/message-stateful.

