# P6-F.9.4 — AppointmentRequest Lifecycle Validation

## Status

Draft specification — SDD first pass.

No implementation code must be written before this specification is reviewed and accepted.

---

## 1. Purpose

This document defines the lifecycle validation rules for the internal `AppointmentRequest` model.

The goal is to protect the appointment request flow from invalid or unsafe state transitions.

This phase does not implement persistence, Google Sheets, calendar automation, Telegram notifications, or n8n workflows.

---

## 2. Contractual Sources

This lifecycle validation spec is based on:

```text
docs/P6-F.9.1_SOLICITUDES_CITA_OPERATIONAL_CONTRACT.md
docs/P6-F.9.2_APPOINTMENT_REQUEST_INTERNAL_MODEL.md

The internal lifecycle validator must remain aligned with the validated operational contract and the internal model specification.

3. Scope
In scope

This phase defines:

Allowed lifecycle transitions for AppointmentRequest.
Rejected invalid transitions.
Protection against automatic confirmation.
Rescheduling behavior.
Same-request continuity during contraoffers and renegotiation.
Minimal test expectations.
Out of scope

The following are explicitly excluded:

Database persistence.
Repository layer.
Google Sheets implementation.
Google Sheets append/update logic.
Google Calendar integration.
Calendar availability checking.
Automatic appointment confirmation.
Telegram notifications.
n8n workflows.
Therapy-session tracking.
Treatment package tracking.
Remaining-session counters.
4. Core Rule

An AppointmentRequest is not a confirmed appointment.

The lifecycle validator must protect this rule:

requested != accepted != confirmed

Patient-requested or patient-accepted data must not automatically become confirmed appointment data.

Only a human confirmation or an explicitly authorized backend action may move a request to confirmada.

5. Lifecycle States

The supported states are:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada

These states are already defined by the internal model.

6. Allowed Transitions

The lifecycle validator must allow only the following transitions:

nueva -> pendiente_datos
nueva -> pendiente_confirmacion

pendiente_datos -> pendiente_confirmacion
pendiente_datos -> cancelada

pendiente_confirmacion -> confirmada
pendiente_confirmacion -> cancelada

confirmada -> reagendada
confirmada -> cancelada
confirmada -> cerrada

reagendada -> pendiente_confirmacion
reagendada -> confirmada
reagendada -> cancelada

cancelada -> cerrada

No other transition should be allowed by default.

7. Transition Meaning
7.1 nueva -> pendiente_datos

The request exists, but required data is still missing.

Example:

Patient: "Quiero una cita."

The system still needs date, range, service, address, or other operational details.

7.2 nueva -> pendiente_confirmacion

The request is created with enough information for human review.

Example:

Patient provides date, range, service, and address in the first message.

This does not mean the appointment is confirmed.

7.3 pendiente_datos -> pendiente_confirmacion

The missing information was collected.

The request is now ready for Dra. D’Aleman or the operational team to review.

7.4 pendiente_confirmacion -> confirmada

The request was confirmed by Dra. D’Aleman or the operational team.

This transition must be protected.

It must not happen simply because the patient requested or accepted a slot.

7.5 confirmada -> reagendada

A confirmed appointment request is being rescheduled.

This must preserve the same id_solicitud when it belongs to the same original appointment request.

7.6 reagendada -> pendiente_confirmacion

A rescheduled proposal needs human review again.

Example:

Patient accepted a new alternative, but the doctor has not confirmed it yet.
7.7 reagendada -> confirmada

A rescheduled appointment has been confirmed by Dra. D’Aleman or the operational team.

7.8 Any active state -> cancelada

Cancellation may be allowed from active states:

pendiente_datos
pendiente_confirmacion
confirmada
reagendada

The first implementation does not allow nueva -> cancelada unless needed later.

7.9 cancelada -> cerrada

A cancelled request can be closed or archived.

7.10 confirmada -> cerrada

A confirmed request can be closed after operational handling.

This does not imply therapy-session tracking.

8. Invalid Transition Examples

The validator must reject examples like:

nueva -> confirmada
pendiente_datos -> confirmada
cancelada -> confirmada
cerrada -> confirmada
cerrada -> pendiente_confirmacion
cancelada -> reagendada
nueva -> reagendada

These transitions are unsafe or semantically incorrect.

9. Confirmation Protection

The transition to confirmada must be treated as sensitive.

Allowed:

pendiente_confirmacion -> confirmada
reagendada -> confirmada

Not allowed:

nueva -> confirmada
pendiente_datos -> confirmada

The validator should support a future explicit confirmation actor, for example:

confirmed_by = doctor
confirmed_by = staff
confirmed_by = system_admin

But actor validation is not required in this phase.

10. Rescheduling Rule

Contraoffers and renegotiation should remain in the same appointment request.

The validator must support this operational principle:

Do not create a new AppointmentRequest just because the patient accepts an alternative.

When rescheduling belongs to the same appointment request, the same id_solicitud must be preserved.

This phase only validates lifecycle transitions.

It does not implement storage or mutation logic yet.

11. Suggested Implementation Shape

Future implementation file:

app/services/appointment_request_lifecycle.py

Suggested functions:

def is_valid_transition(current_status: str, next_status: str) -> bool:
    ...

def validate_transition(current_status: str, next_status: str) -> None:
    ...

Suggested exception:

class InvalidAppointmentRequestTransition(ValueError):
    ...

The implementation should stay small and deterministic.

No database access.

No LLM call.

No external service call.

12. Test Expectations

Future test file:

tests/test_appointment_request_lifecycle.py

Required test coverage:

Allows all explicitly valid transitions.
Rejects nueva -> confirmada.
Rejects pendiente_datos -> confirmada.
Allows pendiente_confirmacion -> confirmada.
Allows confirmada -> reagendada.
Allows reagendada -> pendiente_confirmacion.
Allows reagendada -> confirmada.
Rejects transitions from cerrada to active states.
Rejects unknown statuses.
Does not import or depend on n8n, Google Sheets, Calendar, Telegram, DB, or LLM services.
13. Acceptance Criteria

P6-F.9.4 is accepted when:

This specification exists under:
docs/P6-F.9.4_APPOINTMENT_REQUEST_LIFECYCLE_VALIDATION.md
The spec defines allowed transitions.
The spec defines invalid transition examples.
The spec protects confirmation from happening automatically.
The spec includes rescheduling via reagendada.
The spec keeps contraoffers inside the same appointment request.
The spec explicitly excludes:
Google Sheets
Google Calendar
Telegram
n8n
therapy-session tracking
database persistence
LLM calls
No implementation code has been created before this specification.
14. Next Step After Approval

After this spec is reviewed and accepted, the next implementation step may be:

P6-F.9.5 — Implement AppointmentRequest lifecycle validator

Expected implementation tasks:

Create app/services/appointment_request_lifecycle.py.
Create tests/test_appointment_request_lifecycle.py.
Add deterministic transition validation.
Run targeted tests.
Run existing appointment request model tests again.
