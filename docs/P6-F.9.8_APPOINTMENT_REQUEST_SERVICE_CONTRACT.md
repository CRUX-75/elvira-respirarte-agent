# P6-F.9.8 — AppointmentRequestService Contract

## Status

Draft — Specification first.

This document defines the service-level contract for the future `AppointmentRequestService`.

No implementation is included in this phase.

---

## Context

Previous phases already defined and validated:

- `AppointmentRequest` internal model
- Appointment request lifecycle rules
- lifecycle validator
- factory contract
- factory implementation
- progress handoff documentation

The current test baseline before this phase is:

```text
44 passed

The repository uses:

app/

not:

src/
Goal

Define the contract of the service that will orchestrate appointment request behavior around the existing internal model, lifecycle validator, and factory.

The service will be responsible for:

Creating new appointment requests.
Managing valid lifecycle transitions.
Preventing duplicate active appointment requests.
Preserving the same id_solicitud during contraoffers and rescheduling.
Providing a clean future boundary for persistence and external integrations.

This phase defines the service contract only.

Explicitly Out of Scope

The following are not part of P6-F.9.8:

Database implementation
SQLAlchemy repository
PostgreSQL persistence
Google Sheets integration
Calendar integration
Telegram notifications
n8n workflows
WhatsApp sending changes
treatment plan tracking
therapy session package tracking
remaining sessions tracking
executed sessions tracking
automatic appointment confirmation

This service contract must stay focused only on appointment request orchestration.

Service Name

The future service should be named:

AppointmentRequestService

Expected future location:

app/services/appointment_request_service.py

This file must not be created in this phase unless explicitly approved in a later implementation step.

Core Responsibility

AppointmentRequestService acts as the application-level orchestration layer for appointment requests.

It should coordinate:

existing AppointmentRequest model
existing factory
existing lifecycle validator
future persistence layer
future human-visible operational inbox

It should not contain low-level database logic, external API calls, or UI-specific formatting.

Design Principle

The service must preserve deterministic appointment request state.

The LLM must never decide:

whether a new appointment request should be created
whether an existing request should be reused
whether a transition is valid
whether a duplicate active request exists
whether a contraoffer or reschedule keeps the same request
whether a request is confirmed, cancelled, or completed

Those decisions belong to deterministic Python logic.

Active Appointment Request Concept

An active appointment request is any request that is not in a terminal state.

The following states are considered active:

pendiente
contraoferta
reagendada
confirmada

The following states are considered terminal:

cancelada
completada

Reasoning:

pendiente is active because the request awaits doctor review or action.
contraoferta is active because the same request is still being negotiated.
reagendada is active because the request remains valid but changed.
confirmada is active because the appointment exists and has not yet been completed or cancelled.
cancelada ends the request.
completada ends the request.
Duplicate Active Request Prevention

The service must prevent creating a second active appointment request for the same patient when one already exists.

The duplicate prevention rule is:

One patient may have only one active AppointmentRequest at a time.

If an active request already exists for the patient, the service must return or reuse the existing request instead of creating a new one.

This prevents:

duplicate rows in the future Solicitudes_Cita table
multiple active requests for the same appointment conversation
fragmented appointment negotiation
losing the original id_solicitud
id_solicitud Preservation Rule

The service must preserve the original id_solicitud during:

contraoffers
renegotiation of date
renegotiation of time range
rescheduling
state transition to reagendada

A contraoffer or reschedule must update the existing appointment request, not create a new request.

Correct behavior:

SOL-20260526-073022-0163
pendiente -> contraoferta -> reagendada -> confirmada

Incorrect behavior:

SOL-20260526-073022-0163
pendiente -> contraoferta

SOL-20260526-081145-0163
reagendada

The second example is incorrect because the reschedule created a new request instead of preserving the original request identity.

Expected Service Dependencies

The future service may depend on the following internal components:

AppointmentRequest
AppointmentRequestFactory
AppointmentRequestLifecycleValidator

The future service may later depend on a repository interface, but no repository should be implemented in this phase.

Possible future repository boundary:

AppointmentRequestRepository

This contract should allow a future repository to provide:

find active request by phone number
save new request
update existing request
get request by id_solicitud

But the repository itself is out of scope for this phase.

Proposed Service Operations

The future service should expose operations equivalent to the following conceptual methods.

These are contract definitions, not implementation requirements for this phase.

1. create_or_reuse_active_request

Purpose:

Create a new appointment request only if the patient does not already have an active one.

If an active request already exists, return the existing active request.

Conceptual signature:

create_or_reuse_active_request(input_data) -> AppointmentRequest

Required behavior:

Check whether the patient already has an active appointment request.
If yes, return the existing request.
If no, use the factory to create a new request.
The new request should start in the correct initial state defined by the model/factory contract.
Do not create duplicate active requests.

Expected result cases:

Case	Expected Behavior
No active request exists	Create new request
Active request exists in pendiente	Reuse existing request
Active request exists in contraoferta	Reuse existing request
Active request exists in reagendada	Reuse existing request
Active request exists in confirmada	Reuse existing request
Last request is cancelada	Create new request
Last request is completada	Create new request
2. transition_request

Purpose:

Transition an existing appointment request from one lifecycle state to another.

Conceptual signature:

transition_request(id_solicitud, target_state, transition_data) -> AppointmentRequest

Required behavior:

Load or receive the existing appointment request.
Validate the transition using the lifecycle validator.
Reject invalid transitions.
Preserve the same id_solicitud.
Apply only the fields relevant to the transition.
Return the updated request.

The service must not bypass lifecycle validation.

3. apply_contraoffer

Purpose:

Apply a doctor contraoffer to the same active appointment request.

Conceptual signature:

apply_contraoffer(id_solicitud, contraoffer_data) -> AppointmentRequest

Required behavior:

Keep the same id_solicitud.
Transition the request to contraoferta if valid.
Store proposed alternative date/time range fields according to the model contract.
Do not create a new request.
Do not confirm availability automatically.
4. apply_reschedule

Purpose:

Apply a rescheduling update to the same existing appointment request.

Conceptual signature:

apply_reschedule(id_solicitud, reschedule_data) -> AppointmentRequest

Required behavior:

Keep the same id_solicitud.
Transition the request to reagendada if valid.
Update rescheduled date/time range fields according to the model contract.
Do not create a new request.
Do not treat rescheduling as a new appointment request.
5. cancel_request

Purpose:

Cancel an existing appointment request.

Conceptual signature:

cancel_request(id_solicitud, reason) -> AppointmentRequest

Required behavior:

Validate whether cancellation is allowed from the current state.
Transition to cancelada.
Preserve id_solicitud.
Store cancellation reason if the model supports it or future contract defines it.
Mark the request as terminal.
6. complete_request

Purpose:

Mark an appointment request as completed.

Conceptual signature:

complete_request(id_solicitud) -> AppointmentRequest

Required behavior:

Validate whether completion is allowed from the current state.
Transition to completada.
Preserve id_solicitud.
Mark the request as terminal.
State Transition Contract

The service must never define lifecycle rules independently.

Lifecycle rules belong to:

AppointmentRequestLifecycleValidator

The service must call the lifecycle validator before applying state changes.

The service may orchestrate transitions, but it must not duplicate lifecycle logic.

Request Identity Contract

The service must treat id_solicitud as the stable identity of one appointment request lifecycle.

The following events must remain under the same id_solicitud:

initial appointment request
doctor contraoffer
patient accepting alternative
patient rejecting alternative
renegotiation
rescheduling
final confirmation
cancellation
completion

A new id_solicitud should only be generated when:

no active request exists for the patient
the previous request is terminal
a truly new appointment request starts
Patient Identity Contract

The first duplicate prevention key should be:

telefono

The service should use the normalized patient phone number as the primary patient identity for active request lookup.

Future phases may add stronger patient identity handling, but this phase assumes phone number is the stable operational key.

Error Handling Contract

The future service should fail explicitly and predictably.

Expected service-level errors may include:

Error	Meaning
ActiveAppointmentRequestExists	A new request was attempted while active request exists
AppointmentRequestNotFound	Requested id_solicitud does not exist
InvalidAppointmentRequestTransition	Lifecycle validator rejected the transition
InvalidAppointmentRequestInput	Required service input is missing or invalid

Whether these are implemented as custom exceptions or result objects will be decided in the implementation phase.

This document only defines the expected failure cases.

Persistence Boundary

The service should be designed so persistence can be added later.

The service contract should not assume:

Google Sheets as source of truth
n8n as state manager
Calendar as source of truth
Telegram as state manager
LLM output as state manager

Future persistence should likely follow this direction:

AppointmentRequestService
    -> AppointmentRequestRepository
        -> PostgreSQL
        -> optional Google Sheets sync/read model later

Google Sheets, when added later, should be treated as a human-visible operational inbox, not as the core source of truth.

Google Sheets Boundary

Google Sheets is explicitly out of scope for this phase.

When integrated in a future phase, it should not own:

lifecycle validation
duplicate prevention
request identity
appointment state authority
transition rules

The Python application must remain the authority.

n8n Boundary

n8n is explicitly out of scope for this phase.

n8n must not own:

appointment request state
duplicate prevention
lifecycle transitions
request identity
appointment scheduling truth
persistence rules

n8n may only be considered later for auxiliary notifications or non-critical workflow automation.

Calendar Boundary

Calendar integration is explicitly out of scope for this phase.

The service contract must not confirm real availability.

Appointment request lifecycle is not the same as calendar booking.

A request may become confirmada only through deterministic business logic defined in future phases, not through LLM wording.

LLM Boundary

The LLM may later help phrase messages to the patient.

The LLM must not decide:

whether to create a request
whether to reuse a request
whether a transition is valid
whether a slot is available
whether an appointment is confirmed
whether a request is duplicated
whether to generate a new id_solicitud

The service must expose deterministic outcomes that the response layer can safely phrase.

Acceptance Criteria

P6-F.9.8 is complete when:

This document exists at:
docs/P6-F.9.8_APPOINTMENT_REQUEST_SERVICE_CONTRACT.md
The document defines the future AppointmentRequestService contract.
The document defines duplicate active request prevention.
The document defines id_solicitud preservation.
The document keeps DB, Google Sheets, Calendar, Telegram, n8n, and therapy session tracking out of scope.
The document defines expected service operations.
The document defines service boundaries.
No implementation code has been created.
Existing tests remain unchanged.
Next Phase

After this spec is reviewed and accepted, the next phase should be:

P6-F.9.9 — AppointmentRequestService Implementation

Expected future implementation should happen only after this contract is accepted.

Implementation should likely include:

app/services/appointment_request_service.py
tests for duplicate active request prevention
tests for id_solicitud preservation
tests for contraoffer reuse
tests for reschedule reuse
tests for terminal state allowing new request creation

No implementation should begin before the spec is approved.
