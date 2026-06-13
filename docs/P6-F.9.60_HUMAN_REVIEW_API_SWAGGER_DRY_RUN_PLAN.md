# P6-F.9.60 — Human Review API Swagger Dry-Run Plan

## Status

PLAN / NO RUNTIME CHANGES

## Context

The internal human review backend is now implemented and pushed to `main`.

Validated previous blocks:

- P6-F.9.56 — Human Review API Boundary Spec
- P6-F.9.57 — Human Review API Endpoint Tests
- P6-F.9.58 — Human Review API Minimal Implementation
- P6-F.9.59 — Human Review API Config Hardening

Current implemented endpoint:

```http
POST /internal/human-review/actions

Current security boundary:

X-Internal-Admin-Token: <INTERNAL_ADMIN_TOKEN>

Current service wiring:

POST /internal/human-review/actions
→ HumanReviewAction
→ HumanReviewService
→ PostgresAppointmentRequestRepository
→ appointment_requests
→ HumanReviewResult
Objective

Define the controlled Swagger dry-run for the internal human review endpoint before using it in any real operational workflow.

This phase does not implement new code.

It defines:

required environment setup
controlled test data
Swagger request payloads
expected responses
database validation queries
safety boundaries
pass/fail criteria
Safety Baseline

The safety baseline remains:

WHATSAPP_SENDING_ENABLED=false
no uncontrolled real patients
no campaigns
no Google Sheets
no Telegram
no n8n
no Calendar
no doctor confirmation automation
no patient notification sending

The endpoint may return:

should_notify_patient
patient_message

But it must not send WhatsApp messages.

Required Environment Variable

Before using the endpoint in Swagger, the environment must define:

INTERNAL_ADMIN_TOKEN=<secure-token>

Do not hardcode the token.

Do not paste the real token into documentation, Git, or chat.

Recommended Validation Surface

Use Swagger/OpenAPI on the deployed or local app:

/docs

Endpoint:

POST /internal/human-review/actions

Required header:

X-Internal-Admin-Token: <configured-token>
Controlled AppointmentRequest Requirement

Swagger validation requires an existing controlled AppointmentRequest.

The request must be:

created only for test/control purposes
not associated with an uncontrolled real patient
safe to mutate
in an expected status for the action being tested

Recommended controlled statuses:

pendiente_confirmacion for confirm
pendiente_confirmacion for cancel
pendiente_confirmacion for request_missing_data
pendiente_confirmacion for propose_alternative
confirmada for reschedule
confirmada for close
Recommended Controlled Test ID

Use a clearly marked control request ID such as:

SOL-HUMAN-REVIEW-SWAGGER-001

If the production DB requires the standard ID format, use a standard generated ID but document it clearly as controlled test data.

Database Pre-Check

Before running Swagger validation, confirm the controlled request exists:

SELECT
  id_solicitud,
  telefono,
  nombre_paciente,
  estado_solicitud,
  fecha_solicitada,
  franja_solicitada,
  fecha_confirmada,
  franja_confirmada,
  motivo_cancelacion,
  updated_by
FROM appointment_requests
WHERE id_solicitud = '<CONTROLLED_ID>';
Dry-Run Case 1 — Missing Token

Request:

{
  "id_solicitud": "<CONTROLLED_ID>",
  "action": "confirm",
  "actor": "dra_daleman"
}

Header:

None

Expected response:

401

Expected detail:

{
  "detail": "Invalid or missing internal admin token"
}

Expected DB mutation:

None
Dry-Run Case 2 — Invalid Token

Request:

{
  "id_solicitud": "<CONTROLLED_ID>",
  "action": "confirm",
  "actor": "dra_daleman"
}

Header:

X-Internal-Admin-Token: wrong-token

Expected response:

401

Expected detail:

{
  "detail": "Invalid or missing internal admin token"
}

Expected DB mutation:

None
Dry-Run Case 3 — Confirm Request

Precondition:

estado_solicitud = pendiente_confirmacion

Request:

{
  "id_solicitud": "<CONTROLLED_ID>",
  "action": "confirm",
  "actor": "dra_daleman",
  "confirmed_date": "2026-06-16",
  "confirmed_franja": "5:00 p. m.–7:00 p. m.",
  "notes": "Swagger dry-run confirmation"
}

Expected response:

{
  "success": true,
  "id_solicitud": "<CONTROLLED_ID>",
  "previous_status": "pendiente_confirmacion",
  "new_status": "confirmada",
  "action": "confirm",
  "message": "Human review action applied.",
  "should_notify_patient": true,
  "patient_message": "<non-null message>",
  "error_code": null
}

Expected DB state:

estado_solicitud = confirmada
fecha_confirmada = 2026-06-16
franja_confirmada = 5:00 p. m.–7:00 p. m.
updated_by = dra_daleman

Important:

No WhatsApp message should be sent.

Dry-Run Case 4 — Business Error / Invalid Action

Request:

{
  "id_solicitud": "<CONTROLLED_ID>",
  "action": "approve_without_contract",
  "actor": "dra_daleman"
}

Expected response:

200

Expected body:

{
  "success": false,
  "error_code": "invalid_action",
  "should_notify_patient": false,
  "patient_message": null
}

Expected DB mutation:

None
Dry-Run Case 5 — Forbidden Transition

Precondition:

estado_solicitud = cancelada

Request:

{
  "id_solicitud": "<CONTROLLED_ID>",
  "action": "confirm",
  "actor": "dra_daleman"
}

Expected response:

200

Expected body:

{
  "success": false,
  "previous_status": "cancelada",
  "new_status": null,
  "error_code": "forbidden_transition",
  "should_notify_patient": false,
  "patient_message": null
}

Expected DB mutation:

None
Post-Validation DB Query

After each Swagger action, verify DB state:

SELECT
  id_solicitud,
  estado_solicitud,
  fecha_confirmada,
  franja_confirmada,
  fecha_aceptada,
  franja_aceptada,
  motivo_reagendamiento,
  motivo_cancelacion,
  observaciones,
  updated_by,
  updated_at
FROM appointment_requests
WHERE id_solicitud = '<CONTROLLED_ID>';
Pass Criteria

P6-F.9.60 dry-run can be considered passed when:

endpoint appears in Swagger
missing token returns 401
invalid token returns 401
valid token reaches HumanReviewService
valid confirm action mutates DB correctly
invalid action returns structured business error
forbidden transition returns structured business error
no WhatsApp message is sent
no Google Sheets/Telegram/n8n/Calendar actions occur
controlled test data is clearly identified
Fail Criteria

The dry-run fails if:

endpoint is publicly usable without token
wrong token is accepted
DB state changes on rejected requests
endpoint sends WhatsApp messages
endpoint triggers external adapters
endpoint confirms a cancelled or closed request
response says success but DB does not change
Out Of Scope

Do not implement or activate:

Google Sheets
Telegram
n8n
Calendar
doctor confirmation automation
patient notification sending
real patient activation
campaigns
therapy package/session tracking
Next Recommended Phase

P6-F.9.61 — Human Review API Swagger Dry-Run Execution

Purpose:

Execute the Swagger dry-run using controlled data and document evidence.

Boundary:

No real patient notification sending.
