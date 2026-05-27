# AI_CONTEXT.md — Elvira Respirarte Agent

## Purpose

This file is the operational context for AI-assisted development on the Elvira / Respirarte project.

It exists so ChatGPT or any coding assistant can understand the repository structure, architecture decisions, documentation hierarchy, current branch, and current phase without rediscovering the repo from scratch.

This file is not public-facing documentation. It is a working context file.

---

## Repository Structure

The repository uses:

- app/
- docs/
- tests/
- scripts/
- data/
- requirements.txt
- Dockerfile
- README.md

Do not create a src/ folder. This repository uses app/.

---

## Main Stack

- Python 3.12+
- FastAPI
- LangGraph
- Pydantic
- SQLAlchemy with raw SQL repositories
- PostgreSQL
- OpenAI for response wording only
- LangSmith for tracing
- WhatsApp Cloud API
- Google Sheets only as human-visible operational surface when needed

---

## Architecture Principles

The system follows this rule:

El canal transporta.
El workflow controla.
La KB informa.
El modelo redacta.
La state machine protege.
El log permite auditar.

Critical business logic must live in FastAPI/Python, not in n8n.

n8n may be used only for auxiliary workflows such as notifications, but not for:

- appointment request state
- scheduling handoff logic
- deterministic validation
- patient state transitions
- persistence rules
- appointment request lifecycle

---

## Appointment Request Architecture Decision

Solicitudes_Cita must not be treated as a Google Sheets-first object.

Correct direction:

AppointmentRequest internal model
→ service layer
→ future repository layer
→ future Google Sheets adapter / human inbox
→ future Telegram notification, optional

Google Sheets is only the visible operational inbox for the doctor.

The source of truth for appointment request rules must remain in Python.

---

## Closed Appointment Request Phases

The following phases are closed and committed to main:

- P6-F.9.2 — AppointmentRequest internal model spec
- P6-F.9.3 — AppointmentRequest model
- P6-F.9.4 — lifecycle validation spec
- P6-F.9.5 — lifecycle validator
- P6-F.9.6 — factory spec
- P6-F.9.7 — factory implementation and progress handoff
- P6-F.9.8 — AppointmentRequestService contract
- P6-F.9.9 — AppointmentRequestService test plan

Last known clean main validation baseline:

120 passed

---

## Current RED Branch

Current branch:

p6-f-9-10-appointment-request-service-tests

This branch contains:

- tests/test_appointment_request_service.py
- docs/P6-F.9.10_APPOINTMENT_REQUEST_SERVICE_TESTS_RED_HANDOFF.md

Expected RED result when running only the new service tests:

ModuleNotFoundError: No module named 'app.services.appointment_request_service'

This RED is intentional because the service implementation does not exist yet.

Do not merge this branch to main while tests are red.

---

## Current Phase for Next Chat

Active phase:

P6-F.9.11 — AppointmentRequestService Implementation

Objective:

Create the minimal deterministic service implementation required to make:

tests/test_appointment_request_service.py

pass.

Expected file to create:

app/services/appointment_request_service.py

The implementation must satisfy:

- docs/P6-F.9.8_APPOINTMENT_REQUEST_SERVICE_CONTRACT.md
- docs/P6-F.9.9_APPOINTMENT_REQUEST_SERVICE_TEST_PLAN.md
- tests/test_appointment_request_service.py

---

## P6-F.9.11 Scope

In scope:

- create AppointmentRequestService
- create deterministic service-level errors
- support create_or_reuse_active_request
- support transition_request
- support apply_contraoffer
- support apply_reschedule
- support active request reuse
- preserve id_solicitud
- keep repository dependency injectable
- keep logic deterministic in Python

Out of scope:

- PostgreSQL implementation
- SQLAlchemy repository
- Google Sheets integration
- Calendar integration
- Telegram notifications
- n8n workflows
- WhatsApp sending changes
- Swagger endpoint
- LangSmith validation
- therapy session package tracking
- remaining sessions tracking
- executed sessions tracking
- automatic appointment confirmation

---

## Next Startup Commands

Start next chat from this branch:

git checkout p6-f-9-10-appointment-request-service-tests

Run the RED test:

pytest tests/test_appointment_request_service.py

Expected initial result:

ModuleNotFoundError: No module named 'app.services.appointment_request_service'

Then implement:

app/services/appointment_request_service.py

After implementation, validate:

pytest tests/test_appointment_request_service.py
pytest

Target:

all tests passing

---

## Development Protocol

This project follows SDD: Specification-Driven Development.

No vibecoding.

For non-trivial changes, follow this order:

1. SPEC
2. DESIGN
3. CONTRACT
4. TESTS
5. IMPLEMENTATION
6. VALIDATION
7. DOCS UPDATE

For P6-F.9.11, SPEC, CONTRACT and TESTS already exist.

The next allowed step is:

IMPLEMENTATION

Do not create new specs before implementing the service unless a real gap is discovered.

---

## Working Rules

Work step by step.

Do not dump huge files unnecessarily.

Prefer copy-paste friendly Bash commands.

Prefer cat and sed for file creation and modification.

Avoid repeating large code blocks already created in the session.

Follow DRY principles.

Keep code clean, robust, typed, and testable.

Before adding new files, verify whether the target folder already exists.

For this repo, use app/, never src/.

---

## Environment Note

If pytest fails with:

ModuleNotFoundError: No module named 'fastapi'

this is an environment or dependency issue, not necessarily a code regression.

Check:

echo $VIRTUAL_ENV
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest

---

## P6-F.9.11 — AppointmentRequestService Implementation Closed

Status: closed.

Validation result:

```text
133 passed

Branch used:

p6-f-9-10-appointment-request-service-tests

Implemented / modified files:

app/services/appointment_request_factory.py
app/services/appointment_request_service.py
tests/test_appointment_request_service.py
Key implementation decision

AppointmentRequestFactory was added as a class wrapper, but it must not duplicate AppointmentRequest construction logic.

The wrapper delegates to the existing function-based factory:

create_appointment_request()

This keeps the factory DRY and avoids creating a second source of truth for AppointmentRequest defaults.

Real AppointmentRequest lifecycle contract

The service and tests were aligned with the real AppointmentRequest model contract.

Valid states are:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada

Invalid/non-existing states that must not be used:

pendiente
contraoferta
completada

Important clarification:

AppointmentRequestStatus is not an Enum with members such as .PENDIENTE.

It is treated according to the model's real Literal/string contract.

Contraoffer representation

There is no separate contraoferta state in the model.

A contraoffer is represented operationally as:

pendiente_confirmacion

Meaning:

The request is waiting for patient acceptance, doctor review, or confirmation after a proposed change.

AppointmentRequestService responsibilities implemented

The minimal service now supports:

creating a new appointment request
reusing an existing active request
preventing duplicate active requests
applying contraoffer logic while preserving id_solicitud
applying reschedule logic while preserving id_solicitud
validating basic lifecycle transitions
raising deterministic errors for invalid transitions
raising deterministic errors for unknown request IDs
Important invariant

id_solicitud must be preserved during:

contraoffers
rescheduling
lifecycle transitions

Contraoffers and rescheduling update the same operational request. They must not create a new request.

Explicitly out of scope for P6-F.9.11

No implementation was added for:

PostgreSQL repository
Google Sheets integration
Calendar integration
Telegram notification
n8n workflow
WhatsApp sending changes
automatic appointment confirmation
therapy/session package tracking
Architecture boundary confirmed

Appointment request lifecycle remains owned by FastAPI/Python.

Google Sheets may later become a human-visible operational inbox, but it must not own appointment state or validation rules.

n8n may later send auxiliary notifications, but it must not own core appointment request logic.

Next recommended block

P6-F.9.12 — AppointmentRequestRepository Contract / Persistence Preparation

Recommended next objective:

Define the repository contract before implementing real persistence.

The next block should clarify:

repository interface
required persistence operations
active request lookup
update semantics
PostgreSQL table shape
fake/in-memory repository tests first


---

## P6-F.9.12 — AppointmentRequestRepository Contract Progress

Status: partially closed.

Closed microblocks:

- P6-F.9.12.1 — Repository Contract SPEC
- P6-F.9.12.2 — Repository Protocol + In-Memory Contract Tests
- P6-F.9.12.3 — Repository Protocol Extraction
- P6-F.9.12.4 — Service wired to Repository Protocol

Current validation result:

```text
140 passed
Repository contract location

The official repository contract now lives at:

app/repositories/appointment_request_repository.py

This file defines:

ACTIVE_APPOINTMENT_REQUEST_STATES
TERMINAL_APPOINTMENT_REQUEST_STATES
AppointmentRequestRepository Protocol

Official repository layer location:

app/repositories/

Do not create a src/ folder.

AppointmentRequest active states

Active states for repository lookup:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada

These states still belong to the active operational appointment request flow.

AppointmentRequest terminal states

Terminal states:

cancelada
cerrada

These states must not block creation of a new appointment request for the same patient.

Repository contract methods

The repository contract currently requires:

save(request)
update(request)
get_by_id(id_solicitud)
find_active_by_telefono(telefono)
Service wiring decision

AppointmentRequestService now depends on the official repository Protocol from:

from app.repositories.appointment_request_repository import AppointmentRequestRepository

The service must not define a duplicated internal repository Protocol.

Boundary confirmed

The repository owns persistence and retrieval only.

The service owns orchestration decisions such as:

create vs reuse active request
lifecycle transitions
contraoffer handling
reschedule handling
invalid transition errors
not-found errors

The repository must not own business logic, WhatsApp sending, Telegram notification, Google Sheets formatting, appointment availability, or doctor confirmation.

Test coverage added

Repository contract behavior is currently validated with an in-memory test adapter in:

tests/test_appointment_request_repository_contract.py

Covered behaviors:

save request
get request by id_solicitud
return None for unknown ID
update without duplication
reject update for unknown request
find active request by phone
ignore terminal requests
return latest active request when multiple active records exist
Next recommended block

P6-F.9.12.6 — Repository PostgreSQL Table Contract SPEC

Objective:

Define the future PostgreSQL table shape before writing SQL or repository implementation.

No PostgreSQL implementation yet.

The next block should specify:

table name
required columns
nullable vs required fields
primary key
indexes
active lookup ordering
timestamp semantics
mapping from AppointmentRequest model to DB row
mapping from DB row back to AppointmentRequest


---

## P6-F.9.12.7 — PostgreSQL Repository Tests RED Closed

Status: closed.

Validation path:

```text
tests/test_postgres_appointment_request_repository.py

Initial RED was confirmed correctly in stages:

Missing repository implementation module:
ModuleNotFoundError: No module named 'app.repositories.postgres_appointment_request_repository'
After creating the skeleton implementation, tests reached the repository layer and failed with:
NotImplementedError

This confirmed that the test file was wired correctly and no production database connection was being touched.

P6-F.9.12.8 — PostgreSQL Repository Implementation v1 Closed

Status: closed / green.

Validation result:

149 passed

Files added:

app/repositories/postgres_appointment_request_repository.py
tests/test_postgres_appointment_request_repository.py

Implemented repository:

PostgresAppointmentRequestRepository

Repository methods implemented:

save(request)
update(request)
get_by_id(id_solicitud)
find_active_by_telefono(telefono)

Implementation style:

SQLAlchemy raw SQL
sqlalchemy.text
injectable Engine
no global production engine import inside the repository
AppointmentRequest model mapping via row._mapping
timestamps normalized back to strings for the lightweight Pydantic model

Important design decision:

The repository accepts an injected SQLAlchemy Engine:

def __init__(self, engine: Engine):
    self.engine = engine

This avoids accidental coupling to the production database and keeps the repository testable.

The existing project pattern uses SQLAlchemy raw SQL repositories. This implementation follows that style while improving testability through dependency injection.

Test setup:

The PostgreSQL repository tests currently use a local SQLite in-memory engine to validate SQL behavior safely without touching production.

This is intentional for the current repository implementation test layer.

The real production table contract remains PostgreSQL-first and is documented in:

docs/P6-F.9.12_POSTGRESQL_TABLE_CONTRACT_SPEC.md

Covered behaviors:

save inserts a row
duplicate id_solicitud fails
get_by_id returns AppointmentRequest
get_by_id returns None for unknown ID
update modifies existing row without duplicating
update unknown fails deterministically
find_active_by_telefono ignores terminal requests
find_active_by_telefono returns latest active request using deterministic ordering
find_active_by_telefono returns None when no request exists

Active request ordering remains:

updated_at DESC
created_at DESC
id_solicitud DESC

Active states:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada

Terminal states:

cancelada
cerrada

SQLAlchemy detail:

The active-state lookup uses:

bindparam("active_states", expanding=True)

This is required so SQLAlchemy expands the IN clause correctly across test and production-compatible engines.

Boundary confirmed:

The repository only persists and retrieves AppointmentRequest records.

It does not own:

appointment lifecycle decisions
create vs reuse active request logic
contraoffer handling
reschedule handling
doctor confirmation
WhatsApp sending
Google Sheets formatting
Telegram notification
Calendar logic
n8n workflow logic

Those responsibilities remain outside the repository.

Next recommended block:

P6-F.9.12.9 — Commit PostgreSQL Repository v1

Before continuing with Google Sheets, Telegram, Swagger, LangSmith or production database migration, commit this green repository milestone.

