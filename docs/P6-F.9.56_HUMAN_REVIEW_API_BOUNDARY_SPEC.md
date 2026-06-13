# P6-F.9.56 — Human Review API Boundary Spec

## Status

SPEC / API BOUNDARY ONLY

## Context

The internal human review service is now implemented and validated.

Closed previous phases:

- P6-F.9.52 — Human Review Service Tests
- P6-F.9.53 — Human Review Model + Minimal Service Implementation
- P6-F.9.54 — Human Review Repository Contract Alignment
- P6-F.9.55 — Human Review PostgreSQL Repository Integration Test

Current validated internal contract:

- `HumanReviewAction`
- `HumanReviewResult`
- `HumanReviewService`
- `HumanReviewService.apply_action(action)`
- Repository contract:
  - `repository.get_by_id(id_solicitud)`
  - `repository.update(request)`

The service has already been validated against:

- fake repository tests
- `PostgresAppointmentRequestRepository` using local SQLite-style test infrastructure

## Objective

Define the backend API boundary for future doctor/human review actions before implementing any endpoint.

This phase does not implement the API.

It defines:

- whether an endpoint is needed
- proposed endpoint route
- request contract
- response contract
- supported actions
- error behavior
- security boundary
- notification boundary
- future Swagger validation plan

## Core Decision

A backend API boundary is useful and should be introduced in a later implementation phase.

Reason:

Future review surfaces such as Google Sheets, Telegram buttons, internal admin UI, or manual tools should not mutate appointment state directly.

All human review actions must pass through backend validation.

Correct future direction:

```text
Doctor-facing surface
→ backend human review endpoint
→ HumanReviewService
→ AppointmentRequestRepository
→ PostgreSQL
→ optional future notification adapter

Incorrect direction:

Google Sheets / Telegram / n8n
→ direct appointment status mutation
Proposed Endpoint

Recommended future route:

POST /internal/human-review/actions

Alternative if grouped under appointment requests:

POST /internal/appointment-requests/{id_solicitud}/review-action

Recommended route for first implementation:

POST /internal/human-review/actions

Reason:

The action itself already carries id_solicitud, and this route can later support multiple doctor-facing surfaces without coupling to one URL style.

Request Contract

Recommended request body:

{
  "id_solicitud": "SOL-20260613-090329-503926-0163",
  "action": "confirm",
  "actor": "dra_daleman",
  "notes": "Confirmado por revisión humana",
  "confirmed_date": "2026-06-16",
  "confirmed_franja": "5:00 p. m.–7:00 p. m.",
  "alternative_date": null,
  "alternative_franja": null,
  "missing_fields": null,
  "reason": null
}

The request body maps directly to:

HumanReviewAction
Supported Actions

The endpoint must accept only:

confirm
request_missing_data
propose_alternative
reschedule
cancel
close

Any unsupported action must return a safe error.

Required Fields By Action
confirm

Required:

id_solicitud
action
actor

Optional:

confirmed_date
confirmed_franja
notes
request_missing_data

Required:

id_solicitud
action
actor
missing_fields

Optional:

notes
propose_alternative

Required:

id_solicitud
action
actor
alternative_date
alternative_franja

Optional:

reason
notes
reschedule

Required:

id_solicitud
action
actor
alternative_date
alternative_franja

Optional:

reason
notes
cancel

Required:

id_solicitud
action
actor

Optional:

reason
notes
close

Required:

id_solicitud
action
actor

Optional:

notes
Response Contract

Recommended successful response:

{
  "success": true,
  "id_solicitud": "SOL-20260613-090329-503926-0163",
  "previous_status": "pendiente_confirmacion",
  "new_status": "confirmada",
  "action": "confirm",
  "message": "Human review action applied.",
  "should_notify_patient": true,
  "patient_message": "Su cita ha sido confirmada para el 2026-06-16 en la franja 5:00 p. m.–7:00 p. m.",
  "error_code": null
}

The response maps directly to:

HumanReviewResult
Error Response Contract

The endpoint should return safe structured responses for business errors.

Examples:

Invalid action
{
  "success": false,
  "id_solicitud": "SOL-TEST",
  "previous_status": null,
  "new_status": null,
  "action": "invalid_action",
  "message": "Unsupported human review action.",
  "should_notify_patient": false,
  "patient_message": null,
  "error_code": "invalid_action"
}
Missing request
{
  "success": false,
  "id_solicitud": "SOL-MISSING",
  "previous_status": null,
  "new_status": null,
  "action": "confirm",
  "message": "Appointment request was not found.",
  "should_notify_patient": false,
  "patient_message": null,
  "error_code": "request_not_found"
}
Forbidden transition
{
  "success": false,
  "id_solicitud": "SOL-CANCELLED",
  "previous_status": "cancelada",
  "new_status": null,
  "action": "confirm",
  "message": "Transition is not allowed.",
  "should_notify_patient": false,
  "patient_message": null,
  "error_code": "forbidden_transition"
}
Missing required fields
{
  "success": false,
  "id_solicitud": "SOL-TEST",
  "previous_status": null,
  "new_status": null,
  "action": "request_missing_data",
  "message": "missing_fields is required for request_missing_data.",
  "should_notify_patient": false,
  "patient_message": null,
  "error_code": "missing_required_fields"
}
HTTP Status Strategy

Recommended first implementation:

200 OK for successful business action.
200 OK for known business rejections returned by HumanReviewService.
422 Unprocessable Entity only for request body validation errors at FastAPI/Pydantic level.
500 Internal Server Error only for unexpected infrastructure errors.

Reason:

Known business rejections are part of the domain contract and should be visible in a structured HumanReviewResult.

Notification Boundary

The endpoint must not send WhatsApp messages in its first implementation.

Allowed:

return should_notify_patient
return patient_message

Not allowed yet:

call WhatsApp Cloud API
update interactions as if a message was sent
mark outbound notification as delivered
trigger Telegram or n8n

Future patient notification must be a separate named phase.

Security Boundary

This endpoint must not be public patient-facing API.

It is an internal/admin endpoint.

Minimum future security options:

internal API key header
private admin token
Basic auth for early internal testing
later proper admin auth if an internal UI exists

Recommended first implementation:

Require an internal header such as:

X-Internal-Admin-Token: <secret>

The secret must come from environment variables.

Do not hardcode secrets.

Do not expose this endpoint publicly without protection.

Actor Rule

The actor field is required.

For now, accepted actor examples:

dra_daleman
admin
system_test

Future implementation may restrict actor values.

For the first implementation, actor must be non-empty and must be stored through updated_by.

Audit Boundary

P6-F.9.56 does not implement audit events.

However, the API boundary must not block future audit logging.

Recommended future phase:

Create appointment_request_events table.

Future event fields:

event_id
id_solicitud
previous_status
new_status
action
actor
notes
reason
created_at

For now:

updated_by on appointment_requests is sufficient for the first internal contract.
OpenAPI / Swagger Validation Plan

When implemented, Swagger should validate:

confirm pending request.
cancel pending request.
request_missing_data pending request.
propose_alternative pending request.
reschedule confirmed request.
close confirmed request.
invalid action returns structured rejection.
missing request returns structured rejection.
forbidden transition returns structured rejection.
missing required fields returns structured rejection.
response includes should_notify_patient.
no WhatsApp message is sent.
Out Of Scope

Do not implement in P6-F.9.56:

API endpoint
API auth
Google Sheets adapter
Telegram buttons
n8n workflow
Calendar integration
doctor confirmation automation
patient notification sending
WhatsApp sending
production activation
campaigns
therapy package/session tracking
Future Implementation Candidate

Recommended next phase:

P6-F.9.57 — Human Review API Endpoint Tests

Purpose:

Create tests for the internal endpoint boundary before implementing it.

Test first:

endpoint requires internal token
valid confirm action calls service and returns result
invalid token is rejected
invalid action returns safe result
missing request returns safe result
no WhatsApp sending occurs

Implementation after tests only.
