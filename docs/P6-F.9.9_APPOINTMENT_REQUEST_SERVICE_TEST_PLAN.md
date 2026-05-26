# P6-F.9.9 — AppointmentRequestService Test Plan

## Status

Draft — Test plan before implementation.

This document defines the expected test coverage for the future `AppointmentRequestService`.

No production service implementation is included in this phase.

---

## Context

Previous closed phase:

```text
P6-F.9.8 — AppointmentRequestService Contract

P6-F.9.8 defined that the future service must orchestrate:

appointment request creation
active request reuse
duplicate active request prevention
lifecycle transitions
contraoffer handling
rescheduling handling
id_solicitud preservation
deterministic ownership in Python

Current validation baseline before this phase:

120 passed
Goal

Define the test cases that must exist before or alongside the first implementation of:

app/services/appointment_request_service.py

The tests must prove that the service follows the contract before connecting any database, Google Sheets, Calendar, Telegram, WhatsApp sending, or n8n logic.

Explicitly Out of Scope

The following must not be tested or implemented in this phase:

PostgreSQL persistence
SQLAlchemy repository
Google Sheets sync
Calendar availability
Telegram notification
n8n workflow behavior
WhatsApp sending
treatment/session package tracking
therapy session remaining count
automatic appointment confirmation

This test plan is only for the deterministic service contract.

Test File

The future test file should be:

tests/test_appointment_request_service.py
Test Strategy

Because no database repository exists yet, the first service tests should use an in-memory fake repository.

The fake repository should simulate only the minimum persistence behavior needed by the service contract:

save a request
update a request
get request by id_solicitud
find active request by telefono

This fake must stay inside the test file.

It must not become production code.

Fake Repository Contract

The test fake should expose behavior equivalent to:

save(request) -> AppointmentRequest
update(request) -> AppointmentRequest
get_by_id(id_solicitud) -> AppointmentRequest | None
find_active_by_telefono(telefono) -> AppointmentRequest | None

The fake repository should determine active requests using the same active/terminal distinction defined in the contract.

Active states:

pendiente
contraoferta
reagendada
confirmada

Terminal states:

cancelada
completada
Required Test Cases
1. Creates new request when no active request exists

Given:

no existing active request for telefono

When:

create_or_reuse_active_request is called

Then:

a new AppointmentRequest is created
the request is saved
the initial status is correct
the returned request has an id_solicitud
2. Reuses active pendiente request

Given:

an existing request for the same telefono
status is pendiente

When:

create_or_reuse_active_request is called again

Then:

no new request is created
the existing request is returned
the same id_solicitud is preserved
3. Reuses active contraoferta request

Given:

an existing request for the same telefono
status is contraoferta

When:

create_or_reuse_active_request is called again

Then:

no new request is created
the existing request is returned
the same id_solicitud is preserved
4. Reuses active reagendada request

Given:

an existing request for the same telefono
status is reagendada

When:

create_or_reuse_active_request is called again

Then:

no new request is created
the existing request is returned
the same id_solicitud is preserved
5. Reuses active confirmada request

Given:

an existing request for the same telefono
status is confirmada

When:

create_or_reuse_active_request is called again

Then:

no new request is created
the existing request is returned
the same id_solicitud is preserved
6. Creates new request after cancelada

Given:

the last request for the same telefono
status is cancelada

When:

create_or_reuse_active_request is called

Then:

a new request is created
the new request has a different id_solicitud
the previous cancelled request remains unchanged
7. Creates new request after completada

Given:

the last request for the same telefono
status is completada

When:

create_or_reuse_active_request is called

Then:

a new request is created
the new request has a different id_solicitud
the previous completed request remains unchanged
8. Preserves id_solicitud during contraoffer

Given:

an existing active request
status allows contraoffer transition

When:

apply_contraoffer is called

Then:

the same request is updated
no new request is created
id_solicitud remains unchanged
status becomes contraoferta
contraoffer fields are updated according to the model contract
9. Preserves id_solicitud during reschedule

Given:

an existing active request
status allows reschedule transition

When:

apply_reschedule is called

Then:

the same request is updated
no new request is created
id_solicitud remains unchanged
status becomes reagendada
reschedule fields are updated according to the model contract
10. Rejects invalid lifecycle transition

Given:

an existing request
a transition not allowed by the lifecycle validator

When:

transition_request is called

Then:

the transition is rejected
the request is not modified
the original status remains unchanged
the service raises or returns a deterministic invalid transition error
11. Raises not found for unknown id_solicitud

Given:

no request exists with the provided id_solicitud

When:

transition_request, apply_contraoffer, apply_reschedule, cancel_request, or complete_request is called

Then:

the service fails explicitly
the error is deterministic
no new request is silently created
12. Terminal states are not active

Given:

multiple requests exist for the same telefono
one request is cancelada
one request is completada

When:

find_active_by_telefono is used by the service

Then:

neither terminal request is treated as active
a new request may be created
Expected Future Service Errors

The tests may expect service-level errors such as:

AppointmentRequestNotFound
InvalidAppointmentRequestTransition
InvalidAppointmentRequestInput

The exact implementation may use custom exceptions.

If custom exceptions are created, they should live near the service layer unless a broader project convention already exists.

Test Design Rules

The test suite should:

avoid database setup
avoid external APIs
avoid Google Sheets
avoid Calendar
avoid Telegram
avoid n8n
avoid WhatsApp sending
use deterministic input data
assert exact id_solicitud preservation where relevant
assert object count where duplicate prevention matters
verify that lifecycle validation is not bypassed
Acceptance Criteria

P6-F.9.9 is complete when:

this document exists at:
docs/P6-F.9.9_APPOINTMENT_REQUEST_SERVICE_TEST_PLAN.md
the expected service test file is defined
duplicate prevention tests are specified
id_solicitud preservation tests are specified
terminal state behavior is specified
invalid transition behavior is specified
no service implementation has been created yet
existing test suite still passes
Next Phase

After this test plan is accepted, the next phase should be:

P6-F.9.10 — AppointmentRequestService Tests

Expected next file:

tests/test_appointment_request_service.py

The service tests may initially fail until the service implementation exists.

That is acceptable only when intentionally entering the RED phase of test-driven implementation.
