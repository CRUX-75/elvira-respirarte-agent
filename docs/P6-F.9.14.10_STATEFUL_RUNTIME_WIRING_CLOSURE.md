# P6-F.9.14.10 — Stateful Runtime Wiring Closure

## Status

CLOSED / GREEN

## Validation

Latest validation:

```bash
169 passed

Working tree after commit:

clean
Scope

This block documents the first runtime wiring of AppointmentRequest persistence.

The wiring is intentionally limited to:

POST /test/message-stateful

The real WhatsApp webhook remains out of scope.

What Changed

The /test/message-stateful endpoint now returns:

appointment_request_decision
appointment_request

For skipped cases, appointment_request is null.

For persisted cases, appointment_request includes metadata such as:

id_solicitud
estado_solicitud
source_interaction_id
fecha_solicitada
franja_solicitada
Runtime Decision

The endpoint now calls:

decide_appointment_request_persistence(...)

The decision remains:

deterministic
pure
no LLM
no network
no DB access inside the decision function
Source Interaction ID

Because save_interaction() currently inserts interactions but does not return an interaction row ID, the runtime uses:

source_interaction_id = whatsapp_message_id

For /test/message-stateful, this means:

source_interaction_id = test-stateful-{uuid4()}
Persistence Surface

When the decision allows persistence, /test/message-stateful uses:

PostgresAppointmentRequestRepository(engine)
AppointmentRequestService(repository=...)

The service creates or reuses an active AppointmentRequest.

Safety Boundaries

Still not touched:

POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
doctor confirmation flow
calendar integration
therapy/session package tracking
Tests Added

New test file:

tests/test_stateful_appointment_request_wiring.py

Covered behaviors:

general message returns skip decision
cita message returns skip decision
fecha_cita message returns skip decision
ready hora_cita persists or reuses AppointmentRequest
response includes appointment_request_decision
response includes appointment_request metadata when persisted
synthetic whatsapp_message_id is used as source_interaction_id
patient state still updates correctly
no real WhatsApp sending is touched
Conclusion

The first safe runtime wiring is complete.

AppointmentRequest persistence is now testable through /test/message-stateful without activating real WhatsApp behavior.

The next safe block should validate this behavior through Swagger or local TestClient scenarios before considering any real webhook integration.
