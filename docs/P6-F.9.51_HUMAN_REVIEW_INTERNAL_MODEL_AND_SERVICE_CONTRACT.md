# P6-F.9.51 — Human Review Internal Model And Service Contract

## Status

SPEC / CONTRACT / PRE-IMPLEMENTATION

## Context

P6-F.9.50 defined the Human Review Handoff Spec.

The core decision remains:

Elvira registers appointment requests.

Dra. D'Aleman confirms, cancels, reschedules, or requests missing information.

PostgreSQL remains the source of truth.

Google Sheets, Telegram, n8n, and Calendar remain out of scope.

## Objective

Define the internal backend contract for human review actions before connecting any external adapter.

This phase prepares the service layer that will later allow a doctor-facing review surface to safely update AppointmentRequests.

## Scope

P6-F.9.51 defines:

- internal action model
- allowed doctor actions
- required payload fields per action
- status transition validation
- service method contract
- repository expectations
- audit expectations
- test plan

## Out Of Scope

Do not implement yet:

- Google Sheets adapter
- Telegram bot or buttons
- n8n workflow
- Calendar integration
- automatic doctor confirmation
- patient notification sending
- real WhatsApp sending
- campaigns
- therapy package/session tracking

## Source Of Truth

The source of truth remains:

```text
PostgreSQL appointment_requests

The service layer must be the only valid path for changing AppointmentRequest review state.

Correct future direction:

Doctor action
→ HumanReviewService
→ AppointmentRequestRepository
→ PostgreSQL
→ optional future notification adapter
→ optional future inbox sync

Incorrect direction:

Google Sheet edit
→ state changed without backend validation
Human Review Action Model

Recommended internal model name:

HumanReviewAction

Recommended fields:

id_solicitud: str
action: str
actor: str
notes: str | None
confirmed_date: date | None
confirmed_franja: str | None
alternative_date: date | None
alternative_franja: str | None
missing_fields: list[str] | None
reason: str | None
Supported Actions

Supported action values:

confirm
request_missing_data
propose_alternative
reschedule
cancel
close

No other action should be accepted.

Required Fields Per Action
confirm

Required:

id_solicitud
actor

Optional:

confirmed_date
confirmed_franja
notes

Expected transition:

pendiente_confirmacion → confirmada
nueva → confirmada
reagendada → confirmada
request_missing_data

Required:

id_solicitud
actor
missing_fields

Optional:

notes

Expected transition:

nueva → pendiente_datos
pendiente_confirmacion → pendiente_datos
propose_alternative

Required:

id_solicitud
actor
alternative_date
alternative_franja

Optional:

notes
reason

Expected transition:

pendiente_confirmacion → pendiente_confirmacion

Important:

A contraoffer is not a separate status.

The request remains pendiente_confirmacion.

reschedule

Required:

id_solicitud
actor
alternative_date
alternative_franja

Optional:

notes
reason

Expected transition:

confirmada → reagendada
pendiente_confirmacion → reagendada
cancel

Required:

id_solicitud
actor

Optional:

reason
notes

Expected transition:

nueva → cancelada
pendiente_datos → cancelada
pendiente_confirmacion → cancelada
confirmada → cancelada
reagendada → cancelada
close

Required:

id_solicitud
actor

Optional:

notes

Expected transition:

confirmada → cerrada
reagendada → cerrada
cancelada → cerrada
Forbidden Transitions

The service must reject:

cerrada → any active status
cancelada → confirmada
cancelada → reagendada
cancelada → pendiente_confirmacion
cancelada → pendiente_datos

A cancelled or closed request must not be silently reactivated.

Service Contract

Recommended service name:

HumanReviewService

Recommended public method:

apply_action(action: HumanReviewAction) -> HumanReviewResult

Recommended result model:

HumanReviewResult

Recommended result fields:

success: bool
id_solicitud: str
previous_status: str | None
new_status: str | None
action: str
message: str
should_notify_patient: bool
patient_message: str | None
error_code: str | None
Patient Notification Decision

P6-F.9.51 must not send messages.

However, the result may prepare whether a patient notification should be sent later.

Example:

should_notify_patient=true
patient_message="Su cita ha sido confirmada para..."

The actual sending belongs to a later named phase.

Audit Expectations

Every human review action should eventually record:

request ID
previous status
new status
action
actor
timestamp
notes
reason
changed fields

Implementation options for a later phase:

Add audit fields directly to appointment_requests.
Create an appointment_request_events table.
Use existing interaction logs only for patient-facing communication and a separate event table for human actions.

Recommended future direction:

Create appointment_request_events.

Do not overload interactions with doctor-side lifecycle events.

Repository Expectations

The repository layer should support or later support:

find request by id_solicitud
update request status
update confirmed/proposed date/franja fields if available
preserve existing request data
reject missing request safely
optionally append human review event
Test Plan

When implementing P6-F.9.51, add tests for:

confirm from pendiente_confirmacion to confirmada.
request_missing_data from pendiente_confirmacion to pendiente_datos.
propose_alternative keeps status as pendiente_confirmacion.
reschedule from confirmada to reagendada.
cancel from active status to cancelada.
close from confirmada to cerrada.
Invalid action is rejected.
Missing required fields are rejected.
Missing request is rejected.
Forbidden transition from cancelada to confirmada is rejected.
Forbidden transition from cerrada to active status is rejected.
Service result does not send WhatsApp messages.
Service result can prepare should_notify_patient and patient_message.
Implementation Boundary

Implementation should be internal only.

Allowed files in a future implementation phase may include:

app/models/human_review.py
app/services/human_review_service.py
tests/test_human_review_service.py

Only add repository methods if needed.

Do not add API endpoints yet unless a separate phase explicitly scopes it.

Closure Criteria

P6-F.9.51 can be closed when:

internal model contract is documented
service contract is documented
transition rules are documented
test plan is documented
implementation boundary is clear
no external adapter is introduced
no real sending is enabled
Recommended Next Phase

P6-F.9.52 — Human Review Service Tests

Purpose:

Create tests for the internal human review service contract before implementation.

No external adapters.

No API endpoints.

No Google Sheets.

No Telegram.

No n8n.

No Calendar.

No real WhatsApp sending.
