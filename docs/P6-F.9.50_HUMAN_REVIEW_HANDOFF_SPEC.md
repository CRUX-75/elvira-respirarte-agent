# P6-F.9.50 — Human Review Handoff Spec

## Status

SPEC / DESIGN ONLY

## Context

The production appointment request flow has already been validated end-to-end.

Current confirmed behavior:

1. Elvira can receive a real WhatsApp appointment request.
2. Elvira can resolve date availability using deterministic rules and KB schedules.
3. Elvira can block unavailable dates such as Colombia holidays.
4. Elvira can present candidate time windows.
5. Elvira can register a valid AppointmentRequest.
6. Final appointment confirmation remains with Dra. D'Aleman.

The current production safety baseline remains:

- `WHATSAPP_SENDING_ENABLED=false`
- No uncontrolled real patients.
- No campaigns.
- No Google Sheets implementation.
- No Telegram implementation.
- No n8n workflow implementation.
- No Calendar integration.
- No doctor confirmation automation.

## Objective

Define how a persisted `AppointmentRequest` moves from Elvira into human review by Dra. D'Aleman.

This phase does not implement the handoff.

It defines the operational contract, lifecycle, required fields, allowed human actions, status transitions, and future adapter boundaries.

## Core Principle

Elvira registers requests.

Dra. D'Aleman confirms appointments.

The system must not let Elvira auto-confirm an appointment unless a future explicitly named phase changes that rule.

## Current Source of Truth

The source of truth remains PostgreSQL.

AppointmentRequest internal flow:

```text
WhatsApp message
→ FastAPI /webhook
→ state machine
→ AppointmentRequestService
→ AppointmentRequestRepository
→ PostgreSQL appointment_requests
→ future human review inbox adapter

Google Sheets, Telegram, n8n, or Calendar must not become the source of truth.

They may later act only as:

visual inbox
notification layer
auxiliary workflow
doctor-facing review surface
Human Review Object

A human review item represents an AppointmentRequest that needs doctor action.

Minimum required fields:

id_solicitud
telefono
nombre_paciente
fecha_solicitada
franja_solicitada
servicio_solicitado
direccion_paciente
estado_solicitud
fecha_creacion
ultima_actualizacion
notas_paciente
source_channel
source_interaction_id

Optional useful fields:

patient_id
appointment_context_snapshot
conversation_summary
doctor_notes
reviewed_by
reviewed_at
human_decision
proposed_alternative_date
proposed_alternative_franja
cancellation_reason
reschedule_reason
Required Doctor View

Dra. D'Aleman should be able to see:

Who requested the appointment.
How to contact the patient.
Requested date.
Requested time window.
Requested service, if captured.
Patient address, if captured.
Current request status.
Whether the request is new, pending confirmation, confirmed, rescheduled, cancelled, or closed.
Any patient notes relevant to the request.
The latest human action taken.
AppointmentRequest Status Contract

Valid statuses:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada

Active statuses:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada

Terminal statuses:

cancelada
cerrada

Invalid statuses that must not be introduced:

pendiente
contraoferta
completada
Human Actions

The future human review flow must support these doctor actions:

1. Confirm request

Doctor accepts the requested date and franja.

Expected status transition:

pendiente_confirmacion → confirmada

Expected future patient message:

Su cita ha sido confirmada para el [fecha] en la franja [franja]. La Dra. D'Aleman le atenderá según la ruta del día.

Important:

The message may confirm the franja, not an exact arrival hour unless the doctor explicitly provides one.

2. Request missing data

Doctor or system identifies that required information is missing.

Examples:

missing address
missing service
unclear patient name
unclear location coverage

Expected status transition:

nueva / pendiente_confirmacion → pendiente_datos

Expected future patient message:

Para continuar con su solicitud, por favor indíquenos [dato faltante].
3. Propose alternative

Doctor cannot accept the requested date/franja and proposes an alternative.

Expected status transition:

pendiente_confirmacion → pendiente_confirmacion

Why same status:

A contraoffer is not a separate status in the current contract.

Operationally, it remains pendiente_confirmacion until the patient accepts or rejects the alternative.

Expected future patient message:

La Dra. D'Aleman no tiene disponibilidad en la franja solicitada. Puede atenderle el [fecha alternativa] en la franja [franja alternativa]. ¿Desea que dejemos esa opción como solicitud?
4. Reschedule

Doctor changes an already confirmed or active request to a new date/franja.

Expected status transition:

confirmada / pendiente_confirmacion → reagendada

Expected future patient message:

Su cita ha sido reagendada para el [fecha] en la franja [franja]. 
5. Cancel request

Doctor or patient cancels the request.

Expected status transition:

nueva / pendiente_datos / pendiente_confirmacion / confirmada / reagendada → cancelada

Expected future patient message:

Su solicitud de cita ha sido cancelada. Si necesita una nueva atención, puede escribirnos nuevamente.
6. Close request

Doctor marks the request as operationally completed or no longer requiring action.

Expected status transition:

confirmada / reagendada / cancelada → cerrada

Expected patient message:

No automatic patient message required unless explicitly configured later.

Status Transition Rules

Allowed transitions:

nueva → pendiente_datos
nueva → pendiente_confirmacion
nueva → confirmada
nueva → cancelada

pendiente_datos → pendiente_confirmacion
pendiente_datos → cancelada

pendiente_confirmacion → confirmada
pendiente_confirmacion → pendiente_datos
pendiente_confirmacion → pendiente_confirmacion
pendiente_confirmacion → reagendada
pendiente_confirmacion → cancelada

confirmada → reagendada
confirmada → cancelada
confirmada → cerrada

reagendada → confirmada
reagendada → cancelada
reagendada → cerrada

cancelada → cerrada

Forbidden transitions:

cerrada → any active status
cancelada → confirmada
cancelada → reagendada

A cancelled or closed request must not be silently reactivated.

If a patient asks again after cancellation or closure, the system should create or guide toward a new request in a future phase.

Human Review Inbox Contract

A future human review inbox must be treated as a projection of PostgreSQL data.

It must not own the lifecycle.

Future inbox rows may contain:

request ID
patient name
phone
requested date
requested franja
requested service
address
current status
doctor action
doctor notes
proposed alternative date
proposed alternative franja
last sync timestamp

The inbox may allow doctor decisions, but those decisions must be written back through the backend service layer.

Correct direction:

Doctor action
→ backend endpoint/service
→ PostgreSQL update
→ optional notification to patient
→ optional inbox sync

Incorrect direction:

Google Sheet cell edit
→ becomes source of truth without validation
Future Adapter Boundaries
Google Sheets

Allowed future role:

human-visible operational inbox
simple review table
lightweight status dashboard

Not allowed:

source of truth
bypassing AppointmentRequestService
uncontrolled state mutation
appointment lifecycle logic
Telegram

Allowed future role:

notify Dra. D'Aleman of a new request
send a compact summary
provide action buttons only if routed back through backend validation

Not allowed:

owning lifecycle logic
directly mutating Google Sheets as source of truth
confirming appointments without backend validation
n8n

Allowed future role:

auxiliary notification orchestration
low-risk admin automations
non-critical reminders

Not allowed:

core appointment state machine
persistence rules
scheduling logic
doctor decision source of truth
Calendar

Allowed future role:

optional later calendar visibility
optional confirmed appointment mirror

Not allowed in current design:

deciding availability
confirming appointments automatically
replacing KB_Horarios and doctor review
Required Data Gaps Before Implementation

Before implementing a human review adapter, the project should decide whether these fields must be captured before request registration or can be completed during review:

servicio_solicitado
direccion_paciente
notas_paciente

Current doctor feedback requires:

service requested visible in the request table
patient address visible in the request table

Decision still required:

Should Elvira ask for missing service/address before creating the AppointmentRequest, or create the request first and mark it as pendiente_datos?

Recommended future approach:

Keep the current appointment request creation working.
Add missing data capture incrementally.
If date/franja is valid but service/address is missing, create or update request as pendiente_datos only when the flow explicitly supports it.
Do not overload the current validated appointment happy path prematurely.
Patient-Facing Communication Rules

Elvira may say:

request registered
doctor will review
doctor will confirm
selected franja was recorded as preference
exact arrival hour is not guaranteed unless doctor confirms

Elvira must not say:

appointment is confirmed automatically
doctor will arrive at an exact hour unless explicitly confirmed
unavailable days are available
appointment has been created if persistence failed
request was sent to doctor if no future notification/inbox adapter exists yet

Safe current wording after AppointmentRequest creation:

Hemos recibido su solicitud para el [fecha] en la franja [franja]. La Dra. D'Aleman revisará la disponibilidad y le confirmará la cita.
Test Plan For Future Implementation

When implementation begins in a later phase, tests should cover:

Human review item can be built from AppointmentRequest.
Required fields are mapped correctly.
Doctor confirm action changes status to confirmada.
Doctor missing-data action changes status to pendiente_datos.
Doctor alternative proposal keeps status as pendiente_confirmacion.
Doctor reschedule action changes status to reagendada.
Doctor cancel action changes status to cancelada.
Doctor close action changes status to cerrada.
Forbidden transitions are rejected.
External adapter cannot bypass backend validation.
Patient message is not sent if outbound sending is disabled.
Audit fields are preserved.
Swagger Validation Plan For Future Implementation

When a backend review endpoint exists, Swagger validation should confirm:

Fetch pending human review item.
Confirm request.
Propose alternative.
Mark missing data.
Cancel request.
Attempt forbidden transition and receive safe rejection.
Verify PostgreSQL state after each action.
Verify no real WhatsApp message is sent unless explicitly enabled in a named controlled phase.
Out Of Scope

Do not implement in P6-F.9.50:

Google Sheets adapter
Telegram bot/actions
n8n workflow
Calendar integration
doctor confirmation automation
patient notification sending
campaigns
therapy package/session tracking
real patient activation
real WhatsApp sending
Closure Criteria

P6-F.9.50 can be closed when:

Human review lifecycle is specified.
Required fields are identified.
Allowed doctor actions are defined.
Status transition rules are defined.
Future adapter boundaries are clear.
Out-of-scope items are explicit.
No runtime code has been changed.
Next implementation phase is named.
Recommended Next Phase

P6-F.9.51 — Human Review Internal Model And Service Contract

Purpose:

Create the internal backend contract for human review actions without connecting Google Sheets, Telegram, n8n, or Calendar.

Potential deliverables:

Human review action model.
Human review service method signatures.
Transition validation contract.
Unit tests for allowed and forbidden transitions.
No external adapters yet.
