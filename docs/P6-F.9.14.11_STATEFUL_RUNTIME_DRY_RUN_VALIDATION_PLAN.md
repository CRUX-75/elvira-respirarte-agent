# P6-F.9.14.11 — Stateful Runtime Dry-Run Validation Plan

## Status

PLANNED

## Objective

Validate AppointmentRequest runtime wiring through:

```text
POST /test/message-stateful

without touching the real WhatsApp webhook.

Current Baseline

Latest validation:

169 passed
Scope

This validation only covers the safe stateful dry-run endpoint.

In scope:

/test/message-stateful
deterministic appointment request decision
AppointmentRequest persistence through PostgreSQL repository/service
synthetic test-stateful-{uuid4()} source interaction ID
patient state update

Out of scope:

POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
doctor confirmation
calendar logic
therapy/session package tracking
Scenarios to Validate
Scenario 1 — General Message

Input:

{
  "telefono": "573001112233",
  "nombre": "Paciente Test",
  "mensaje": "Hola buenos días"
}

Expected:

appointment_request_decision.should_persist = false
appointment_request_decision.reason = skipped_non_appointment_intent
appointment_request = null
delivery_status = sending_skipped
no real WhatsApp sending
Scenario 2 — Initial Appointment Intent

Input:

{
  "telefono": "573001112233",
  "nombre": "Paciente Test",
  "mensaje": "Quiero pedir una cita"
}

Expected:

appointment_request_decision.should_persist = false
reason should indicate initial cita intent
no AppointmentRequest persisted yet
patient state should move toward appointment date collection
Scenario 3 — Date Provided Without Time Window

Input depends on existing patient state.

Expected:

appointment_request_decision.should_persist = false
reason should indicate waiting for time window
no AppointmentRequest persisted yet
Scenario 4 — Ready Appointment Request

Input depends on existing patient state.

Expected:

appointment_request_decision.should_persist = true
reason: allowed_hora_cita_ready_for_human_review
appointment_request metadata present
source_interaction_id equals the synthetic whatsapp_message_id
state persists as ST_CITA_PENDIENTE
Validation Method

Preferred first method:

local TestClient / pytest already covers contract

Second method:

Swagger /docs
endpoint: /test/message-stateful

Production method later:

only after local validation
only with WHATSAPP_SENDING_ENABLED=false
only against /test/message-stateful
Success Criteria

This block is successful when:

local tests still pass
Swagger dry-run confirms response structure
AppointmentRequest is created only for ready hora_cita
skipped messages never create AppointmentRequest
no real WhatsApp sending occurs
