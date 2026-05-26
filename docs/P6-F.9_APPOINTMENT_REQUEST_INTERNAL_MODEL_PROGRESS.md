# P6-F.9 — AppointmentRequest Internal Model Progress

## Status

P6-F.9.2 to P6-F.9.7 completed.

This document summarizes the completed internal AppointmentRequest work before moving to the next chat/session.

---

## Completed Blocks

### P6-F.9.2 — AppointmentRequest Internal Model Spec

Status: DONE

Created:

```text
docs/P6-F.9.2_APPOINTMENT_REQUEST_INTERNAL_MODEL.md

Purpose:

Defined the internal Python model AppointmentRequest under SDD protocol.

Key decisions:

No code before spec.
AppointmentRequest separates:
requested data
accepted data
confirmed data
Added required operational fields:
direccion_domicilio
servicio_solicitado
Included lifecycle state:
reagendada
Explicitly excluded:
calendar automation
Google Sheets implementation
Telegram
n8n
therapy-session tracking
P6-F.9.3 — AppointmentRequest Internal Model

Status: DONE

Created:

app/models/appointment_request.py
tests/test_appointment_request_model.py

Implemented:

AppointmentRequestStatus
AppointmentRequestSource
AppointmentRequest

Validated:

minimal model creation
requested / accepted / confirmed separation
reagendada status
servicio_solicitado
direccion_domicilio
invalid status rejection
invalid source channel rejection, including n8n

Tests:

6 passed

Also updated:

app/models/__init__.py

No regressions detected.

P6-F.9.4 — AppointmentRequest Lifecycle Validation Spec

Status: DONE

Created:

docs/P6-F.9.4_APPOINTMENT_REQUEST_LIFECYCLE_VALIDATION.md

Defined:

allowed lifecycle transitions
invalid transition examples
confirmation protection
rescheduling behavior
same-request continuity during contraoffers and renegotiation

Explicitly excluded:

DB persistence
Google Sheets
Google Calendar
Telegram
n8n
LLM calls
therapy-session tracking
P6-F.9.5 — AppointmentRequest Lifecycle Validator

Status: DONE

Created:

app/services/appointment_request_lifecycle.py
tests/test_appointment_request_lifecycle.py

Implemented:

InvalidAppointmentRequestTransition
is_valid_transition()
validate_transition()

Validated:

all allowed transitions
invalid transitions rejected
nueva -> confirmada rejected
pendiente_datos -> confirmada rejected
pendiente_confirmacion -> confirmada allowed
confirmada -> reagendada allowed
reagendada -> pendiente_confirmacion allowed
reagendada -> confirmada allowed
unknown statuses rejected

Tests:

27 passed

Combined model + lifecycle tests:

33 passed
P6-F.9.6 — AppointmentRequest Factory Spec

Status: DONE

Created:

docs/P6-F.9.6_APPOINTMENT_REQUEST_FACTORY.md

Defined:

when a new AppointmentRequest may be created
required and optional creation inputs
id_solicitud generation
Colombia timezone requirement
confirmation protection at creation
anti-duplication principle for contraoffers
explicit exclusions

Key ID format:

SOL-YYYYMMDD-HHMMSS-LAST4

Timezone for visible ID:

America/Bogota
P6-F.9.7 — AppointmentRequest Factory Implementation

Status: DONE

Created:

app/services/appointment_request_factory.py
tests/test_appointment_request_factory.py

Implemented:

COLOMBIA_TIMEZONE
generate_appointment_request_id()
create_appointment_request()

Validated:

SOL prefix
Colombia time in id_solicitud
UTC-aware datetime conversion to Colombia time
last four phone digits
default estado_solicitud = nueva
optional patient name
requested date/range fields
confirmed fields remain None at creation
servicio_solicitado and direccion_domicilio included when provided
created_at and updated_at generated
source_interaction_id preserved

Tests:

factory tests passed

Full P6-F.9 model + lifecycle + factory test block:

44 passed
Current Files Added
docs/P6-F.9.2_APPOINTMENT_REQUEST_INTERNAL_MODEL.md
docs/P6-F.9.4_APPOINTMENT_REQUEST_LIFECYCLE_VALIDATION.md
docs/P6-F.9.6_APPOINTMENT_REQUEST_FACTORY.md
docs/P6-F.9_APPOINTMENT_REQUEST_INTERNAL_MODEL_PROGRESS.md

app/models/appointment_request.py
app/services/appointment_request_lifecycle.py
app/services/appointment_request_factory.py

tests/test_appointment_request_model.py
tests/test_appointment_request_lifecycle.py
tests/test_appointment_request_factory.py

Updated:

app/models/__init__.py
Current Test Status

Latest validated result:

44 tests passed

Targeted command:

pytest \
  tests/test_appointment_request_model.py \
  tests/test_appointment_request_lifecycle.py \
  tests/test_appointment_request_factory.py \
  -q
Architecture Boundaries Preserved

The implementation does not depend on:

database
Google Sheets
Google Calendar
Telegram
n8n
LLM/OpenAI
therapy-session tracking

The current implementation is pure internal Python logic.

Next Recommended Block

Next phase:

P6-F.9.8 — AppointmentRequestService Contract

Recommended next document:

docs/P6-F.9.8_APPOINTMENT_REQUEST_SERVICE_CONTRACT.md

Purpose:

Define the orchestration contract before implementing a service layer.

The service should eventually coordinate:

creating a new appointment request
preventing duplicate active requests
preserving id_solicitud during contraoffers and rescheduling
applying lifecycle transitions via appointment_request_lifecycle
preparing for future persistence
keeping Google Sheets as a later adapter, not source of truth

Still out of scope for P6-F.9.8:

actual DB implementation
Google Sheets implementation
Calendar automation
Telegram
n8n
therapy-session tracking
Suggested First Prompt for New Chat

We are continuing the Elvira / Respirarte project.

Current phase:

P6-F.9.8 — AppointmentRequestService Contract

Context:

P6-F.9.2 to P6-F.9.7 are complete.
AppointmentRequest model exists.
Lifecycle validator exists.
Factory exists.
Full targeted test block passed: 44 tests.
Repo uses app/, not src/.
Follow SDD.
No code before spec.
Do not implement DB, Google Sheets, Calendar, Telegram, n8n, or therapy-session tracking yet.

Start by creating:

docs/P6-F.9.8_APPOINTMENT_REQUEST_SERVICE_CONTRACT.md

The service contract must define how the backend will orchestrate AppointmentRequest creation and lifecycle updates while preserving same-request continuity for contraoffers and rescheduling.
