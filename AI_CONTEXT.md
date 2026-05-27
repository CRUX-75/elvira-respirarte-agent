# AI_CONTEXT.md — Elvira Respirarte Agent

## Purpose

This file is the operational context for AI-assisted development on the Elvira / Respirarte project.

It exists so ChatGPT or any coding assistant can understand the repository structure, architecture decisions, documentation hierarchy, current branch, and current phase without rediscovering the repo from scratch.

This file is not public-facing documentation. It is a working context file.

---

## Repository

Project:

elvira-respirarte-agent

Repository:

github.com/CRUX-75/elvira-respirarte-agent

Current working branch:

p6-f-9-10-appointment-request-service-tests

Current status:

P6-F.9.12 — AppointmentRequest Persistence Preparation is CLOSED / GREEN / MERGE-READY.

Latest validation baseline:

149 passed

Working tree:

clean

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

Do not create a src/ folder.

This repository uses app/.

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
- Google Sheets only as human-visible operational inbox when needed
- n8n only as auxiliary workflow layer when needed

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
→ AppointmentRequestService
→ AppointmentRequestRepository
→ PostgreSQL source of truth
→ future Google Sheets adapter / human inbox
→ future Telegram notification, optional

Google Sheets is only the visible operational inbox for the doctor.

The source of truth for appointment request rules must remain in Python/PostgreSQL.

---

## Current Milestone

Closed block:

P6-F.9.12 — AppointmentRequest Persistence Preparation

Status:

CLOSED / GREEN / MERGE-READY

Validation:

149 passed

Important boundaries:

- Production SQL has NOT been executed yet.
- Runtime integration has NOT been connected yet.
- Google Sheets has NOT been touched yet.
- Telegram has NOT been touched yet.
- n8n has NOT been touched yet.
- WhatsApp sending has NOT been touched yet.
- No Swagger endpoint has been created for appointment requests yet.

---

## Latest Relevant Commits

Recent commits on branch:

- cb0dd92 Update context for appointment request persistence milestone
- 6e7d8ab Add appointment requests PostgreSQL migration draft
- 512fa86 Add appointment request PostgreSQL repository
- 9e2dce3 Document appointment request PostgreSQL table contract
- 1950340 Update AI context for appointment request repository contract

---

## Closed Appointment Request Phases

The following AppointmentRequest phases are closed:

- P6-F.9.2 — AppointmentRequest internal model spec
- P6-F.9.3 — AppointmentRequest model
- P6-F.9.4 — lifecycle validation spec
- P6-F.9.5 — lifecycle validator
- P6-F.9.6 — factory spec
- P6-F.9.7 — factory implementation and progress handoff
- P6-F.9.8 — AppointmentRequestService contract
- P6-F.9.9 — AppointmentRequestService test plan
- P6-F.9.10 — AppointmentRequestService tests
- P6-F.9.11 — AppointmentRequestService implementation
- P6-F.9.12 — AppointmentRequest persistence preparation

---

## AppointmentRequestService Status

Status:

Implemented and tested.

Main file:

app/services/appointment_request_service.py

The service supports:

- creating a new appointment request
- reusing an existing active request
- preventing duplicate active requests
- applying contraoffer logic while preserving id_solicitud
- applying reschedule logic while preserving id_solicitud
- validating basic lifecycle transitions
- raising deterministic errors for invalid transitions
- raising deterministic errors for unknown request IDs

Important invariant:

id_solicitud must be preserved during:

- contraoffers
- rescheduling
- lifecycle transitions

Contraoffers and rescheduling update the same operational request.

They must not create a new request.

---

## AppointmentRequestFactory Status

Main file:

app/services/appointment_request_factory.py

Important decision:

AppointmentRequestFactory exists as a class wrapper, but it must not duplicate AppointmentRequest construction logic.

The wrapper delegates to the function-based factory:

create_appointment_request()

This keeps the factory DRY and avoids creating a second source of truth for AppointmentRequest defaults.

---

## AppointmentRequest Lifecycle Contract

Valid states:

- nueva
- pendiente_datos
- pendiente_confirmacion
- confirmada
- reagendada
- cancelada
- cerrada

Active states:

- nueva
- pendiente_datos
- pendiente_confirmacion
- confirmada
- reagendada

Terminal states:

- cancelada
- cerrada

Invalid/non-existing states that must not be used:

- pendiente
- contraoferta
- completada

Important clarification:

AppointmentRequestStatus is not an Enum with members such as .PENDIENTE.

It is treated according to the model's real Literal/string contract.

Contraoffer representation:

There is no separate contraoferta state in the model.

A contraoffer is represented operationally as:

pendiente_confirmacion

Meaning:

The request is waiting for patient acceptance, doctor review, or confirmation after a proposed change.

---

## AppointmentRequestRepository Protocol

Main file:

app/repositories/appointment_request_repository.py

This file defines:

- ACTIVE_APPOINTMENT_REQUEST_STATES
- TERMINAL_APPOINTMENT_REQUEST_STATES
- AppointmentRequestRepository Protocol

Repository contract methods:

- save(request)
- update(request)
- get_by_id(id_solicitud)
- find_active_by_telefono(telefono)

Repository responsibility:

The repository owns persistence and retrieval only.

The repository must not own:

- appointment lifecycle decisions
- create vs reuse active request logic
- contraoffer handling
- reschedule handling
- doctor confirmation
- WhatsApp sending
- Google Sheets formatting
- Telegram notification
- Calendar logic
- n8n workflow logic

---

## Repository Contract Tests

Main file:

tests/test_appointment_request_repository_contract.py

The repository contract is validated with an in-memory test adapter.

Covered behaviors:

- save request
- get request by id_solicitud
- return None for unknown ID
- update without duplication
- reject update for unknown request
- find active request by phone
- ignore terminal requests
- return latest active request when multiple active records exist

Terminal requests must not block creation of a new request for the same patient.

---

## PostgreSQL Table Contract

Main document:

docs/P6-F.9.12_POSTGRESQL_TABLE_CONTRACT_SPEC.md

Future production table:

appointment_requests

Primary key:

id_solicitud TEXT PRIMARY KEY

Main columns:

- id_solicitud
- telefono
- nombre_paciente
- estado_solicitud
- intent_origen
- canal_origen
- fecha_solicitada
- franja_solicitada
- hora_solicitada_texto
- fecha_aceptada
- franja_aceptada
- fecha_confirmada
- franja_confirmada
- servicio_solicitado
- direccion_domicilio
- observaciones
- motivo_reagendamiento
- motivo_cancelacion
- source_interaction_id
- created_by
- updated_by
- created_at
- updated_at

Valid estado_solicitud values:

- nueva
- pendiente_datos
- pendiente_confirmacion
- confirmada
- reagendada
- cancelada
- cerrada

Valid canal_origen values:

- whatsapp
- manual
- system

Deterministic active lookup ordering:

1. updated_at DESC
2. created_at DESC
3. id_solicitud DESC

---

## PostgreSQL Repository Implementation

Main file:

app/repositories/postgres_appointment_request_repository.py

Class:

PostgresAppointmentRequestRepository

Implemented methods:

- save(request)
- update(request)
- get_by_id(id_solicitud)
- find_active_by_telefono(telefono)

Implementation style:

- SQLAlchemy raw SQL
- sqlalchemy.text
- injected SQLAlchemy Engine
- no global production engine import inside repository
- row._mapping to dict
- AppointmentRequest(**data)
- timestamps normalized to strings for the lightweight Pydantic model

Important design decision:

The repository accepts an injected SQLAlchemy Engine:

def __init__(self, engine: Engine):
    self.engine = engine

This avoids accidental coupling to production DB and keeps the repository testable.

The active-state lookup uses:

bindparam("active_states", expanding=True)

This is required so SQLAlchemy expands the IN clause correctly across test and production-compatible engines.

---

## PostgreSQL Repository Tests

Main file:

tests/test_postgres_appointment_request_repository.py

Current test strategy:

The tests use a local SQLite in-memory engine to validate SQL behavior safely without touching production.

This is intentional for the current repository implementation test layer.

Covered behaviors:

- save inserts a row
- duplicate id_solicitud fails
- get_by_id returns AppointmentRequest
- get_by_id returns None for unknown ID
- update modifies existing row without duplicating
- update unknown fails deterministically
- find_active_by_telefono ignores terminal requests
- find_active_by_telefono returns latest active request using deterministic ordering
- find_active_by_telefono returns None when no request exists

---

## SQL Migration Draft

Main file:

scripts/sql/001_create_appointment_requests.sql

Status:

Versioned and committed.

Purpose:

This SQL draft defines the future production PostgreSQL table for AppointmentRequest persistence.

Table:

appointment_requests

Includes:

- CREATE TABLE IF NOT EXISTS appointment_requests
- CHECK constraint for estado_solicitud
- CHECK constraint for canal_origen
- TIMESTAMPTZ for created_at / updated_at
- idx_appointment_requests_telefono
- idx_appointment_requests_active_lookup

Important operational rule:

This SQL file is reviewable and versioned, but it must not be executed automatically by the application.

Production execution remains a separate controlled step.

---

## Current Merge Plan

Recommended next action:

Merge current branch into main.

Commands:

git checkout main
git pull origin main
git merge p6-f-9-10-appointment-request-service-tests
pytest -q
git status --short
git push origin main

Expected result:

149 passed

Working tree clean.

---

## Next Recommended Block After Merge

Next block:

P6-F.9.13 — Controlled Production DB Migration Plan

Objective:

Prepare a controlled plan for applying the appointment_requests table migration to the real production PostgreSQL database.

Do not execute production SQL directly without a checklist.

The next block should include:

- review SQL migration
- confirm production DB access method
- define pre-check queries
- define migration execution step
- define post-check queries
- define rollback/containment decision
- confirm no runtime integration yet
- confirm no WhatsApp sending changes
- confirm no Google Sheets changes
- confirm no Telegram/n8n changes

---

## Explicitly Out of Scope Until Later

Do not start these before P6-F.9.13 is planned and closed:

- Runtime integration of AppointmentRequestService
- Production SQL execution without checklist
- Google Sheets adapter
- Telegram notification
- n8n workflow
- WhatsApp sending changes
- Swagger endpoint
- LangSmith appointment request validation
- Calendar integration
- therapy session package tracking
- remaining sessions tracking
- executed sessions tracking
- automatic appointment confirmation

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

---

## Working Rules

Work step by step.

Do not dump huge files unnecessarily unless replacing a context/spec file intentionally.

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

## Current Source of Truth

Current true project status:

- P6-F.9.12 closed
- Repository protocol implemented
- In-memory repository contract tests implemented
- PostgreSQL table contract spec documented
- PostgreSQL repository v1 implemented
- SQL migration draft versioned
- Full test suite green
- 149 passed
- Branch merge-ready
- Working tree clean


---

## P6-F.9.13 — Controlled Production DB Migration

Status:

PARTIALLY CLOSED / PRODUCTION TABLE CREATED / POST-CHECKS GREEN

Completed microblocks:

- P6-F.9.13.1 — Production DB Migration Plan SPEC
- P6-F.9.13.2 — SQL Migration Draft Review
- P6-F.9.13.3 — Production DB Access Method Confirmation
- P6-F.9.13.4 — Production Pre-Check Queries
- P6-F.9.13.5 — Production Migration Post-Checks

Execution method:

pgweb via EasyPanel browser UI.

Production database:

elvira_respirarte_prod

Migration executed:

scripts/sql/001_create_appointment_requests.sql

Production result:

The `appointment_requests` table now exists in production.

Verified production columns:

- id_solicitud
- telefono
- nombre_paciente
- estado_solicitud
- intent_origen
- canal_origen
- fecha_solicitada
- franja_solicitada
- hora_solicitada_texto
- fecha_aceptada
- franja_aceptada
- fecha_confirmada
- franja_confirmada
- servicio_solicitado
- direccion_domicilio
- observaciones
- motivo_reagendamiento
- motivo_cancelacion
- source_interaction_id
- created_by
- updated_by
- created_at
- updated_at

Verified production constraints:

- appointment_requests_canal_origen_check
- appointment_requests_estado_solicitud_check
- appointment_requests_pkey

Verified production indexes:

- appointment_requests_pkey
- idx_appointment_requests_active_lookup
- idx_appointment_requests_telefono

Important boundary:

The production migration only created the new table and indexes.

Still NOT done:

- runtime integration
- AppointmentRequestService connection to WhatsApp flow
- Google Sheets adapter
- Telegram notification
- n8n workflow changes
- WhatsApp sending changes
- Swagger endpoint
- LangSmith appointment request validation

Current production behavior remains unchanged.

Next recommended microblock:

P6-F.9.13.6 — Application Health / Ready Safety Check

Objective:

Confirm that after the production DB migration, the deployed application is still healthy and no runtime behavior changed.

Recommended checks:

- open `/health`
- open `/ready`
- confirm no runtime errors in EasyPanel logs
- confirm WhatsApp sending flag remains unchanged
- confirm app behavior remains unchanged


---

## P6-F.9.13.6 — Application Health / Ready Safety Check

Status:

CLOSED / GREEN

Production readiness check after creating `appointment_requests` table passed.

Production `/ready` result confirmed:

- status: ready
- environment: production
- app_version: 0.2.1
- whatsapp_sending_enabled: false
- kb_runtime_enabled: true
- database configured: true
- repositories configured: patients, interactions, processed_messages, kb
- LangSmith tracing enabled: true
- LangSmith project: elvira-respirarte-prod
- OpenAI configured: true
- WhatsApp configured: true
- hard_failures: []
- real_whatsapp_sending_allowed: false

Conclusion:

The production application remained healthy after the DB migration.

The new `appointment_requests` production table exists, but runtime integration is still not connected.

Current production behavior remains unchanged.

