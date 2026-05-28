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


---

## P6-F.9.14 — Runtime Integration Preparation

Status:

PARTIALLY CLOSED / READY FOR STATEFUL TEST ENDPOINT WIRING TESTS

Recently closed blocks:

- P6-F.9.14.1 — Runtime Integration SPEC
- P6-F.9.14.2 — Runtime Integration Design
- P6-F.9.14.3 — Runtime Flow Inspection
- P6-F.9.14.4 — Appointment Persistence Decision Function SPEC
- P6-F.9.14.5 — Decision Function Tests
- P6-F.9.14.6 — Decision Function Implementation
- P6-F.9.14.7 — Repository/Service Runtime Wiring Design

Latest validation:

165 passed

Current working tree at closure:

clean

---

## Runtime Flow Inspection Findings

Main runtime file:

app/main.py

Relevant endpoints:

- POST /webhook
- POST /test/message
- POST /test/message-stateful

Important finding:

`/test/message-stateful` is the safest first validation surface for AppointmentRequest runtime integration.

Reason:

- It reads patient state from PostgreSQL.
- It processes the message through the real LangGraph flow.
- It persists interactions.
- It updates patient state.
- It never sends real WhatsApp messages.
- It generates a synthetic `whatsapp_message_id`.

Real `/webhook` integration is explicitly deferred.

---

## Interaction Linkage Decision

`save_interaction()` currently inserts into `interactions` but returns `None`.

Therefore, the first AppointmentRequest runtime integration will use:

source_interaction_id = whatsapp_message_id

For `/test/message-stateful`, this means:

source_interaction_id = synthetic test-stateful whatsapp_message_id

A later improvement may modify interaction persistence to return a real interaction row ID, but that is out of scope for the first runtime wiring.

---

## Appointment Request Runtime Decision Function

New file:

app/services/appointment_request_runtime.py

New pure decision function:

decide_appointment_request_persistence(...)

New decision object:

AppointmentPersistenceDecision

Test file:

tests/test_appointment_request_runtime_decision.py

Important properties:

- pure
- deterministic
- no DB access
- no network access
- no LLM call
- no FastAPI dependency
- unit tested

---

## Decision Function Rules

The decision function skips persistence for:

- general
- servicios
- horarios
- pago
- reglas
- urgencia
- optout
- cita
- fecha_cita

The first allowed persistence case is intentionally narrow.

It allows persistence only when:

- intent == "hora_cita"
- nuevo_estado == "ST_CITA_PENDIENTE"
- next_action == "confirm_appointment_request"
- fecha_solicitada is present
- date is not weekend
- date is not a Colombia holiday
- es_dia_disponible is not False
- a time preference exists through slots_candidatos or raw message text

When persistence is allowed:

estado_solicitud = "pendiente_confirmacion"

The function never returns:

estado_solicitud = "confirmada"

Doctor/human confirmation remains a future flow.

---

## Repository/Service Runtime Wiring Design

Design document:

docs/P6-F.9.14.7_REPOSITORY_SERVICE_RUNTIME_WIRING_DESIGN.md

First wiring target:

POST /test/message-stateful

Do not wire real WhatsApp webhook yet.

Runtime should later use:

- PostgresAppointmentRequestRepository(engine)
- AppointmentRequestService(repository=...)
- decide_appointment_request_persistence(...)

The response from `/test/message-stateful` should later include:

appointment_request_decision

and, when persistence succeeds:

appointment_request metadata

Candidate metadata:

- id_solicitud
- estado_solicitud
- source_interaction_id

---

## Safety Boundaries Still Active

Do not touch yet:

- real POST /webhook integration
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- doctor confirmation flow
- calendar integration
- therapy package/session tracking

WHATSAPP_SENDING_ENABLED must remain false unless a later controlled sending block explicitly changes it.

---

## Next Exact Block

P6-F.9.14.8 — Stateful Test Endpoint Wiring Tests

Goal:

Write failing tests first for appointment request wiring in `/test/message-stateful`.

Before implementation:

1. Inspect AppointmentRequestService method signatures.
2. Inspect existing FastAPI TestClient patterns.
3. Write failing endpoint tests.
4. Only then implement minimal wiring.

Expected test goals:

- `/test/message-stateful` returns appointment_request_decision for skipped messages.
- General/cita/fecha_cita messages skip persistence.
- hora_cita ready state creates or reuses AppointmentRequest.
- Response includes appointment_request metadata when persisted.
- Synthetic whatsapp_message_id is used as source_interaction_id.
- Patient state still updates correctly when persistence succeeds.
- No real WhatsApp sending is touched.


---

## P6-F.9.14.8 — Stateful Test Endpoint Wiring Tests

Status:

CLOSED / RED-THEN-GREEN / GREEN

Validation:

170 passed after later routing fix.

New test file:

tests/test_stateful_appointment_request_wiring.py

Covered behaviors:

- `/test/message-stateful` returns `appointment_request_decision`
- general messages skip AppointmentRequest persistence
- initial `cita` messages skip AppointmentRequest persistence
- `fecha_cita` messages skip AppointmentRequest persistence
- ready `hora_cita` messages can persist or reuse AppointmentRequest
- response includes `appointment_request` metadata when persistence succeeds
- synthetic `test-stateful-{uuid4()}` WhatsApp message ID is used as `source_interaction_id`
- patient state still updates correctly
- real WhatsApp sending is not touched

---

## P6-F.9.14.9 — Minimal Stateful Runtime Wiring

Status:

CLOSED / GREEN

Changed files:

- app/main.py
- app/services/appointment_request_service.py

The first AppointmentRequest runtime wiring now exists only in:

POST /test/message-stateful

The real WhatsApp webhook remains out of scope.

Runtime behavior:

- generates synthetic `whatsapp_message_id = test-stateful-{uuid4()}`
- calls `decide_appointment_request_persistence(...)`
- always returns `appointment_request_decision`
- returns `appointment_request = null` when skipped
- when persistence is allowed, uses:
  - `PostgresAppointmentRequestRepository(engine)`
  - `AppointmentRequestService(repository=...)`
- returns AppointmentRequest metadata:
  - id_solicitud
  - estado_solicitud
  - source_interaction_id
  - fecha_solicitada
  - franja_solicitada

Important:

`source_interaction_id` currently uses the synthetic WhatsApp message ID because `save_interaction()` still inserts interactions but does not return a real interaction row ID.

---

## P6-F.9.14.10 — Stateful Runtime Wiring Closure

Status:

CLOSED / COMMITTED / CLEAN

Documentation:

docs/P6-F.9.14.10_STATEFUL_RUNTIME_WIRING_CLOSURE.md

Documented that:

- first runtime wiring is limited to `/test/message-stateful`
- `/webhook` real remains untouched
- WhatsApp real sending remains untouched
- Google Sheets, Telegram, n8n, doctor confirmation, calendar, and therapy/session tracking remain out of scope

---

## P6-F.9.14.11 — Stateful Runtime Dry-Run Validation Plan

Status:

DOCUMENT CREATED

Documentation:

docs/P6-F.9.14.11_STATEFUL_RUNTIME_DRY_RUN_VALIDATION_PLAN.md

Important note:

Verify whether this file has been committed. It appeared as untracked during cleanup.

Validation target:

POST /test/message-stateful

Dry-run sequence:

1. Hola buenos días
2. Quiero pedir una cita
3. El viernes
4. En la tarde

---

## P6-F.9.14.12 — Time Window Intent Routing Fix

Status:

CLOSED / RED-THEN-GREEN / GREEN

Changed files:

- app/services/intent.py
- tests/test_intent.py

Bug found in production dry-run:

When the patient was already in:

ST_CITA_FRANJA

and answered:

En la tarde

the system incorrectly classified the message as:

fecha_cita

instead of:

hora_cita

Root cause:

In `ST_CITA_FRANJA`, generic time-window phrases like `en la tarde` were not included in the slot selection patterns. They later matched the date patterns and returned `fecha_cita`.

Fix:

In `ST_CITA_FRANJA`, these phrases are now treated as `hora_cita`:

- en la tarde
- por la tarde
- tarde
- en la mañana
- por la mañana
- mañana
- en la noche
- por la noche
- noche

Validation:

170 passed

Production Swagger dry-run confirmed the routing fix:

Input:

En la tarde

Result:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request

---

## New Runtime Bug Found — Appointment Context Lost Between Turns

Status:

OPEN / NEXT ARCHITECTURAL FIX NEEDED

Production Swagger dry-run result after P6-F.9.14.12:

The routing bug is fixed, but AppointmentRequest persistence still does not happen.

Final turn:

Input:

En la tarde

Runtime result:

- estado_anterior = ST_CITA_FRANJA
- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = skipped_missing_fecha_solicitada
- appointment_request = null

Diagnosis:

The appointment date context from the previous turn is lost.

Previous turn:

Input:

El viernes

Resolved:

- fecha_solicitada = 2026-05-29
- fecha_solicitada_texto = viernes 29 de mayo
- slots_candidatos:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- nuevo_estado = ST_CITA_FRANJA

Next turn:

Input:

En la tarde

The system has only:

- estado_actual = ST_CITA_FRANJA

but no persisted:

- fecha_solicitada
- fecha_solicitada_texto
- slots_candidatos
- availability flags

Therefore the decision function correctly blocks persistence with:

skipped_missing_fecha_solicitada

This is not a decision function bug.

The decision function is protecting correctly.

---

## Appointment Context Carryover Decision

Decision:

Persist active appointment context in `patients`.

Recommended new column:

appointment_context JSONB

Reason:

`patients` already stores the current conversational state through `estado_actual`.

The appointment context is operational state needed to continue the current appointment flow.

Do not store this first in `interactions` for runtime carryover, because `interactions` is audit/history and currently does not hold stateful appointment context.

Expected JSON shape:

```json
{
  "fecha_solicitada": "2026-05-29",
  "fecha_solicitada_texto": "viernes 29 de mayo",
  "slots_candidatos": [
    "3:00 p. m.–5:00 p. m.",
    "5:00 p. m.–7:00 p. m."
  ],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null
}

Capture rule:

Store appointment context when:

result.intent == "fecha_cita"
result.nuevo_estado == "ST_CITA_FRANJA"
result.fecha_solicitada is present

Carryover rule:

Apply stored appointment context when:

result.intent == "hora_cita"
result.nuevo_estado == "ST_CITA_PENDIENTE"
result.fecha_solicitada is missing
patient.appointment_context has a stored fecha_solicitada

Fields to restore before calling decide_appointment_request_persistence(...):

fecha_solicitada
fecha_solicitada_texto
slots_candidatos
es_dia_disponible
is_weekend
is_colombia_holiday
colombia_holiday_name

Clear rule minimum:

Clear appointment context when:

AppointmentRequest persistence succeeds
opt_out becomes true

Still out of scope:

POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
doctor confirmation
calendar integration
therapy/session package tracking
Next Exact Block

P6-F.9.14.13 — Appointment Context Carryover SPEC

Objective:

Create and commit:

docs/P6-F.9.14.13_APPOINTMENT_CONTEXT_CARRYOVER_SPEC.md

Then proceed with:

P6-F.9.14.14 — Appointment Context Pure Helpers + Tests

Planned files:

app/services/appointment_context.py
tests/test_appointment_context.py

Planned pure helpers:

capture_appointment_context_from_state(state)
apply_appointment_context_to_state(state, context)
should_clear_appointment_context(state, persisted: bool)

Then:

P6-F.9.14.15 — Patient Repository Appointment Context Methods

Expected work:

add appointment_context JSONB to schema/migration draft
add patient repository methods:
update_patient_appointment_context(...)
clear_patient_appointment_context(...)

Then:

P6-F.9.14.16 — Stateful Endpoint Carryover Wiring

Expected work in /test/message-stateful only:

apply context carryover before decide_appointment_request_persistence(...)
capture context after fecha_cita / ST_CITA_FRANJA
clear context if AppointmentRequest persisted successfully
clear context if opt_out true

Critical boundary:

Do not touch real POST /webhook yet.
Do not touch WhatsApp sending.
Do not touch Google Sheets.
Do not touch Telegram.
Do not touch n8n.

Follow SDD:

SPEC → tests RED → implementation mínima → pytest → docs → commit.


---

## P6-F.9.14.13 — Appointment Context Carryover SPEC

Status:

CLOSED / SPEC / COMMITTED

Documentation:

docs/P6-F.9.14.13_APPOINTMENT_CONTEXT_CARRYOVER_SPEC.md

Problem solved at specification level:

The appointment date context was lost between turns.

Observed dry-run flow:

1. Patient says: `El viernes`
2. Runtime resolves:
   - `fecha_solicitada = 2026-05-29`
   - `fecha_solicitada_texto = viernes 29 de mayo`
   - `slots_candidatos`
   - availability flags
3. Patient state moves to `ST_CITA_FRANJA`
4. Patient says: `En la tarde`
5. Runtime routes correctly:
   - `intent = hora_cita`
   - `nuevo_estado = ST_CITA_PENDIENTE`
   - `next_action = confirm_appointment_request`
6. AppointmentRequest persistence was skipped because:
   - `fecha_solicitada` was missing

Decision:

Persist active appointment context in:

patients.appointment_context JSONB

Expected JSON shape:

{
  "fecha_solicitada": "2026-05-29",
  "fecha_solicitada_texto": "viernes 29 de mayo",
  "slots_candidatos": [
    "3:00 p. m.–5:00 p. m.",
    "5:00 p. m.–7:00 p. m."
  ],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null
}

Capture rule:

Store context when:

- result.intent == "fecha_cita"
- result.nuevo_estado == "ST_CITA_FRANJA"
- result.fecha_solicitada is present

Carryover rule:

Apply stored context when:

- result.intent == "hora_cita"
- result.nuevo_estado == "ST_CITA_PENDIENTE"
- result.fecha_solicitada is missing
- patient.appointment_context has fecha_solicitada

Clear rule:

Clear context when:

- AppointmentRequest persistence succeeds
- opt_out becomes true

---

## P6-F.9.14.14 — Appointment Context Pure Helpers + Tests

Status:

CLOSED / RED-THEN-GREEN / GREEN / COMMITTED

Files:

- app/services/appointment_context.py
- tests/test_appointment_context.py

Implemented pure helpers:

- capture_appointment_context_from_state(state)
- apply_appointment_context_to_state(state, context)
- should_clear_appointment_context(state, persisted: bool)

Properties:

- pure
- deterministic
- no DB access
- no network access
- no FastAPI dependency
- no LLM dependency

Validated behaviors:

- captures context after fecha_cita -> ST_CITA_FRANJA
- returns None when not fecha_cita
- returns None when fecha_solicitada missing
- restores context for hora_cita -> ST_CITA_PENDIENTE when fecha is missing
- does not override an already present fecha_solicitada
- ignores invalid context without fecha_solicitada
- clears after successful persistence
- clears on opt_out
- does not clear otherwise

---

## P6-F.9.14.15 — Patient Appointment Context Repository Methods

Status:

CLOSED / RED-THEN-GREEN / GREEN / COMMITTED

Documentation:

docs/P6-F.9.14.15_PATIENT_APPOINTMENT_CONTEXT_REPOSITORY_SPEC.md

Migration draft:

scripts/sql/002_add_patient_appointment_context.sql

Migration SQL:

ALTER TABLE patients
ADD COLUMN IF NOT EXISTS appointment_context JSONB;

Repository file:

app/repositories/patients.py

Implemented methods:

- update_patient_appointment_context(telefono, appointment_context)
- clear_patient_appointment_context(telefono)

Responsibilities:

The repository only persists or clears context.

It must not decide:

- when to capture context
- when to apply carryover
- when to clear context
- whether AppointmentRequest should be created
- appointment lifecycle transitions
- WhatsApp sending
- Google Sheets sync
- Telegram notification
- n8n workflows

Tests:

tests/test_patient_appointment_context_repository.py

Validated:

- update stores JSON-compatible appointment_context
- clear sets appointment_context to NULL
- telefono is required
- context is required for update

---

## P6-F.9.14.16 — Stateful Endpoint Carryover Wiring

Status:

CLOSED / RED-THEN-GREEN / GREEN / COMMITTED

Documentation:

docs/P6-F.9.14.16_STATEFUL_ENDPOINT_CARRYOVER_WIRING_CLOSURE.md

Runtime changed:

POST /test/message-stateful only.

Real POST /webhook remains untouched.

Files changed:

- app/main.py
- tests/test_stateful_appointment_context_carryover.py
- tests/test_stateful_appointment_request_wiring.py

Runtime behavior added to /test/message-stateful:

1. Reads patient.appointment_context
2. Applies stored context before calling decide_appointment_request_persistence(...)
3. Captures context after fecha_cita -> ST_CITA_FRANJA
4. Persists AppointmentRequest when decision allows it
5. Clears context after successful AppointmentRequest persistence
6. Clears context when opt_out is true

Validation:

pytest tests/test_stateful_appointment_request_wiring.py -q

Result:

4 passed

pytest tests/test_stateful_appointment_context_carryover.py -q

Result:

2 passed

Full suite:

pytest -q

Result:

186 passed

Important test isolation fix:

tests/test_stateful_appointment_request_wiring.py now monkeypatches:

- update_patient_appointment_context
- clear_patient_appointment_context

Reason:

After carryover wiring, /test/message-stateful may call these repository functions.

Unit tests must not reach the real production database.

Observed previous failure:

The test tried to resolve production host `elvira_elvira`.

This was fixed by proper monkeypatching.

Current safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation flow
- therapy/session package tracking
- automatic appointment confirmation

Current conclusion:

The stateful dry-run endpoint now supports appointment context carryover.

The original dry-run bug is fixed at the /test/message-stateful layer.

Before validating in production Swagger, production DB must receive:

ALTER TABLE patients
ADD COLUMN IF NOT EXISTS appointment_context JSONB;

Next exact block:

P6-F.9.14.17 — Controlled Production Migration: patients.appointment_context

Objective:

Execute and validate the controlled production migration for patients.appointment_context before running Swagger dry-run again.


---

## P6-F.9.14.19 — Appointment Flow Hardening: Relative Dates, Time Windows & Clarification Guards

Status:

SPEC CREATED / READY FOR TESTS

Reason for new block:

Production Swagger validation showed that the appointment flow is still too fragile for real patients.

Important finding:

The message:

`Maniana en la tarde`

while the patient was in `ST_CITA_FECHA` produced:

- intent = fecha_cita
- nuevo_estado = ST_CITA_FRANJA
- fecha_solicitada = null
- slots_candidatos = []
- response text included vague wording such as "la fecha indicada"

This is unsafe because Elvira advanced to an operational appointment state without a resolved date.

Core decision:

Relative date and time window must be parsed independently.

Examples:

- "mañana en la tarde" means relative_date = tomorrow, time_window = afternoon
- "mañana en la mañana" means relative_date = tomorrow, time_window = morning
- "en la mañana" means time_window = morning, but no date
- "en la tarde" means time_window = afternoon, but no date unless context exists

Normalization requirement:

The system must support:

- mañana
- manana
- maniana
- pasado mañana
- pasado manana
- pasado maniana

Schedule rule from KB:

Domiciliary care is not available in the morning.

Current KB schedule:

- HOR-01: Monday to Friday except Wednesday, domiciliary, 15:00–19:00, two visible slots: 15:00–17:00 and 17:00–19:00
- HOR-02: Wednesday, domiciliary, 15:00–18:00, one visible slot: 15:00–17:00
- HOR-03: Saturday, no domiciliary service
- HOR-04: Sunday, no service except explicit doctor instruction

Behavior decision:

If the patient says "mañana/manana/maniana en la mañana":

- resolve tomorrow as date
- confirm the resolved date
- explain that domiciliary care is only available in the afternoon
- offer the valid KB-backed afternoon slots
- do not accept morning as a valid domiciliary appointment slot

If the patient says "mañana/manana/maniana en la tarde":

- resolve tomorrow as date
- confirm the resolved date
- offer valid KB-backed afternoon slots
- ask which slot works better

Hard guard:

The system must never move to ST_CITA_FRANJA when fecha_solicitada is null.

The system must never move to ST_CITA_PENDIENTE when date context is missing.

Vague phrase guard:

Elvira must not say:

- "la fecha indicada"
- "ese día"
- "la fecha solicitada"

unless fecha_solicitada_texto exists.

Clarification handling:

If the patient asks:

- "cuál fecha?"
- "qué fecha indicada?"
- "no entendí"
- "qué quiere decir?"

inside appointment flow, Elvira must answer with a short clarification and ask again for the date, instead of treating it as a broad general question.

New SPEC:

docs/P6-F.9.14.19_APPOINTMENT_FLOW_HARDENING_SPEC.md

Next chat starting point:

Continue with P6-F.9.14.19 tests RED.

First inspect:

- app/services/intent.py
- date resolver module
- state machine module
- existing tests for date resolution and appointment routing

Then add failing tests for:

- Maniana en la tarde
- Maniana en la maniana
- En la maniana without date
- Cual fecha indicada?
- guard against ST_CITA_FRANJA without fecha_solicitada

Do not touch yet:

- POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation



---

## P6-F.9.14.19 — Appointment Flow Hardening: Relative Dates, Time Windows & Clarification Guards

Status:

CLOSED / RED-THEN-GREEN / GREEN / READY TO COMMIT

Validation:

Targeted tests:

```bash
pytest tests/test_date_resolver.py tests/test_intent.py tests/test_state_machine.py -q

Full suite:

pytest -q

Latest result:

196 passed

Reason for block:

Production Swagger validation showed that the appointment flow was still fragile with mixed relative-date and time-window phrases.

Unsafe examples:

Maniana en la tarde
Maniana en la maniana
En la maniana
Cual fecha indicada?

Main risks fixed:

maniana was not recognized as a patient typo/transliteration for mañana
en la maniana could be incorrectly interpreted as tomorrow instead of a morning-only time window
clarification questions could fall back to general
the flow could advance to ST_CITA_FRANJA without a resolved fecha_solicitada
Elvira could use vague wording such as la fecha indicada

Implemented changes:

app/services/date_resolver.py
supports maniana as a relative-date variant when it really means tomorrow
supports pasado maniana
prevents en la maniana / por la maniana from being interpreted as tomorrow when no date exists
app/services/intent.py
normalizes maniana safely in intent classification
routes appointment clarification questions inside appointment-date context:
Cual fecha indicada?
Cuál fecha indicada?
Qué fecha indicada?
No entendí
Qué quiere decir?
app/graph/nodes.py
adds deterministic guard after date resolution:
if intent == fecha_cita
and nuevo_estado == ST_CITA_FRANJA
and fecha_solicitada is missing
then force the flow back to:
nuevo_estado = ST_CITA_FECHA
next_action = ask_preferred_date
state_reason = missing_fecha_solicitada_guard
app/services/llm.py
removes unsafe fallback wording la fecha indicada
updates ask_preferred_date response to:
Claro, me refiero a la fecha de la cita. ¿Para qué día le gustaría agendarla?
recognizes maniana / pasado maniana in patient-facing date references

Tests added/updated:

tests/test_date_resolver.py
Maniana en la tarde resolves to tomorrow + afternoon slots
Maniana en la maniana resolves to tomorrow while redirecting to valid afternoon slots
En la maniana without date does not resolve a requested date
tests/test_intent.py
Maniana variants route to fecha_cita in appointment date state
clarification questions remain in appointment date context
tests/test_state_machine.py
Maniana en la tarde resolves date and offers slots
Maniana en la maniana resolves date but redirects to afternoon slots
En la maniana without date does not advance to ST_CITA_FRANJA
Cual fecha indicada? does not become general
guard blocks ST_CITA_FRANJA when fecha_solicitada is missing

Safety boundaries preserved:

Still not touched:

POST /webhook
real WhatsApp sending
Google Sheets
Telegram
n8n
Calendar
doctor confirmation automation
therapy/session package tracking

Current conclusion:

P6-F.9.14.19 closes the appointment-flow hardening gap for relative-date typos, time-window-only phrases, clarification questions, and missing-date state transitions.

The system now prevents advancing into ST_CITA_FRANJA without deterministic fecha_solicitada.

Next recommended step:

Commit P6-F.9.14.19.

After commit, run a controlled Swagger dry-run against /test/message-stateful for:

Quiero pedir una cita
Maniana en la tarde
En la maniana
Cual fecha indicada?
Maniana en la maniana

Do not touch real /webhook or WhatsApp sending yet.
