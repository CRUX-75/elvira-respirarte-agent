# AI_CONTEXT.md — Elvira Respirarte Agent

## Purpose

This file is the operational context for AI-assisted development on the Elvira / Respirarte project.

It exists so ChatGPT or any coding assistant can understand the repository structure, architecture decisions, documentation hierarchy, current branch, and current phase without rediscovering the repo from scratch.

This file is not public-facing documentation. It is a working context file.

---

## Current Working Status

Current repository:

elvira-respirarte-agent

Repository:

github.com/CRUX-75/elvira-respirarte-agent

Current working branch:

main

Current phase:

P6-F.9.18 — Production Activation Context Reconciliation

Current operational objective:

Prepare Elvira for controlled production activation with the official Respirarte Colombian WhatsApp number.

Latest confirmed local validation:

214 passed

Current safety baseline:

- FastAPI app is production-deployed.
- PostgreSQL production database is operational.
- Knowledge Base runtime is enabled.
- LangSmith production tracing is active.
- `/test/message-stateful` has been used as the safe production dry-run surface.
- AppointmentRequest persistence works after explicit patient confirmation.
- Elvira does not confirm appointments automatically.
- Elvira only registers appointment requests for human review by Dra. D'Aleman.
- Real `/webhook` activation/review is still pending.
- Real WhatsApp sending remains disabled.
- `WHATSAPP_SENDING_ENABLED=false` remains the production safety default.
- Google Sheets, Telegram, n8n, and Calendar are out of scope for the initial controlled MVP launch.
- Minor duplicated punctuation in one production response was accepted as non-blocking.

Current next production-preparation block:

P6-F.9.19 — Production Activation Checklist

Important current rule:

Do not touch real `/webhook` or enable real WhatsApp sending until the production activation checklist and webhook readiness review are completed.

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
- Google Sheets only as future human-visible operational inbox when needed
- n8n only as future auxiliary workflow layer when needed

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

Solicitudes_Cita / AppointmentRequest must not be treated as a Google Sheets-first object.

Correct direction:

AppointmentRequest internal model
→ AppointmentRequestService
→ AppointmentRequestRepository
→ PostgreSQL source of truth
→ future Google Sheets adapter / human inbox, optional
→ future doctor notification adapter, optional

Google Sheets is only a possible visible operational inbox for the doctor.

The source of truth for appointment request rules must remain in Python/PostgreSQL.

---

## Historical Context Notice

Older sections below are preserved for traceability.

If an older section says the project is in P6-F.9.12, P6-F.8, uses branch `p6-f-9-10-appointment-request-service-tests`, or has a test baseline such as 149/76 tests, treat that as historical context only.

The current source of truth is the "Current Working Status" section above.

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


---

## P6-F.9.14.20 — Controlled Stateful Swagger Dry-Run

Status:

CLOSED / TECHNICALLY GREEN / PRODUCT COPY GAP IDENTIFIED

Production Swagger endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Validated production dry-run sequence:

1. `Quiero pedir una cita`
2. `Maniana en la tarde`
3. `A las 3`

Final technical result:

- `Quiero pedir una cita` correctly moved the patient from `ST_INIT` to `ST_CITA_FECHA`.
- `Maniana en la tarde` correctly resolved:
  - `fecha_solicitada = 2026-05-29`
  - `fecha_solicitada_texto = viernes 29 de mayo`
  - `slots_candidatos = ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."]`
  - `nuevo_estado = ST_CITA_FRANJA`
- `A las 3` correctly moved the patient to:
  - `intent = hora_cita`
  - `nuevo_estado = ST_CITA_PENDIENTE`
  - `next_action = confirm_appointment_request`
- `AppointmentRequest` was created successfully in production PostgreSQL.
- `appointment_request.estado_solicitud = pendiente_confirmacion`
- `appointment_request.fecha_solicitada = 2026-05-29`
- `appointment_request.franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `source_interaction_id` used the synthetic `test-stateful-*` ID.
- `delivery_status = sending_skipped`
- real WhatsApp sending remained off.

Hotfix completed during this block:

P6-F.9.14.20.1 — AppointmentRequest Production Insert Hotfix

Reason:

The first production dry-run failed on the final appointment persistence step with a 500 error.

Root cause:

`PostgresAppointmentRequestRepository.save()` inserted explicit NULL values for `created_at` and `updated_at`.

PostgreSQL did not apply the table defaults because NULL was passed explicitly.

Observed error:

`null value in column "created_at" of relation "appointment_requests" violates not-null constraint`

Fix:

- Repository INSERT now uses:
  - `COALESCE(:created_at, CURRENT_TIMESTAMP)`
  - `COALESCE(:updated_at, CURRENT_TIMESTAMP)`
- Repository UPDATE now preserves `created_at` and refreshes `updated_at` safely:
  - `created_at = COALESCE(:created_at, created_at)`
  - `updated_at = COALESCE(:updated_at, CURRENT_TIMESTAMP)`
- `AppointmentRequestService.create_or_reuse_active_request(...)` now accepts:
  - `estado_solicitud: str = "nueva"`
- `/test/message-stateful` now passes:
  - `estado_solicitud=appointment_request_decision.estado_solicitud or "nueva"`

Validation after hotfix:

- local tests green
- production Swagger dry-run green
- AppointmentRequest persistence confirmed

Important product finding:

The test phrase `En la tarde` after Elvira already offered two afternoon slots is not a good real-patient final selection.

Reason:

If Elvira already says:

- `3:00 p. m.–5:00 p. m.`
- `5:00 p. m.–7:00 p. m.`

then a generic response like `En la tarde` is ambiguous and should not select the first slot by default in a future hardening block.

Correct final test phrase used:

`A las 3`

This correctly selected the first slot and created the AppointmentRequest.

Future hardening candidate:

Slot Selection Precision Guard

Rule idea:

When multiple candidate slots exist, generic phrases like `en la tarde`, `por la tarde`, or `tarde` should keep the patient in `ST_CITA_FRANJA` and ask them to choose between the specific slots instead of persisting an AppointmentRequest.

Do not implement this yet unless explicitly started as a new block.

Product copy gap found:

Initial appointment response currently says:

`Claro, me refiero a la fecha de la cita. ¿Para qué día le gustaría agendarla?`

This is not acceptable as the first response to:

`Quiero pedir una cita`

It sounds unnatural and confusing.

Approved next block:

P6-F.9.14.21 — Appointment Initial Copy + Slot Disclaimer Polish

Approved initial response direction:

`Claro, con muchísimo gusto. Le cuento que las atenciones domiciliarias se manejan solamente en la tarde, normalmente en dos franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Para qué día le gustaría agendar su cita?`

Important nuance:

At the initial appointment request, Elvira may explain the general afternoon-only domiciliary rule and usual candidate windows, but must not confirm real date-specific availability yet because no date has been selected.

Next exact starting point:

P6-F.9.14.21 — Appointment Initial Copy + Slot Disclaimer Polish

First command:

grep -R "me refiero a la fecha" -n app tests

Then follow SDD:

1. Inspect copy source.
2. Add RED test for initial appointment copy.
3. Add/adjust clarification test if needed.
4. Implement minimal copy/prompt change.
5. Run targeted tests.
6. Run full suite.
7. Update docs if needed.
8. Commit.

Safety boundaries still active:

Do not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

---

## P6-F.9.14.21 — Appointment Initial Copy + Slot Disclaimer Polish

Status:

CLOSED / RED-THEN-GREEN / GREEN / COMMITTED / CLEAN

Reason:

The initial appointment response to `Quiero pedir una cita` was too confusing because it said:

`Claro, me refiero a la fecha de la cita...`

This sounded like a clarification even though the patient had just started the appointment flow.

Change:

The initial `ask_preferred_date` copy now says:

`Claro, con muchísimo gusto. Le cuento que las atenciones domiciliarias se manejan solamente en la tarde, normalmente en dos franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Para qué día le gustaría agendar su cita?`

Important nuance:

This copy explains the general afternoon-only domiciliary rule and usual candidate windows, but it does not confirm real date-specific availability.

Files changed:

- app/services/llm.py
- tests/test_state_machine.py

Tests updated:

- `test_cita_flow` now protects the exact initial appointment copy.
- `test_p6f91419_clarification_question_does_not_become_general` now validates that clarification questions remain inside appointment-date context and still ask for the appointment day without using unsafe wording like `la fecha indicada`.

Validation:

- Targeted state machine tests GREEN
- Full suite GREEN
- Working tree clean after commit

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Current conclusion:

The initial appointment copy is now warmer, clearer, and aligned with the approved domiciliary slot disclaimer.

Next recommended block:

P6-F.9.14.22 — Controlled Swagger Copy Dry-Run

Objective:

Validate in production Swagger through `/test/message-stateful` only that `Quiero pedir una cita` returns the new initial appointment copy.

Do not touch real `/webhook`, WhatsApp sending, Google Sheets, Telegram, n8n, Calendar, or doctor confirmation automation.

---

## P6-F.9.14.22 — Controlled Swagger Copy Dry-Run

Status:

CLOSED / GREEN / PRODUCTION COPY VALIDATED

Objective:

Validate in production through `/test/message-stateful` only that the initial appointment message:

`Quiero pedir una cita`

returns the polished initial appointment copy with the afternoon domiciliary care disclaimer.

Production endpoint validated:

POST /test/message-stateful

Payload used:

{
  "telefono": "test-p6f91422a",
  "mensaje": "Quiero pedir una cita",
  "nombre": "Paciente Test Copy"
}

Production result:

- estado_anterior = ST_INIT
- estado_actual = ST_INIT
- nuevo_estado = ST_CITA_FECHA
- intent = cita
- next_action = ask_preferred_date
- delivery_status = sending_skipped
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = skipped_initial_cita_intent
- appointment_request = null

Validated response copy:

Claro, con muchísimo gusto. Le cuento que las atenciones domiciliarias se manejan solamente en la tarde, normalmente en dos franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Para qué día le gustaría agendar su cita?

Conclusion:

The production copy is correct.

Elvira now explains the general afternoon-only domiciliary care rule and usual time windows on the first appointment request, without confirming real date-specific availability.

The system correctly does not create an AppointmentRequest at this stage because no date or concrete time window has been selected yet.

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Next recommended block:

P6-F.9.14.23 — Slot Selection Precision Guard

Objective:

Prevent ambiguous generic time-window replies from selecting a slot automatically when multiple candidate slots exist.

Example future case:

If Elvira has already offered:

- 3:00 p. m.–5:00 p. m.
- 5:00 p. m.–7:00 p. m.

and the patient replies:

`En la tarde`

then the system should not automatically choose the first slot.

Expected future behavior:

- remain in ST_CITA_FRANJA
- do not persist AppointmentRequest
- ask the patient to choose one of the concrete offered slots

Do not start this block until P6-F.9.14.22 is committed cleanly.


---

## P6-F.9.14.23 — Slot Selection Precision Guard

Status:

CLOSED / RED-THEN-GREEN / GREEN / READY TO COMMIT

Reason:

After Elvira offered multiple concrete appointment slots, a generic patient reply such as:

`En la tarde`

could move the flow from `ST_CITA_FRANJA` to `ST_CITA_PENDIENTE`.

This was unsafe because the patient had not selected a concrete slot.

Example offered slots:

- 3:00 p. m.–5:00 p. m.
- 5:00 p. m.–7:00 p. m.

Generic replies like:

- en la tarde
- por la tarde
- tarde

must not automatically select the first slot.

Implemented behavior:

When the patient is in `ST_CITA_FRANJA` and replies with an ambiguous afternoon phrase:

- intent remains `hora_cita`
- nuevo_estado remains `ST_CITA_FRANJA`
- next_action becomes `ask_specific_time_slot`
- state_reason becomes `ambiguous_slot_selection_guard`
- Elvira asks the patient to choose one concrete available slot
- the flow does not advance to `ST_CITA_PENDIENTE`
- `confirm_appointment_request` is not triggered
- AppointmentRequest persistence is not reached from this ambiguous turn

Files changed:

- app/graph/transitions.py
- app/services/llm.py
- tests/test_state_machine.py

Important design decision:

The fix does not revert the previous intent routing fix.

`En la tarde` in `ST_CITA_FRANJA` may still classify as `hora_cita`.

The safety guard lives after intent classification, in deterministic transition behavior.

This preserves intent understanding while preventing unsafe state advancement.

Validated response copy:

Para continuar, por favor elija una de las franjas disponibles: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Cuál le queda mejor?

Validation:

Targeted state machine tests:

GREEN

Full suite:

198 passed

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

The appointment flow now avoids guessing the patient’s preferred slot when multiple concrete options exist.

Next recommended block:

P6-F.9.14.24 — Controlled Swagger Slot Guard Dry-Run

Objective:

Validate in production through `/test/message-stateful` only that after Elvira offers two slots, the patient reply `En la tarde` stays in `ST_CITA_FRANJA` and asks for a concrete slot instead of creating an AppointmentRequest.


---

## P6-F.9.14.24 — Controlled Swagger Slot Guard Dry-Run

Status:

PARTIAL / NEW SLOT MAPPING BUG FOUND

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Validated sequence:

1. `Quiero pedir una cita`
2. `Para maniana`
3. `se puede a las 5?`

Observed successful behavior:

- Initial appointment copy was correct.
- `Para maniana` correctly resolved:
  - fecha_solicitada = 2026-05-29
  - fecha_solicitada_texto = viernes 29 de mayo
  - slots_candidatos:
    - 3:00 p. m.–5:00 p. m.
    - 5:00 p. m.–7:00 p. m.
  - nuevo_estado = ST_CITA_FRANJA
- Final message `se puede a las 5?` correctly classified as:
  - intent = hora_cita
  - nuevo_estado = ST_CITA_PENDIENTE
  - next_action = confirm_appointment_request
  - appointment_request_decision.should_persist = true

Bug found:

The final concrete selection:

`se puede a las 5?`

was persisted with the wrong requested slot:

Observed:

franja_solicitada = 3:00 p. m.–5:00 p. m.

Expected:

franja_solicitada = 5:00 p. m.–7:00 p. m.

Diagnosis:

The system appears to select the first candidate slot as fallback instead of mapping the patient's concrete time expression to the correct offered slot.

This is not the same as the ambiguous `En la tarde` guard.

This is a new concrete slot mapping bug.

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Next recommended block:

P6-F.9.14.25 — Concrete Slot Mapping Guard

Objective:

Map concrete patient slot selections to the correct candidate slot before AppointmentRequest persistence.

Examples:

- `A las 3`, `a las tres`, `de 3 a 5`, `la primera`
  → 3:00 p. m.–5:00 p. m.

- `A las 5`, `a las cinco`, `de 5 a 7`, `la segunda`
  → 5:00 p. m.–7:00 p. m.

The system must not default to the first slot when the patient clearly selected the second slot.


---

## P6-F.9.14.24 — Controlled Swagger Slot Guard Dry-Run

Status:

PARTIAL / NEW CONCRETE SLOT MAPPING BUG FOUND

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Validated sequence:

1. `Quiero pedir una cita`
2. `Para maniana`
3. `se puede a las 5?`

Observed successful behavior:

Initial appointment copy was correct.

`Para maniana` correctly resolved:

- fecha_solicitada = 2026-05-29
- fecha_solicitada_texto = viernes 29 de mayo
- slots_candidatos:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_preferred_time

Final message:

`se puede a las 5?`

correctly classified as:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- appointment_request_decision.should_persist = true

Bug found:

The final concrete selection:

`se puede a las 5?`

was persisted with the wrong requested slot.

Observed:

franja_solicitada = 3:00 p. m.–5:00 p. m.

Expected:

franja_solicitada = 5:00 p. m.–7:00 p. m.

Root cause found in:

app/services/appointment_request_runtime.py

Current unsafe logic:

franja_solicitada = slots[0] if slots else None

This blindly selects the first candidate slot whenever slots exist.

This explains why a clear patient preference for 5 p. m. was persisted as the 3–5 p. m. slot.

Additional cleanup finding:

app/services/llm.py currently contains a duplicated block for:

if state.next_action == "ask_specific_time_slot":

This should be cleaned in the next block or before final implementation.

Important product decision:

The patient may ask:

- `se puede a las 3?`
- `se puede a las 5?`

These must map deterministically to the visible offered franjas:

- `se puede a las 3?` → 3:00 p. m.–5:00 p. m.
- `se puede a las 5?` → 5:00 p. m.–7:00 p. m.

If the patient asks for another loose hour outside the offered slot starts, for example:

- `se puede a las 4?`
- `se puede a las 6?`
- `a las 2`
- `a las 7`
- `a las 10`

the agent must not persist an AppointmentRequest.

Expected behavior for unsupported loose hours:

- stay in ST_CITA_FRANJA
- do not trigger confirm_appointment_request
- do not persist AppointmentRequest
- answer that only the offered franjas can be registered as preference
- ask the patient to choose between the two offered franjas

Product nuance:

Even if a loose time such as `4` is technically inside 3:00 p. m.–5:00 p. m., it must not be interpreted as a valid slot selection.

The business flow works with visible appointment franjas, not arbitrary exact hours inside a franja.

Correct assistant copy direction:

`Por ahora solo puedo registrar su preferencia dentro de estas dos franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Cuál de las dos le queda mejor?`

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

P6-F.9.14.24 is not fully GREEN because the Swagger dry-run revealed a new concrete slot mapping bug.

Next exact block:

P6-F.9.14.25 — Concrete Slot Mapping & Out-of-Slot Guard

Objective:

Implement deterministic slot mapping before AppointmentRequest persistence.

Required valid mappings:

- `A las 3`
- `se puede a las 3?`
- `a las tres`
- `de 3 a 5`
- `la primera`
- `el primer horario`

must map to:

3:00 p. m.–5:00 p. m.

And:

- `A las 5`
- `se puede a las 5?`
- `a las cinco`
- `de 5 a 7`
- `la segunda`
- `el segundo horario`

must map to:

5:00 p. m.–7:00 p. m.

Required blocking behavior:

Unsupported loose hours such as:

- `se puede a las 4?`
- `se puede a las 6?`
- `a las 2`
- `a las 7`
- `a las 10`

must not default to the first slot.

Recommended starting point in next chat:

1. Clean duplicated `ask_specific_time_slot` block in app/services/llm.py.
2. Create SPEC:

docs/P6-F.9.14.25_CONCRETE_SLOT_MAPPING_AND_OUT_OF_SLOT_GUARD_SPEC.md

3. Add RED tests in:

tests/test_appointment_request_runtime_decision.py

4. Implement deterministic helper near:

app/services/appointment_request_runtime.py

Possible helper:

resolve_requested_slot_from_message(message, slots)

5. Remove blind fallback:

franja_solicitada = slots[0] if slots else None

6. Run targeted tests.
7. Run full suite.
8. Update docs.
9. Commit.

Latest known full suite before this new block:

198 passed



---

## P6-F.9.14.25 — Concrete Slot Mapping & Out-of-Slot Guard

Status:

CLOSED / RED-THEN-GREEN / GREEN / COMMITTED

Reason:

Production Swagger dry-run in P6-F.9.14.24 revealed a concrete slot mapping bug.

Scenario:

1. Elvira offered two appointment franjas:
   - 3:00 p. m.–5:00 p. m.
   - 5:00 p. m.–7:00 p. m.
2. Patient replied:
   - `se puede a las 5?`
3. The system persisted:
   - franja_solicitada = 3:00 p. m.–5:00 p. m.
4. Expected:
   - franja_solicitada = 5:00 p. m.–7:00 p. m.

Root cause:

app/services/appointment_request_runtime.py used a blind first-slot fallback:

franja_solicitada = slots[0] if slots else None

This caused any concrete or loose time expression to default to the first offered slot.

Implemented fix:

File changed:

- app/services/appointment_request_runtime.py

New deterministic helper:

- resolve_requested_slot_from_message(message, slots)

The helper maps concrete patient slot selections to the correct visible offered franja.

Supported first-slot mappings:

- A las 3
- se puede a las 3?
- a las tres
- de 3 a 5
- la primera
- el primer horario
- la primera franja

Maps to:

3:00 p. m.–5:00 p. m.

Supported second-slot mappings:

- A las 5
- se puede a las 5?
- a las cinco
- de 5 a 7
- la segunda
- el segundo horario
- la segunda franja

Maps to:

5:00 p. m.–7:00 p. m.

New guard:

Unsupported loose hours are blocked.

Examples:

- se puede a las 4?
- se puede a las 6?
- a las 2
- a las 7
- a las 10

Expected behavior:

- AppointmentRequest persistence is blocked
- no fallback to the first slot
- decision reason = skipped_unsupported_slot_selection

Important product rule:

The business flow registers visible appointment franjas, not arbitrary exact loose hours inside a franja.

Even if `4` is technically inside `3:00 p. m.–5:00 p. m.`, it must not be interpreted as a valid slot selection.

The patient must choose one of the visible offered franjas.

Tests changed:

- tests/test_appointment_request_runtime_decision.py
- tests/test_stateful_appointment_context_carryover.py
- tests/test_stateful_appointment_request_wiring.py

Test coverage added/updated:

- maps `se puede a las 3?` to first slot
- maps `se puede a las 5?` to second slot
- maps ordinal selections:
  - la primera franja
  - el segundo horario
- blocks unsupported loose hours:
  - se puede a las 4?
  - a las 6
- confirms no fallback to the first slot
- updates legacy persistence tests to use concrete slot selections instead of generic `En la tarde`

Validation:

Targeted decision tests:

21 passed

Stateful endpoint/carryover tests:

6 passed

Full suite:

203 passed

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

The concrete slot mapping bug is fixed.

The system no longer defaults to the first available franja when the patient clearly selects the second one or asks for an unsupported loose hour.

Next recommended block:

P6-F.9.14.26 — Controlled Swagger Concrete Slot Mapping Dry-Run

Objective:

Validate in production through `/test/message-stateful` only that:

1. `se puede a las 5?` persists:
   - franja_solicitada = 5:00 p. m.–7:00 p. m.

2. `se puede a las 3?` persists:
   - franja_solicitada = 3:00 p. m.–5:00 p. m.

3. `se puede a las 4?` does not persist and asks the patient to choose between the visible franjas.

Do not touch:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation


---

## P6-F.9.14.26 — Controlled Swagger Concrete Slot Mapping Dry-Run

Status:

PAUSED / PARTIAL GREEN / PRODUCT CONTRACT UPDATED

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Validated Test A:

Flow:

1. `Para pedir una cita`
2. `Para maniana es posible?`
3. `se puede a las 5?`

Result:

- initial appointment copy correct
- `maniana` resolved correctly to `2026-05-29`
- visible slots returned:
  - `3:00 p. m.–5:00 p. m.`
  - `5:00 p. m.–7:00 p. m.`
- final message `se puede a las 5?` mapped correctly to:
  - `5:00 p. m.–7:00 p. m.`
- AppointmentRequest was created
- `appointment_request_decision.should_persist = true`
- `appointment_request.franja_solicitada = 5:00 p. m.–7:00 p. m.`
- `delivery_status = sending_skipped`

Technical result:

Test A technical mapping is GREEN.

Reason for pause:

During review, the appointment scheduling flow revealed product/operational complexity that should not be solved by code assumptions.

The block was paused before running Test B and Test C.

Decision:

Do not continue coding appointment scheduling until the operational contract is validated and documented.

---

## Appointment Operational Contract v1.0 — Doctor Validation

Document:

Contrato_Operativo_Agendamiento_Respirarte_v1.0

Status:

DEFINITIVE FOR DOCTOR VALIDATION / BORRADOR PENDING DOCTOR FINAL APPROVAL

Core principle:

Elvira recoge.
La doctora decide.
El sistema registra.

Architecture sealed:

- FastAPI/PostgreSQL is the technical source of truth.
- Google Sheets is the human-visible operational inbox for Dra. D'Aleman.
- n8n is excluded from the core appointment scheduling flow.
- Any doctor notification must be implemented as a controlled backend adapter.
- Elvira must not confirm real availability.
- Elvira must not approve or reject appointments.
- Elvira must not promise an exact hour inside a franja.

Contract workflow:

1. Patient requests appointment via WhatsApp.
2. Elvira collects preferred date and preferred time window/franja.
3. FastAPI creates AppointmentRequest.
4. Backend generates SOL- ID.
5. PostgreSQL persists AppointmentRequest as source of truth.
6. System adapter syncs request to Google Sheets with pending human-review status.
7. System adapter notifies Dra. D'Aleman through validated channel.
8. Elvira sends terminal message to patient.
9. Dra. D'Aleman reviews in Sheets.
10. Dra. D'Aleman approves, rejects, cancels, confirms, or proposes alternative.

ADR sealed:

n8n remains excluded from the core scheduling flow.

The creation, identification, persistence, and transition of appointment requests belong exclusively to FastAPI/Python and PostgreSQL.

---

## Doctor Answers — Operational Decisions

Dra. D'Aleman provided the following operational decisions:

1. Expected patient response time:
   - 30–60 minutes.

2. Patient terminal message after request registration:
   - “Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.”

3. Doctor notification channel:
   - WhatsApp.

4. Exact-hour requests:
   - The patient must be told politely that care is handled by time window/franja.
   - It is not possible to guarantee an exact hour inside the assigned block.
   - The patient should be advised to keep the full time window available.

5. Out-of-hours message:
   - “Gracias por escribirnos. En este momento nuestro horario de atención ha finalizado, pero hemos recibido tu mensaje. Pronto nos pondremos en contacto para ayudarte con tu agendamiento.”

Important wording decision:

Do not hardcode only `3:00 p. m.–5:00 p. m.` in patient responses.

The doctor's mention of 3–5 is treated as an example.

The system must always use KB_Horarios as the source of truth for valid franjas.

---

## P6-F.9.14.27 — KB-Based Exact-Hour Franja Clarification Guard

Status:

SPEC CREATED / READY FOR TESTS

Spec document:

docs/P6-F.9.14.27_KB_BASED_EXACT_HOUR_FRANJA_CLARIFICATION_SPEC.md

Reason:

The previous out-of-slot guard blocked loose exact hours such as:

- `se puede a las 4?`
- `a las 6`

After doctor validation, the product rule changed:

If the exact hour falls inside a visible KB-backed franja, Elvira should not reject abruptly.

Instead, Elvira should:

1. explain that attention is handled by franjas, not guaranteed exact hours
2. map the exact hour to the corresponding KB-backed franja
3. ask the patient to confirm that franja
4. persist only after patient confirmation

New desired behavior:

Example 1:

Patient says:

`se puede a las 4?`

If KB slots include:

`3:00 p. m.–5:00 p. m.`

Expected:

- stay in ST_CITA_FRANJA
- do not persist yet
- next_action = ask_confirm_exact_hour_as_slot
- store pending franja in appointment_context
- ask if patient wants to register that franja

Example 2:

Patient says:

`se puede a las 6?`

If KB slots include:

`5:00 p. m.–7:00 p. m.`

Expected:

- stay in ST_CITA_FRANJA
- do not persist yet
- next_action = ask_confirm_exact_hour_as_slot
- store pending franja in appointment_context
- ask if patient wants to register that franja

Example 3:

Patient confirms after clarification:

`sí`

Expected:

- use pending exact-hour franja from appointment_context
- persist AppointmentRequest
- move to ST_CITA_PENDIENTE
- respond with doctor-approved terminal message
- mention 30–60 minute expected confirmation window if operationally allowed

Example 4:

Patient asks for an exact hour outside all KB slots:

`a las 2`

Expected:

- do not persist
- stay in ST_CITA_FRANJA
- show available KB-backed franjas
- ask patient to choose one

State machine decision:

Do not create a new patient state yet.

Keep:

ST_CITA_FRANJA

Use new next_action:

ask_confirm_exact_hour_as_slot

Suggested appointment_context fields:

- pending_exact_hour_franja
- pending_exact_hour_text
- pending_exact_hour_requires_confirmation

Safety boundaries:

Do not touch yet:

- real POST /webhook
- real WhatsApp sending
- Google Sheets adapter
- Doctor WhatsApp Notification Adapter
- Telegram
- n8n
- Calendar
- therapy/session package tracking

Next starting point in new chat:

P6-F.9.14.27 tests RED.

First inspect:

- app/services/appointment_request_runtime.py
- app/services/appointment_context.py
- app/graph/transitions.py
- app/services/intent.py
- app/services/llm.py
- tests/test_state_machine.py
- tests/test_appointment_request_runtime_decision.py
- tests/test_stateful_appointment_context_carryover.py

Then implement through SDD:

SPEC → tests RED → implementation mínima → targeted tests → full pytest → docs update → commit.


---

## Checkpoint — P6-F.9.14.27 KB-Based Exact-Hour Franja Clarification Guard

Status: GREEN / CLOSED

### Context

P6-F.9.14.26 quedó pausado como PARTIAL GREEN después de validar en producción que el sistema podía persistir correctamente una solicitud cuando el paciente decía una hora concreta como “se puede a las 5?”, mapeándola a la franja `5:00 p. m.–7:00 p. m.`.

Después de esa validación técnica, Dra. D’Aleman definió una regla operativa más precisa:

- Respirarte trabaja por franjas horarias.
- No se debe garantizar una hora exacta dentro de la franja.
- Si el paciente menciona una hora exacta que cae dentro de una franja visible de `KB_Horarios`, Elvira debe aclarar primero la franja correspondiente y pedir confirmación.
- Solo después de que el paciente confirme la franja, el sistema debe persistir `AppointmentRequest`.

### New Operational Rule

If a patient says an exact loose hour inside a visible KB schedule slot, for example:

- “se puede a las 3?”
- “se puede a las 5?”
- “a las 6”

and that hour falls inside one of the visible KB slots, Elvira must not persist the appointment request immediately.

Instead:

1. Resolve the matching KB franja.
2. Return a non-persistence decision.
3. Use reason `requires_exact_hour_franja_confirmation`.
4. Keep the matched `franja_solicitada` in the decision.
5. Let the response layer clarify that care is handled by franjas, not guaranteed exact hours.
6. Persist only when the patient explicitly confirms/selects the franja.

### Runtime Changes

Implemented in:

- `app/services/appointment_request_runtime.py`

Added helper:

- `is_exact_hour_without_explicit_franja_confirmation(message)`

Behavior:

- Loose exact-hour messages such as “a las 3”, “a las 5”, “se puede a las 5?” trigger clarification.
- Explicit franja selections such as “la primera franja”, “el segundo horario”, “la franja de 5 a 7 está bien” still allow persistence.
- Unsupported loose hours outside visible KB slots continue to avoid persistence.

### Tests Added / Updated

Added:

- `tests/test_kb_based_exact_hour_franja_clarification_guard.py`

Updated:

- `tests/test_appointment_request_runtime_decision.py`
- `tests/test_stateful_appointment_context_carryover.py`
- `tests/test_stateful_appointment_request_wiring.py`

### Validated Test Results

Focused suite:

```bash
pytest tests/test_appointment_request_runtime_decision.py tests/test_kb_based_exact_hour_franja_clarification_guard.py tests/test_stateful_appointment_request_wiring.py -q

Result:

28 passed

Full suite:

pytest -q

Result:

206 passed
Architectural Decision Preserved

The operational contract remains:

Elvira recoge.
La doctora decide.
El sistema registra.

Architecture remains sealed:

FastAPI/PostgreSQL = source of truth.
Google Sheets = visible operational tray.
n8n remains outside the core.
Doctor WhatsApp notification remains for a later backend adapter phase.
Next Step

Commit P6-F.9.14.27 changes.



---

## P6-F.9.14.28 — Response-layer Exact-Hour Franja Confirmation

Status:

CLOSED / GREEN / COMMITTED / CLEAN

Commit:

Add exact-hour franja confirmation response handling

Validation:

Full suite GREEN

207 passed

Reason:

P6-F.9.14.27 introduced the runtime guard for exact-hour messages inside a visible KB-backed franja.

When the patient says something like:

- se puede a las 5?

and the hour maps to a visible KB_Horarios franja, the runtime returns:

- should_persist = False
- reason = requires_exact_hour_franja_confirmation
- franja_solicitada = corresponding KB-backed franja

The missing part was patient-facing response handling.

Implementation:

File changed:

- app/main.py

A deterministic response override was added in `/test/message-stateful`.

When:

reason == "requires_exact_hour_franja_confirmation"

the endpoint overrides `result.respuesta` with a controlled response that:

- explains that attention is handled by time windows / franjas
- explains that an exact hour cannot be guaranteed inside the block
- proposes the corresponding KB-backed franja
- asks the patient to explicitly confirm that franja
- does not persist an AppointmentRequest yet

Example response:

Con gusto. Le cuento que la atención se maneja por franjas horarias y no es posible garantizar una hora exacta dentro del bloque. Para esa hora, la franja correspondiente sería de 5:00 p. m. a 7:00 p. m. ¿Desea que registremos su solicitud para esa franja?

Important implementation detail:

`logged_response` is now built after the response override.

This ensures the endpoint response and the saved interaction log use the same patient-facing text.

Test added:

- tests/test_stateful_appointment_context_carryover.py

Covered behavior:

- `/test/message-stateful` returns the exact-hour franja clarification copy
- `appointment_request_decision.should_persist` remains false
- `appointment_request_decision.reason` is `requires_exact_hour_franja_confirmation`
- `appointment_request_decision.franja_solicitada` uses the KB-backed franja
- `appointment_request` remains null
- AppointmentRequestService is not called
- interaction log stores the overridden response text

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets adapter
- Doctor WhatsApp Notification Adapter
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Current conclusion:

P6-F.9.14.28 closes the response-layer gap for exact-hour franja clarification.

The stateful test endpoint can now explain the franja rule clearly and ask for explicit confirmation before persistence.

Next recommended block:

P6-F.9.14.29 — Controlled Swagger Exact-Hour Franja Confirmation Dry-Run

Objective:

Validate in production through `/test/message-stateful` only that:

1. Patient starts appointment flow.
2. Patient provides a valid date.
3. Patient asks for an exact hour that maps to a KB-backed franja.
4. Elvira does not persist an AppointmentRequest yet.
5. Elvira explains the franja rule and asks for explicit confirmation.

Suggested Swagger sequence:

1. Quiero pedir una cita
2. Para maniana
3. se puede a las 5?

Expected final result:

- should_persist = false
- reason = requires_exact_hour_franja_confirmation
- franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request = null
- delivery_status = sending_skipped
- response explains franja handling and asks for confirmation

Do not touch:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Doctor WhatsApp adapter
- Telegram
- n8n
- Calendar

---

## P6-F.9.14.30 — Weekend/Unavailable Date State Regression Guard

Status:

CLOSED / RED-THEN-GREEN / GREEN

Reason:

Production Swagger dry-run in P6-F.9.14.29 revealed a dangerous inconsistency.

Scenario:

1. Patient requested an appointment.
2. Patient said `Para maniana`.
3. `maniana` resolved to Saturday 2026-05-30.
4. The system correctly detected:
   - `is_weekend = true`
   - `es_dia_disponible = false`
   - `slots_candidatos = []`
5. Patient then said `se puede a las 5?`.

Observed unsafe behavior before fix:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- response implied the request was registered
- `appointment_request_decision.should_persist = false`
- `appointment_request_decision.reason = skipped_weekend`
- `appointment_request = null`

The decision layer blocked persistence correctly, but the state/response layer had already advanced incorrectly.

Fix:

Added deterministic unavailable appointment context guard in:

- `app/graph/transitions.py`

New helper:

- `_has_unavailable_appointment_context(state)`

Behavior:

If the patient is in `ST_CITA_FRANJA`, gives a `hora_cita`, and there is an already resolved unavailable date context, the state machine now blocks the transition to appointment confirmation.

Blocked conditions apply only when `fecha_solicitada` exists and one of these is true:

- `is_weekend is True`
- `is_colombia_holiday is True`
- `es_dia_disponible is False`
- `slots_candidatos` is empty

Safe result:

- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `state_reason = unavailable_date_guard`

Important calibration:

The guard does not trigger when `fecha_solicitada` is missing.

This avoids breaking legacy or generic appointment-time tests where availability context has not been resolved yet.

Tests:

Added regression test in:

- `tests/test_state_machine.py`

Validation:

- `pytest tests/test_state_machine.py -q` → 20 passed
- `pytest tests/test_stateful_appointment_context_carryover.py -q` → 3 passed
- `pytest tests/test_appointment_request_runtime_decision.py -q` → 21 passed
- `pytest -q` → 208 passed

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

Unavailable date context now wins over later hour selection.

The state machine no longer allows Saturday/unavailable-date flows to reach `ST_CITA_PENDIENTE` or `confirm_appointment_request`.

Next recommended block:

P6-F.9.14.31 — Controlled Swagger Unavailable-Date Regression Dry-Run

Objective:

Validate in production through `/test/message-stateful` only that this sequence no longer produces fake registration copy:

1. `Quiero pedir una cita`
2. `Para maniana`
3. `se puede a las 5?`

Expected final result:

- no `ST_CITA_PENDIENTE`
- no `confirm_appointment_request`
- no AppointmentRequest created
- response asks for another valid date
- `delivery_status = sending_skipped`


---

## P6-F.9.14.32 — Stateful Carryover Before Confirmation Guard

Status:

CLOSED / GREEN

Reason:

Production Swagger dry-run in P6-F.9.14.31 showed that `/test/message-stateful` could still return unsafe confirmation copy after an unavailable date context was carried over.

Observed unsafe behavior:

1. Patient requested an appointment.
2. Patient said `Para maniana`.
3. The date resolved to Sunday 2026-05-31:
   - `is_weekend = true`
   - `es_dia_disponible = false`
   - `slots_candidatos = []`
4. Elvira correctly told the patient that no consultations are available that day.
5. Patient then said `se puede a las 5?`.

Before the fix, the endpoint returned:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- response implied the request was registered
- `appointment_request_decision.should_persist = false`
- `appointment_request_decision.reason = skipped_weekend`
- `appointment_request = null`

Diagnosis:

The persistence decision layer correctly blocked AppointmentRequest creation, but the response/state layer had already advanced incorrectly.

Fix:

Added endpoint-level safety helper in:

- `app/main.py`

New helper:

- `_force_unavailable_date_guard_response(result)`

Behavior:

After appointment context carryover and after `decide_appointment_request_persistence(...)`, if the decision reason is:

- `skipped_weekend`
- `skipped_colombia_holiday`
- `skipped_unavailable_date`

then the endpoint forces safe state/copy before `logged_response`, `save_interaction`, and `update_patient_state`.

Safe result:

- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `state_reason = unavailable_date_guard`
- response asks for another valid weekday/date
- no fake registration copy
- no AppointmentRequest created

Scope:

Only `/test/message-stateful`.

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Validation:

Targeted tests GREEN.

Full suite GREEN.

Next recommended block:

P6-F.9.14.33 — Controlled Swagger Stateful Carryover Guard Dry-Run

Objective:

Validate in production through `/test/message-stateful` only that this sequence no longer returns fake registration copy:

1. `Quiero pedir una cita`
2. `Para maniana`
3. `se puede a las 5?`

Expected final result:

- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `state_reason = unavailable_date_guard`
- `persisted_state = ST_CITA_FECHA`
- `appointment_request = null`
- response does not contain `queda registrada`
- `delivery_status = sending_skipped`


---

## P6-F.9.14.33 — Controlled Swagger Stateful Carryover Guard Dry-Run

Status:

CLOSED / GREEN / PRODUCTION VALIDATED

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Validated sequence:

1. `Quiero pedir una cita`
2. `Para maniana`
3. `se puede a las 5?`
4. Additional sanity check: `ahh, no atienden fines de semana?`

Production context:

At validation time, Colombia current date was:

- `fecha_actual_colombia = 2026-05-30`

Therefore:

- `maniana` resolved to `domingo 31 de mayo`
- `fecha_solicitada = 2026-05-31`
- `is_weekend = true`
- `es_dia_disponible = false`
- `slots_candidatos = []`

Final result for `se puede a las 5?`:

- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `state_reason = unavailable_date_guard`
- `persisted_state = ST_CITA_FECHA`
- `appointment_request_decision.should_persist = false`
- `appointment_request_decision.reason = skipped_weekend`
- `appointment_request = null`
- `delivery_status = sending_skipped`

Validated response:

`Domingo 31 de mayo no tenemos atención domiciliaria disponible. ¿Le gustaría indicarme otro día entre semana para revisar las franjas disponibles?`

Important validation:

The endpoint no longer returns fake registration copy.

Confirmed NOT present:

- no `ST_CITA_PENDIENTE`
- no `confirm_appointment_request`
- no `queda registrada`
- no AppointmentRequest creation

Additional sanity check:

Patient asked:

`ahh, no atienden fines de semana?`

Result:

- `intent = horarios`
- `next_action = answer_schedule`
- `persisted_state = ST_CITA_FECHA`
- `appointment_request = null`

This confirms that Elvira can answer a schedule clarification while remaining safely inside the appointment-date flow.

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

The stateful carryover guard is production-validated.

Unavailable date context now wins over later hour-selection messages in `/test/message-stateful`.


---

## P6-F.9.14.35 — Exact-Hour Franja Confirmation State Guard

Status:

CLOSED / RED-THEN-GREEN / GREEN

Reason:

The controlled Swagger dry-run P6-F.9.14.34 validated that exact-hour franja mapping and AppointmentRequest persistence blocking worked correctly, but revealed a state advancement bug.

Observed production dry-run behavior before fix:

- Patient asked: `se puede a las 5?`
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request = null

But the endpoint still persisted:

- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- persisted_state = ST_CITA_PENDIENTE

This was unsafe because the patient had not explicitly confirmed that the proposed franja should be registered.

Files changed:

- app/main.py
- tests/test_stateful_appointment_context_carryover.py
- docs/P6-F.9.14.35_EXACT_HOUR_FRANJA_CONFIRMATION_STATE_GUARD_SPEC.md

Implementation:

Added helper in app/main.py:

- _force_exact_hour_franja_confirmation_state_guard_response(result)

Runtime behavior:

When:

appointment_request_decision.reason == "requires_exact_hour_franja_confirmation"

the endpoint now forces before save_interaction() and update_patient_state():

- result.nuevo_estado = ST_CITA_FRANJA
- result.next_action = ask_confirm_exact_hour_as_slot
- result.state_reason = requires_exact_hour_franja_confirmation

The response still explains:

- care is handled by time window/franja
- exact hour inside the block cannot be guaranteed
- the matching franja is proposed
- explicit confirmation is required before registering the request

Validation:

Targeted test:

pytest tests/test_stateful_appointment_context_carryover.py::test_stateful_endpoint_returns_exact_hour_franja_confirmation_copy -q

Result:

1 passed

Related endpoint tests:

pytest tests/test_stateful_appointment_context_carryover.py tests/test_stateful_appointment_request_wiring.py -q

Result:

7 passed

Full suite:

pytest -q

Result:

208 passed

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

The exact-hour franja confirmation guard now prevents premature state advancement to ST_CITA_PENDIENTE.

The patient remains in ST_CITA_FRANJA until they explicitly confirm the proposed franja.

Next recommended block:

P6-F.9.14.36 — Controlled Swagger Exact-Hour State Guard Dry-Run

Objective:

Validate in production through /test/message-stateful only that:

1. Quiero pedir una cita
2. Para el lunes
3. se puede a las 5?

now returns:

- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request = null
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_confirm_exact_hour_as_slot
- persisted_state = ST_CITA_FRANJA
- delivery_status = sending_skipped

Do not touch:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation

---

## P6-F.9.14.36 — Controlled Swagger Exact-Hour State Guard Dry-Run

Status:

CLOSED / GREEN / PRODUCTION VALIDATED

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Google Sheets, Telegram, n8n, Calendar, doctor confirmation automation, and therapy/session package tracking were not touched.

Validated production sequence:

1. `Quiero pedir una cita`
2. `Para el lunes`
3. `se puede a las 5?`

Final result for `se puede a las 5?`:

- estado_anterior = ST_CITA_FRANJA
- estado_actual = ST_CITA_FRANJA
- nuevo_estado = ST_CITA_FRANJA
- intent = hora_cita
- next_action = ask_confirm_exact_hour_as_slot
- state_reason = requires_exact_hour_franja_confirmation
- persisted_state = ST_CITA_FRANJA
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.fecha_solicitada = 2026-06-01
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request_decision.hora_solicitada_texto = se puede a las 5?
- appointment_request = null
- delivery_status = sending_skipped

Validated response behavior:

Elvira explains that care is handled by time windows/franjas, not guaranteed exact hours, proposes the matching franja, and asks for explicit confirmation before registering the request.

Conclusion:

P6-F.9.14.35 fix is validated in production dry-run.

The system no longer advances prematurely to ST_CITA_PENDIENTE when an exact-hour request requires franja confirmation.

Minor copy polish found:

The response currently contains a double period after the franja:

`5:00 p. m. a 7:00 p. m..`

This is non-blocking and can be corrected in a later copy polish microblock.

Next recommended block:

P6-F.9.14.37 — Explicit Confirmation After Exact-Hour Franja

Objective:

Validate and, if needed, implement the next-turn behavior after Elvira asks:

`¿Desea que registremos su solicitud para esa franja?`

Expected future flow:

1. Patient asks: `se puede a las 5?`
2. Elvira stays in ST_CITA_FRANJA and asks confirmation for 5:00 p. m.–7:00 p. m.
3. Patient replies: `sí`
4. System should use the pending exact-hour franja context
5. System should then persist AppointmentRequest
6. System should move to ST_CITA_PENDIENTE
7. System should respond with the doctor-approved terminal message

Do not touch:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation

---

## P6-F.9.14.38 — Pending Exact-Hour Franja Confirmation Context

Status:

CLOSED / RED-THEN-GREEN / GREEN

Reason:

P6-F.9.14.37 showed that after Elvira asked the patient to confirm a franja derived from an exact-hour request, the next patient reply `si` was classified as general.

Observed bug:

1. Patient asked: `se puede a las 5?`
2. Runtime correctly returned:
   - nuevo_estado = ST_CITA_FRANJA
   - next_action = ask_confirm_exact_hour_as_slot
   - appointment_request_decision.reason = requires_exact_hour_franja_confirmation
   - appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
   - appointment_request = null
3. Patient replied: `si`
4. Runtime incorrectly returned:
   - intent = general
   - next_action = answer_general
   - appointment_request_decision.reason = skipped_non_appointment_intent
   - appointment_request = null

Root cause:

The system did not persist pending exact-hour confirmation context.

The existing appointment_context only stored date and slot context, but not:

- pending_exact_hour_franja
- pending_exact_hour_text
- pending_exact_hour_requires_confirmation

Files changed:

- app/main.py
- app/services/appointment_context.py
- app/services/appointment_request_runtime.py
- tests/test_appointment_context.py
- tests/test_stateful_appointment_context_carryover.py
- docs/P6-F.9.14.38_PENDING_EXACT_HOUR_FRANJA_CONFIRMATION_CONTEXT_SPEC.md

Implemented helpers:

In app/services/appointment_context.py:

- capture_pending_exact_hour_confirmation_context(state, decision)
- apply_pending_exact_hour_confirmation_to_state(state, context)

Behavior added:

When appointment_request_decision.reason is:

requires_exact_hour_franja_confirmation

the runtime now captures appointment_context with:

- fecha_solicitada
- fecha_solicitada_texto
- slots_candidatos
- availability flags
- pending_exact_hour_franja
- pending_exact_hour_text
- pending_exact_hour_requires_confirmation = true

When the patient later replies affirmatively, for example:

- si
- sí
- claro
- de acuerdo
- listo
- está bien
- esta bien
- correcto
- ok
- okay
- vale

and appointment_context.pending_exact_hour_requires_confirmation is true, the runtime now forces:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- franja_solicitada = pending_exact_hour_franja
- state_reason = confirmed_pending_exact_hour_franja

Decision function update:

app/services/appointment_request_runtime.py now respects state.franja_solicitada when it has already been set by pending exact-hour confirmation context.

This prevents the decision function from trying to resolve the franja from the literal confirmation message `si`.

Validation:

Targeted helper tests:

pytest tests/test_appointment_context.py -q

Endpoint/carryover tests:

pytest tests/test_stateful_appointment_context_carryover.py -q

Full suite:

pytest -q

Result:

212 passed

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

The exact-hour confirmation flow is now complete locally.

Elvira can ask the patient to confirm a franja derived from an exact-hour question, persist that pending franja context, and create the AppointmentRequest only after the patient explicitly confirms.

Next recommended block:

P6-F.9.14.39 — Controlled Swagger Explicit Confirmation Dry-Run

Objective:

Validate in production through /test/message-stateful only:

1. Quiero pedir una cita
2. Para el lunes
3. se puede a las 5?
4. si

Expected final result:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- appointment_request_decision.should_persist = true
- appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review
- appointment_request_decision.fecha_solicitada = 2026-06-01
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request != null
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.franja_solicitada = 5:00 p. m.–7:00 p. m.
- persisted_state = ST_CITA_PENDIENTE
- delivery_status = sending_skipped

Do not touch:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation

---

## P6-F.9.14.40 — Add franja_solicitada to ElviraState

Status:

CLOSED / GREEN / PRODUCTION BUG ROOT CAUSE FIXED LOCALLY

Reason:

P6-F.9.14.39 production Swagger dry-run found a 500 error on the fourth message:

`si`

after the flow:

1. Quiero pedir una cita
2. Para el lunes
3. se puede a las 3?
4. si

Production traceback showed:

ValueError: "ElviraState" object has no field "franja_solicitada"

Root cause:

The pending exact-hour confirmation context flow set:

state.franja_solicitada = pending_franja

This worked in local endpoint tests because FakeElviraResult accepted dynamic attributes.

But the real production ElviraState is a Pydantic BaseModel and did not declare the field:

franja_solicitada

Therefore production raised a 500 error.

Files changed:

- app/graph/state.py
- tests/test_appointment_context.py

Fix:

Added to ElviraState:

franja_solicitada: Optional[str] = None

The field is part of deterministic appointment context and is used when the patient confirms a pending exact-hour franja.

Test added:

test_apply_pending_exact_hour_confirmation_works_with_real_elvira_state

Purpose:

Ensure apply_pending_exact_hour_confirmation_to_state works with the real ElviraState Pydantic model, not only FakeElviraResult.

Validation:

pytest tests/test_appointment_context.py -q

GREEN

pytest tests/test_stateful_appointment_context_carryover.py tests/test_appointment_request_runtime_decision.py -q

GREEN

pytest -q

GREEN

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

The production 500 root cause is fixed locally.

Next recommended block:

P6-F.9.14.41 — Controlled Swagger Explicit Confirmation Re-Test

Objective:

Redeploy and re-test through /test/message-stateful only:

1. Quiero pedir una cita
2. Para el lunes
3. se puede a las 3?
4. si

Expected final result:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- appointment_request_decision.should_persist = true
- appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review
- appointment_request_decision.fecha_solicitada = 2026-06-01
- appointment_request_decision.franja_solicitada = 3:00 p. m.–5:00 p. m.
- appointment_request != null
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.franja_solicitada = 3:00 p. m.–5:00 p. m.
- persisted_state = ST_CITA_PENDIENTE
- delivery_status = sending_skipped

Do not touch:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation

---

## P6-F.9.14.41 — Controlled Swagger Explicit Confirmation Re-Test

Status:

PARTIAL GREEN / RESPONSE CONTAMINATION BUG FOUND

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Google Sheets, Telegram, n8n, Calendar, doctor confirmation automation, and therapy/session package tracking were not touched.

Validated clean production sequence:

1. `Quiero pedir una cita`
2. `para maniana`
3. `se puede a las 3?`
4. `si`

Production current date:

fecha_actual_colombia = 2026-06-01

Validated behavior:

Step 1:

- initial appointment copy correct
- nuevo_estado = ST_CITA_FECHA
- persisted_state = ST_CITA_FECHA
- appointment_request = null

Step 2:

- `para maniana` resolved correctly to martes 2 de junio
- fecha_solicitada = 2026-06-02
- fecha_solicitada_texto = martes 2 de junio
- slots_candidatos:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- nuevo_estado = ST_CITA_FRANJA
- persisted_state = ST_CITA_FRANJA
- appointment_request = null

Step 3:

- `se puede a las 3?` triggered exact-hour franja clarification
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 3:00 p. m.–5:00 p. m.
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_confirm_exact_hour_as_slot
- persisted_state = ST_CITA_FRANJA
- appointment_request = null

Step 4:

- `si` was correctly interpreted as confirmation of the pending exact-hour franja
- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- state_reason = confirmed_pending_exact_hour_franja
- franja_solicitada = 3:00 p. m.–5:00 p. m.
- appointment_request_decision.should_persist = true
- appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review
- appointment_request_decision.fecha_solicitada = 2026-06-02
- appointment_request_decision.franja_solicitada = 3:00 p. m.–5:00 p. m.
- AppointmentRequest was created successfully
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.fecha_solicitada = 2026-06-02
- appointment_request.franja_solicitada = 3:00 p. m.–5:00 p. m.
- persisted_state = ST_CITA_PENDIENTE
- delivery_status = sending_skipped

Important validation:

The previous production 500 caused by missing ElviraState.franja_solicitada is fixed.

Root cause of that previous 500 was:

ValueError: "ElviraState" object has no field "franja_solicitada"

This was fixed in P6-F.9.14.40 by adding:

franja_solicitada: Optional[str] = None

to app/graph/state.py and adding a real ElviraState regression test.

New bug found:

The final response for `si` is wrong.

Observed response:

`Hola, qué gusto saludarle. ¿En qué le podemos ayudar hoy en Respirarte?`

Expected response:

Doctor-approved terminal appointment request message:

`Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

Diagnosis:

The deterministic state and persistence are now correct, but the response is contaminated.

Likely flow:

1. process_message initially treats `si` as general and generates a generic greeting.
2. apply_pending_exact_hour_confirmation_to_state(...) later corrects intent/state deterministically.
3. decide_appointment_request_persistence(...) allows AppointmentRequest persistence.
4. AppointmentRequest is created correctly.
5. result.respuesta remains the old generic response from before the deterministic correction.

Conclusion:

The logic and persistence are correct, but the response layer must be guarded after deterministic pending-franja confirmation.

Next recommended block:

P6-F.9.14.42 — Confirmed Pending Franja Response Guard

Objective:

When:

- state_reason = confirmed_pending_exact_hour_franja
- appointment_request_decision.should_persist = true
- appointment_request is created or ready for persistence

then override result.respuesta before save_interaction() and response return with:

`Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

Acceptance criteria:

The same controlled /test/message-stateful flow:

1. Quiero pedir una cita
2. para maniana
3. se puede a las 3?
4. si

must end with:

- appointment_request_decision.should_persist = true
- appointment_request != null
- persisted_state = ST_CITA_PENDIENTE
- respuesta = Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.

Do not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation

Additional bug to address later:

P6-F.9.14.43 candidate — Date Re-selection and Unavailable Date State Guard

Reason:

Earlier test with `para el lunes` on 2026-06-01 resolved to lunes 8 de junio, Corpus Christi.

Elvira detected the holiday correctly in the response, but state incorrectly advanced to ST_CITA_FRANJA / ask_preferred_time.

Expected unavailable-date behavior:

- remain in ST_CITA_FECHA
- next_action = ask_preferred_date
- persisted_state = ST_CITA_FECHA

This should be handled after P6-F.9.14.42.

---

## P6-F.9.14.41 — Controlled Swagger Explicit Confirmation Re-Test

Status:

PARTIAL GREEN / RESPONSE CONTAMINATION BUG FOUND

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Google Sheets, Telegram, n8n, Calendar, doctor confirmation automation, and therapy/session package tracking were not touched.

Validated clean production sequence:

1. `Quiero pedir una cita`
2. `para maniana`
3. `se puede a las 3?`
4. `si`

Production current date:

fecha_actual_colombia = 2026-06-01

Validated behavior:

Step 1:

- initial appointment copy correct
- nuevo_estado = ST_CITA_FECHA
- persisted_state = ST_CITA_FECHA
- appointment_request = null

Step 2:

- `para maniana` resolved correctly to martes 2 de junio
- fecha_solicitada = 2026-06-02
- fecha_solicitada_texto = martes 2 de junio
- slots_candidatos:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- nuevo_estado = ST_CITA_FRANJA
- persisted_state = ST_CITA_FRANJA
- appointment_request = null

Step 3:

- `se puede a las 3?` triggered exact-hour franja clarification
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 3:00 p. m.–5:00 p. m.
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_confirm_exact_hour_as_slot
- persisted_state = ST_CITA_FRANJA
- appointment_request = null

Step 4:

- `si` was correctly interpreted as confirmation of the pending exact-hour franja
- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- state_reason = confirmed_pending_exact_hour_franja
- franja_solicitada = 3:00 p. m.–5:00 p. m.
- appointment_request_decision.should_persist = true
- appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review
- appointment_request_decision.fecha_solicitada = 2026-06-02
- appointment_request_decision.franja_solicitada = 3:00 p. m.–5:00 p. m.
- AppointmentRequest was created successfully
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.fecha_solicitada = 2026-06-02
- appointment_request.franja_solicitada = 3:00 p. m.–5:00 p. m.
- persisted_state = ST_CITA_PENDIENTE
- delivery_status = sending_skipped

Important validation:

The previous production 500 caused by missing ElviraState.franja_solicitada is fixed.

Root cause of that previous 500 was:

ValueError: "ElviraState" object has no field "franja_solicitada"

This was fixed in P6-F.9.14.40 by adding:

franja_solicitada: Optional[str] = None

to app/graph/state.py and adding a real ElviraState regression test.

New bug found:

The final response for `si` is wrong.

Observed response:

`Hola, qué gusto saludarle. ¿En qué le podemos ayudar hoy en Respirarte?`

Expected response:

Doctor-approved terminal appointment request message:

`Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

Diagnosis:

The deterministic state and persistence are now correct, but the response is contaminated.

Likely flow:

1. process_message initially treats `si` as general and generates a generic greeting.
2. apply_pending_exact_hour_confirmation_to_state(...) later corrects intent/state deterministically.
3. decide_appointment_request_persistence(...) allows AppointmentRequest persistence.
4. AppointmentRequest is created correctly.
5. result.respuesta remains the old generic response from before the deterministic correction.

Conclusion:

The logic and persistence are correct, but the response layer must be guarded after deterministic pending-franja confirmation.

Next recommended block:

P6-F.9.14.42 — Confirmed Pending Franja Response Guard

Objective:

When:

- state_reason = confirmed_pending_exact_hour_franja
- appointment_request_decision.should_persist = true
- appointment_request is created or ready for persistence

then override result.respuesta before save_interaction() and response return with:

`Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

Acceptance criteria:

The same controlled /test/message-stateful flow:

1. Quiero pedir una cita
2. para maniana
3. se puede a las 3?
4. si

must end with:

- appointment_request_decision.should_persist = true
- appointment_request != null
- persisted_state = ST_CITA_PENDIENTE
- respuesta = Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.

Do not touch:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation

Additional bug to address later:

P6-F.9.14.43 candidate — Date Re-selection and Unavailable Date State Guard

Reason:

Earlier test with `para el lunes` on 2026-06-01 resolved to lunes 8 de junio, Corpus Christi.

Elvira detected the holiday correctly in the response, but state incorrectly advanced to ST_CITA_FRANJA / ask_preferred_time.

Expected unavailable-date behavior:

- remain in ST_CITA_FECHA
- next_action = ask_preferred_date
- persisted_state = ST_CITA_FECHA

This should be handled after P6-F.9.14.42.

---

## P6-F.9.14.42 — Confirmed Pending Franja Response Guard

Status:

CLOSED / RED-THEN-GREEN / GREEN

Reason:

P6-F.9.14.41 validated that explicit confirmation after an exact-hour franja clarification worked technically, but the response layer was contaminated.

Observed production behavior:

After the flow:

1. `Quiero pedir una cita`
2. `para maniana`
3. `se puede a las 3?`
4. `si`

the runtime correctly produced:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- state_reason = confirmed_pending_exact_hour_franja
- appointment_request_decision.should_persist = true
- appointment_request was created
- franja_solicitada = 3:00 p. m.–5:00 p. m.
- persisted_state = ST_CITA_PENDIENTE

But the final response was wrong:

`Hola, qué gusto saludarle. ¿En qué le podemos ayudar hoy en Respirarte?`

Root cause:

The LLM/general response was generated before deterministic pending-franja confirmation correction.

After apply_pending_exact_hour_confirmation_to_state(...) corrected the state and AppointmentRequest persistence succeeded, result.respuesta still contained the old generic greeting.

Files changed:

- app/main.py
- tests/test_stateful_appointment_context_carryover.py
- docs/P6-F.9.14.42_CONFIRMED_PENDING_FRANJA_RESPONSE_GUARD_SPEC.md

Fix:

In /test/message-stateful, when:

- appointment_request_decision.should_persist is True
- result.state_reason == confirmed_pending_exact_hour_franja

the runtime now overrides result.respuesta before logged_response, save_interaction(), and response return.

Forced response:

`Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

Validation:

Targeted test:

pytest tests/test_stateful_appointment_context_carryover.py::test_stateful_endpoint_persists_after_pending_exact_hour_franja_confirmation -q

GREEN

Related tests:

pytest tests/test_stateful_appointment_context_carryover.py tests/test_appointment_context.py -q

GREEN

Full suite:

pytest -q

GREEN

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

The explicit pending exact-hour franja confirmation flow is now correct locally across state, persistence, and response layer.

Next recommended block:

P6-F.9.14.43 — Controlled Swagger Confirmed Pending Franja Response Re-Test

Objective:

Redeploy and validate in production through /test/message-stateful only:

1. Quiero pedir una cita
2. para maniana
3. se puede a las 3?
4. si

Expected final result:

- appointment_request_decision.should_persist = true
- appointment_request != null
- persisted_state = ST_CITA_PENDIENTE
- franja_solicitada = 3:00 p. m.–5:00 p. m.
- respuesta = Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.

Do not touch:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation

---

## P6-F.9.14.43 — Controlled Swagger Confirmed Pending Franja Response Re-Test

Status:

CLOSED / GREEN / PRODUCTION VALIDATED

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.

Real WhatsApp sending remained disabled.

Google Sheets, Telegram, n8n, Calendar, doctor confirmation automation, and therapy/session package tracking were not touched.

Validated production sequence:

1. `Quiero pedir una cita`
2. `para maniana`
3. `se puede a las 3?`
4. `si`

Production current date:

fecha_actual_colombia = 2026-06-01

Final result for `si`:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- state_reason = confirmed_pending_exact_hour_franja
- fecha_solicitada = 2026-06-02
- fecha_solicitada_texto = martes 2 de junio
- franja_solicitada = 3:00 p. m.–5:00 p. m.
- persisted_state = ST_CITA_PENDIENTE
- appointment_request_decision.should_persist = true
- appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review
- appointment_request_decision.estado_solicitud = pendiente_confirmacion
- appointment_request_decision.fecha_solicitada = 2026-06-02
- appointment_request_decision.franja_solicitada = 3:00 p. m.–5:00 p. m.
- appointment_request was created successfully
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.fecha_solicitada = 2026-06-02
- appointment_request.franja_solicitada = 3:00 p. m.–5:00 p. m.
- delivery_status = sending_skipped

Validated final response:

`Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.`

Conclusion:

The pending exact-hour franja confirmation flow is now production validated through the controlled stateful Swagger endpoint.

The system now correctly handles:

1. exact-hour patient question inside a valid KB-backed franja
2. franja clarification instead of immediate persistence
3. explicit patient confirmation
4. AppointmentRequest creation only after confirmation
5. correct pending human-review status
6. correct terminal patient response

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Known remaining bugs / next candidates:

P6-F.9.14.44 — Unavailable Date State Guard for fecha_cita Turns

Reason:

When `para el lunes` was tested on 2026-06-01, the resolver correctly mapped it to lunes 8 de junio and detected Corpus Christi as a holiday.

The response correctly told the patient that there is no service that day.

However, state incorrectly advanced to:

- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_preferred_time
- persisted_state = ST_CITA_FRANJA

Expected:

- nuevo_estado = ST_CITA_FECHA
- next_action = ask_preferred_date
- persisted_state = ST_CITA_FECHA

This should be handled next, separately.

---

## P6-F.9.14.28 — Exact-Hour Franja Confirmation Response Polish

Status:

CLOSED / RESPONSE-LAYER POLISH / GREEN / READY FOR NEXT CHAT

Reason:

After P6-F.9.14.27, the backend already detected the case where a patient asks for an exact hour inside a valid KB-backed franja, for example:

- `se puede a las 4?`
- `se puede a las 6?`
- `se puede a las 5?`

The decision layer correctly returned:

- should_persist = false
- reason = requires_exact_hour_franja_confirmation
- franja_solicitada = matched KB-backed franja

P6-F.9.14.28 polished the patient-facing response for this case.

Architecture preserved:

- FastAPI remains the runtime authority.
- PostgreSQL remains the source of truth.
- The state machine keeps the patient inside ST_CITA_FRANJA.
- AppointmentRequest is not persisted yet.
- The patient must explicitly confirm the proposed franja before persistence.
- No n8n, Telegram, Google Sheets, real WhatsApp sending, or real /webhook changes were made.

Runtime behavior:

When AppointmentRequest decision reason is:

requires_exact_hour_franja_confirmation

the `/test/message-stateful` layer now forces:

- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_confirm_exact_hour_as_slot
- state_reason = requires_exact_hour_franja_confirmation
- appointment_request = null

Response copy direction:

Elvira now explains formally and clearly that domiciliary care is handled by time windows / franjas, not guaranteed exact hours.

Approved response shape:

"Claro. Le cuento que las atenciones domiciliarias se manejan por franjas, no por una hora exacta garantizada. Para la hora que me indica, puedo registrar como preferencia la franja de 5:00 p. m. a 7:00 p. m. ¿Desea que registre esa franja?"

Important safety rules:

Elvira must not say:

- su cita quedó confirmada
- disponibilidad confirmada
- la doctora la atenderá a esa hora
- hora garantizada

Elvira may say:

- puedo registrar esa franja como preferencia
- ¿Desea que registre esa franja?
- la solicitud se registrará only after confirmation

Files touched:

- app/main.py
- tests/test_stateful_appointment_context_carryover.py

Related mini-fix:

`test_fecha_cita_flow` in tests/test_state_machine.py was made deterministic.

Reason:

The old test used `Mañana en la tarde`, but on the current run tomorrow resolved to Saturday 2026-06-06, so the system correctly blocked the flow with:

- nuevo_estado = ST_CITA_FECHA
- next_action = ask_preferred_date
- state_reason = unavailable_date_guard
- is_weekend = true
- es_dia_disponible = false

The test now uses a valid weekday flow such as:

`Para el viernes en la tarde`

and additionally protects:

- fecha_solicitada is not None
- es_dia_disponible is True
- is_weekend is False
- is_colombia_holiday is False
- slots_candidatos exists

Validation:

Full test suite GREEN.

Latest known test count in this phase:

214 passed

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Conclusion:

P6-F.9.14.28 closes the response-layer gap for exact-hour requests inside valid KB-backed franjas.

The appointment flow now behaves safely:

1. Patient asks for an exact hour.
2. Backend maps it to a KB-backed franja.
3. System does not persist yet.
4. Elvira explains that care is managed by franjas.
5. Elvira asks for explicit confirmation.
6. Only a later confirmation turn may persist AppointmentRequest.

Next recommended block:

P6-F.9.14.29 — Controlled Swagger Exact-Hour Franja Confirmation Dry-Run

Objective:

Validate in production through `/test/message-stateful` only that:

1. After Elvira offers KB-backed slots, patient says:
   `se puede a las 5?`

2. System responds with:
   - nuevo_estado = ST_CITA_FRANJA
   - next_action = ask_confirm_exact_hour_as_slot
   - appointment_request_decision.reason = requires_exact_hour_franja_confirmation
   - appointment_request = null
   - response explains franja/no exact hour guarantee
   - response asks for explicit confirmation

3. Patient then says:
   `sí`

4. System persists AppointmentRequest with the pending franja.

Do not touch real `/webhook`, real WhatsApp sending, Google Sheets, Telegram, n8n, Calendar, or doctor confirmation automation.


---

## P6-F.9.14.29 — Controlled Swagger Exact-Hour Franja Confirmation Dry-Run

Status:

CLOSED / GREEN / PRODUCTION DRY-RUN VALIDATED

Production endpoint validated:

POST /test/message-stateful

Real POST /webhook was not touched.
Real WhatsApp sending remained disabled.
Google Sheets, Telegram, n8n, Calendar, and doctor confirmation automation were not touched.

Validated sequence:

1. Patient started appointment request:

`Quiero pedir una cita`

Result:

- nuevo_estado = ST_CITA_FECHA
- intent = cita
- next_action = ask_preferred_date
- appointment_request = null
- delivery_status = sending_skipped

2. Patient selected valid date:

`para el martes`

Result:

- nuevo_estado = ST_CITA_FRANJA
- intent = fecha_cita
- next_action = ask_preferred_time
- fecha_solicitada = 2026-06-09
- fecha_solicitada_texto = martes 9 de junio
- slots_candidatos:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- appointment_request = null

3. Patient asked for exact hour inside valid franja:

`se puede a las 5?`

Result:

- estado_anterior = ST_CITA_FRANJA
- nuevo_estado = ST_CITA_FRANJA
- intent = hora_cita
- next_action = ask_confirm_exact_hour_as_slot
- state_reason = requires_exact_hour_franja_confirmation
- fecha_solicitada = 2026-06-09
- franja_solicitada in decision = 5:00 p. m.–7:00 p. m.
- hora_solicitada_texto = se puede a las 5?
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request = null

4. Patient confirmed explicitly:

`sí`

Result:

- nuevo_estado = ST_CITA_PENDIENTE
- intent = hora_cita
- next_action = confirm_appointment_request
- state_reason = confirmed_pending_exact_hour_franja
- appointment_request_decision.should_persist = true
- appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review
- appointment_request.estado_solicitud = pendiente_confirmacion
- appointment_request.fecha_solicitada = 2026-06-09
- appointment_request.franja_solicitada = 5:00 p. m.–7:00 p. m.
- delivery_status = sending_skipped

Created AppointmentRequest:

- id_solicitud = SOL-20260605-041942-986633-1429
- estado_solicitud = pendiente_confirmacion
- fecha_solicitada = 2026-06-09
- franja_solicitada = 5:00 p. m.–7:00 p. m.

Conclusion:

The exact-hour franja confirmation flow is production-validated through /test/message-stateful.

Elvira correctly maps an exact hour inside a KB-backed franja, asks for explicit confirmation, avoids premature persistence, and only creates AppointmentRequest after patient confirmation.

Minor future polish candidate:

Avoid duplicated punctuation in the franja confirmation response:

`5:00 p. m. a 7:00 p. m..`

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking


---

## P6-F.9.14.30 — Minor Copy Polish: Exact-Hour Franja Response Punctuation

Status:

CLOSED / GREEN / COMMITTED

Reason:

Production dry-run P6-F.9.14.29 validated the exact-hour franja confirmation flow, but found a minor copy issue:

`5:00 p. m. a 7:00 p. m..`

The duplicated punctuation came from appending a sentence period after a formatted franja that already ends with `p. m.`.

Change:

Adjusted the exact-hour franja confirmation response copy to avoid duplicated punctuation after formatted franja text.

Expected response shape now:

`Para la hora que me indica, puedo registrar como preferencia la franja de 5:00 p. m. a 7:00 p. m. ¿Desea que registre esa franja?`

Validation:

Targeted tests GREEN.
Full suite GREEN.

Scope:

Copy-only polish.

No runtime logic was changed.
No persistence logic was changed.
No AppointmentRequest decision logic was changed.
No state transition logic was changed.

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking


---

## P6-F.9.14.31 — Controlled Swagger Copy Polish Dry-Run

Status:

CLOSED / FUNCTIONAL GREEN / MINOR COPY PUNCTUATION PENDING

Production endpoint validated:

POST /test/message-stateful

Validated sequence:

1. Patient started appointment request:

`Quiero pedir una cita`

Result:

- nuevo_estado = ST_CITA_FECHA
- intent = cita
- next_action = ask_preferred_date
- appointment_request = null
- delivery_status = sending_skipped

2. Patient selected valid date:

`para el martes`

Result:

- nuevo_estado = ST_CITA_FRANJA
- intent = fecha_cita
- next_action = ask_preferred_time
- fecha_solicitada = 2026-06-09
- fecha_solicitada_texto = martes 9 de junio
- slots_candidatos:
  - 3:00 p. m.–5:00 p. m.
  - 5:00 p. m.–7:00 p. m.
- appointment_request = null

3. Patient asked for exact hour inside valid franja:

`se puede a las 5?`

Result:

- estado_anterior = ST_CITA_FRANJA
- nuevo_estado = ST_CITA_FRANJA
- intent = hora_cita
- next_action = ask_confirm_exact_hour_as_slot
- state_reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.should_persist = false
- appointment_request_decision.reason = requires_exact_hour_franja_confirmation
- appointment_request_decision.franja_solicitada = 5:00 p. m.–7:00 p. m.
- appointment_request = null
- delivery_status = sending_skipped

Functional conclusion:

The exact-hour franja confirmation behavior remains correct and production-safe.

Elvira correctly maps `se puede a las 5?` to the KB-backed franja `5:00 p. m.–7:00 p. m.`, keeps the patient in `ST_CITA_FRANJA`, does not persist AppointmentRequest prematurely, and asks for explicit confirmation.

Pending non-blocking copy polish:

Production still shows duplicated punctuation in the response:

`5:00 p. m. a 7:00 p. m.. ¿Desea que registre esa franja?`

This is accepted as a minor non-blocking copy issue.

It does not affect:

- intent routing
- state transition
- AppointmentRequest persistence safety
- franja mapping
- WhatsApp delivery safety
- doctor confirmation boundaries

Decision:

Do not block production activation for this punctuation issue.

Carry this as a minor copy polish candidate for a later cleanup or redeploy verification.

Safety boundaries preserved:

Still not touched:

- real POST /webhook
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking


---

## P6-F.9.22 — Real Webhook Payload Dry-Run

Status:

PARTIAL / REAL BUG FOUND / DO NOT ACTIVATE SENDING

Current production safety:

- `WHATSAPP_SENDING_ENABLED=false`
- `real_whatsapp_sending_allowed=false`
- Real WhatsApp sending has NOT been activated.
- Real `/webhook` can receive Meta-shaped payloads in controlled dry-run.
- No Google Sheets, Telegram, n8n, or Calendar integration is active or required for this block.

What was completed:

- P6-F.9.21 was closed cleanly.
- AppointmentRequest runtime logic was wired into real `POST /webhook`.
- `/webhook` now calls AppointmentRequest runtime decision logic.
- Tests were green after wiring.
- Working tree was clean after commit.

Controlled `/webhook` dry-run result:

A Meta-shaped payload flow was tested directly against:

```txt
POST https://elvira.genflowautomation.com/webhook

Using:

WHATSAPP_SENDING_ENABLED=false

The following turns worked correctly:

Quiero pedir una cita
status = sending_skipped
intent = cita
nuevo_estado = ST_CITA_FECHA
appointment_request = null
appointment_request_decision_reason = skipped_initial_cita_intent
El martes en la tarde
status = sending_skipped
intent = fecha_cita
nuevo_estado = ST_CITA_FRANJA
Elvira offered afternoon franjas.
appointment_request = null
appointment_request_decision_reason = skipped_fecha_cita_waiting_for_time
A las 3
status = sending_skipped
intent = hora_cita
nuevo_estado = ST_CITA_FRANJA
Elvira correctly explained that domiciliary care is handled by franjas, not guaranteed exact hours.
appointment_request = null
appointment_request_decision_reason = requires_exact_hour_franja_confirmation

Critical bug found on turn 4:

Input:

Sí, registre esa franja

Observed result:

status = sending_skipped
intent = hora_cita
nuevo_estado = ST_CITA_PENDIENTE
appointment_request_decision_reason = skipped_unsupported_slot_selection
appointment_request = null

But response said:

Perfecto, queda registrada su solicitud para esa franja. La Dra. D'Aleman le confirmará la cita.

This is unsafe.

Reason:

Elvira tells the patient the request was registered, but no AppointmentRequest was created.

Production implication:

Do NOT activate real WhatsApp sending.

This bug must be fixed before any controlled sending activation.

P6-F.9.23 — Exact-Hour Franja Confirmation Persistence Bugfix

Status:

NEXT / SINGLE-FOCUS BUGFIX ONLY

Goal:

Fix the exact-hour franja confirmation flow so that after:

A las 3

Elvira asks for explicit franja confirmation, and after:

Sí, registre esa franja

the system persists an AppointmentRequest using the previously stored pending franja.

Expected correct result on the confirmation turn:

status = sending_skipped
intent = hora_cita
nuevo_estado = ST_CITA_PENDIENTE
appointment_request != null
appointment_request.estado_solicitud = pendiente_confirmacion
appointment_request.franja_solicitada = 3:00 p. m.–5:00 p. m.

Root-cause hypothesis:

The state likely reaches:

state_reason = confirmed_pending_exact_hour_franja
franja_solicitada = 3:00 p. m.–5:00 p. m.

but decide_appointment_request_persistence(...) still tries to resolve the slot from the current message text:

Sí, registre esa franja

That message does not contain 3, 5, primera, or segunda, so the decision returns:

skipped_unsupported_slot_selection

Correct behavior:

If the state is already marked as:

state_reason = confirmed_pending_exact_hour_franja

and state.franja_solicitada exists, then the decision function must use state.franja_solicitada directly.

It must not try to resolve the franja again from the confirmation text.

Required implementation scope:

Only touch what is necessary:

app/services/appointment_request_runtime.py
tests for the decision function
webhook/stateful tests only if required

Do not touch:

Meta configuration
real WhatsApp sending
/ready
/health
Google Sheets
Telegram
n8n
Calendar
payment workflows
doctor notification workflows
unrelated appointment logic
UI/copy polish unless needed to prevent false registration wording

Required validation sequence:

Add a RED test for:
confirmed_pending_exact_hour_franja + state.franja_solicitada
→ should_persist = true
Implement the minimal fix.
Run targeted tests:
pytest tests/test_appointment_request_runtime_decision.py -q
pytest tests/test_appointment_context.py tests/test_webhook_persistence.py -q
Run full suite:
pytest -q
Commit.
Redeploy.
Validate /test/message-stateful full flow with a fresh phone.
Validate /webhook Meta-shaped payload full flow with a different fresh phone.

Important testing rule:

Do not reuse phones after a failed flow.

Use:

1 complete flow = 1 fresh phone
1 turn = 1 fresh wamid
if a flow fails midway = abandon that phone

Production activation rule:

Do not set:

WHATSAPP_SENDING_ENABLED=true

until this exact bug is fixed and the complete flow passes through real /webhook with Meta-shaped payloads.

Current Working Rule After P6-F.9.22

No more documentation-heavy detours.

The next session must start directly with:

P6-F.9.23 — Exact-Hour Franja Confirmation Persistence Bugfix

No scope expansion.

No production sending.

No Meta changes.

No Google Sheets / Telegram / n8n / Calendar.

Fix the bug, prove it with tests, redeploy, and validate the complete flow through /webhook.


---

## Working Methodology Update — Sprint-Based Execution

Status:

ACTIVE RULE

Decision:

Stop documenting every microphase.

The previous microphase-heavy workflow created too much overhead, slowed down execution, and made the project feel unnecessarily bureaucratic.

New working model:

Work by larger phases and focused sprints.

A sprint should group a coherent technical objective, such as:

- fixing one complete appointment-flow bug
- validating one complete webhook flow
- preparing one production activation step
- closing one deployable capability

Documentation rule:

Do not create long documentation for every microstep.

Document only after a sprint or meaningful phase is completed.

Documentation should be concise and should include:

- what was changed
- what files were touched
- what tests passed
- what production/dry-run validation was completed
- what remains blocked or pending
- whether `WHATSAPP_SENDING_ENABLED` stayed false

SDD remains active, but with less ceremony.

Required validation for conversational flows:

A flow is not accepted unless it is tested through its real effect.

For appointment flows, the success criterion is not only that Elvira answers correctly.

The success criterion is:

```txt
appointment_request != null
and appointment_requests contains the correct row in PostgreSQL

For critical conversational flows, acceptance requires:

focused automated tests
/test/message-stateful full-flow validation when relevant
real /webhook Meta-shaped payload full-flow validation
fresh phone per complete flow
fresh wamid per turn
DB evidence for the expected final effect

Testing rule:

1 complete flow = 1 fresh phone
1 turn = 1 fresh wamid
if a flow fails midway = abandon that phone

Current priority:

Do not expand scope.

Next sprint:

P6-F.9.23 — Exact-Hour Franja Confirmation Persistence Bugfix

Sprint goal:

Fix the bug where Elvira says the appointment request was registered after:

Sí, registre esa franja

but appointment_request remains null.

No production sending activation is allowed until this bug is fixed and the complete flow passes through real /webhook.

Permanent safety rule:

WHATSAPP_SENDING_ENABLED=false

must remain active until an explicitly approved controlled sending activation sprint.


---

## P6-F.9.23 — Exact-Hour Franja Confirmation Persistence Bugfix

Status:

CLOSED / GREEN / COMMITTED / DEPLOYED / WEBHOOK DRY-RUN PASSED / DB VERIFIED

Bug fixed:

The pre-production webhook flow failed after the patient confirmed a pending exact-hour franja.

Validated flow:

1. Quiero pedir una cita
2. El martes en la tarde
3. A las 3
4. Sí, registre esa franja

Previous incorrect behavior:

- Elvira replied as if the request had been registered.
- `appointment_request` remained null.
- `appointment_request_decision_reason = skipped_unsupported_slot_selection`.

Root cause:

The pending exact-hour franja context was not applied when the confirmation turn already reached:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`

The system then tried to resolve the slot again from:

`Sí, registre esa franja`

and failed because the message did not contain 3, 5, primera, segunda, or another concrete slot marker.

Fix implemented:

`apply_pending_exact_hour_confirmation_to_state(...)` now also applies pending exact-hour franja context when the state is already:

- `ST_CITA_FRANJA`
- `ST_CITA_PENDIENTE`

Changed files:

- app/services/appointment_context.py
- tests/test_appointment_context.py
- tests/test_appointment_request_runtime_decision.py

Validation completed:

Local automated tests:

- `pytest tests/test_appointment_context.py tests/test_appointment_request_runtime_decision.py -q`
- `pytest tests/test_webhook_persistence.py -q`
- `pytest -q`

Latest confirmed result:

- 216 passed

Production readiness check:

- `/ready` returned `status = ready`
- `whatsapp_sending_enabled = false`
- `real_whatsapp_sending_allowed = false`

Production webhook dry-run:

Endpoint:

- POST `/webhook`

Payload type:

- Meta-shaped WhatsApp payload

Final webhook result:

- `status = sending_skipped`
- `intent = hora_cita`
- `nuevo_estado = ST_CITA_PENDIENTE`
- `appointment_request_decision_reason = allowed_hora_cita_ready_for_human_review`
- `appointment_request != null`
- `estado_solicitud = pendiente_confirmacion`
- `fecha_solicitada = 2026-06-09`
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `source_interaction_id = wamid.p6f923.923.004`

Production PostgreSQL verification:

Table:

- `appointment_requests`

Verified row:

- `id_solicitud = SOL-20260606-051808-954344-0923`
- `telefono = 573009230923`
- `estado_solicitud = pendiente_confirmacion`
- `fecha_solicitada = 2026-06-09`
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `source_interaction_id = wamid.p6f923.923.004`

Conclusion:

The exact-hour franja confirmation bug is fixed.

Elvira now only says the request was received when `appointment_request != null` and the corresponding row exists in PostgreSQL.

---

## Working Methodology Update — Sprint-Based SDD With E2E Acceptance

Status:

ACTIVE RULE

Decision:

Stop documenting every microphase.

The project will continue using SDD, but with less ceremony and stronger E2E acceptance.

Previous workflow to avoid:

microphase → document → test → commit → document → microphase → more documentation

Current workflow:

sprint / concrete phase → implementation + tests + E2E validation → concise final documentation

Documentation rule:

Do not create long documentation for every microstep.

Document only after a sprint or meaningful phase is completed.

Sprint documentation must be concise and include:

- what was changed
- what files were touched
- what tests passed
- what production or dry-run validation was completed
- what remains blocked or pending
- whether `WHATSAPP_SENDING_ENABLED` stayed false

Conversational acceptance rule:

No conversational flow is accepted unless it is tested through its real expected effect.

For appointment flows, the success criterion is not only that Elvira answers correctly.

The success criterion is:

```txt
appointment_request != null
and appointment_requests contains the correct row in PostgreSQL

For critical conversational flows, acceptance requires:

focused automated tests
/test/message-stateful full-flow validation when relevant
real /webhook Meta-shaped payload full-flow validation
fresh phone per complete flow
fresh wamid per turn
DB evidence for the expected final effect

Testing rule:

1 complete flow = 1 fresh phone
1 turn = 1 fresh wamid
if a flow fails midway = abandon that phone

Permanent safety rule:

WHATSAPP_SENDING_ENABLED=false

must remain active until an explicitly approved controlled sending activation sprint.

Current next sprint:

P6-F.9.24 — Production MVP Activation SDD

Goal:

Prepare the controlled MVP production activation roadmap after P6-F.9.23 closed successfully.

Do not expand scope.

Still out of scope unless explicitly started:

Google Sheets sync
Telegram notification
n8n workflows
Calendar integration
doctor confirmation automation
therapy sessions module


---

## Current Checkpoint — P6-F.9.26 Closed

Status:

CLOSED / GREEN / COMMITTED / PRODUCTION WEBHOOK DRY-RUN REGRESSION APPROVED / REAL SENDING DISABLED

Current repository:

elvira-respirarte-agent

Current branch:

main

Working tree:

clean

Latest closed sprint:

P6-F.9.26 — Final Webhook Dry-Run Regression Pack

Latest validation:

- `pytest -q` → 217 passed
- Production `POST /webhook` Meta-shaped regression pack executed through Swagger
- Real WhatsApp sending remained disabled
- `WHATSAPP_SENDING_ENABLED=false`
- `/ready` confirmed production healthy
- LangSmith production tracing enabled
- PostgreSQL remains final operational source of truth

Latest relevant commits:

- `7e0da8d` Add production MVP activation SDD
- `3fbe528` Add controlled WhatsApp sending activation plan
- Latest commit after P6-F.9.26 documented final webhook dry-run regression results

## P6-F.9.24 — Production MVP Activation SDD

Status:

CLOSED / COMMITTED

Document:

docs/P6-F.9.24_PRODUCTION_MVP_ACTIVATION_SDD.md

Decision:

Production activation must follow controlled sprint-based SDD.

Hard rule:

A conversational response is not trusted unless the expected PostgreSQL effect exists.

For appointment requests:

~~~txt
appointment_request != null
and appointment_requests contains the correct row in PostgreSQL
~~~

## P6-F.9.25 — Controlled WhatsApp Sending Activation Plan

Status:

CLOSED / COMMITTED

Document:

docs/P6-F.9.25_CONTROLLED_WHATSAPP_SENDING_ACTIVATION_PLAN.md

Key decision:

Swagger, LangSmith, and PostgreSQL have different roles.

Evidence hierarchy:

~~~txt
Swagger = manual inspection and safe pre-check surface
/webhook Meta-shaped = realistic WhatsApp ingress validation
LangSmith = observability and traceability evidence
PostgreSQL = final operational source of truth
~~~

Operational rule:

~~~txt
LangSmith explains what happened.
PostgreSQL proves what happened.
~~~

Real sending must not be enabled until a later explicit controlled activation sprint.

## P6-F.9.26 — Final Webhook Dry-Run Regression Pack

Status:

CLOSED / GREEN / APPROVED / COMMITTED

Document:

docs/P6-F.9.26_FINAL_WEBHOOK_DRY_RUN_REGRESSION_PACK.md

Execution surface:

- Production `POST /webhook`
- Meta-shaped payloads through Swagger
- `WHATSAPP_SENDING_ENABLED=false`
- real WhatsApp sending disabled

Production readiness result:

- `status = ready`
- `environment = production`
- `app_version = 0.2.1`
- `whatsapp_sending_enabled = false`
- `real_whatsapp_sending_allowed = false`
- `kb_runtime_enabled = true`
- database configured
- LangSmith tracing enabled
- LangSmith project = `elvira-respirarte-prod`
- OpenAI configured
- WhatsApp configured
- `hard_failures = []`

Approved regression flows:

1. Flow 0 — Readiness Check

Result:

- production app ready
- real sending disabled
- no hard failures

2. Flow 1 — Basic Greeting

Phone:

~~~txt
test-p6f926-greeting-001
~~~

WAMID:

~~~txt
wamid.p6f926.greeting.001
~~~

Result:

- `status = sending_skipped`
- `intent = general`
- `estado_anterior = ST_INIT`
- `nuevo_estado = ST_GENERAL`
- `appointment_request_decision_reason = skipped_non_appointment_intent`
- `appointment_request = null`
- `whatsapp_sending_enabled = false`

Conclusion:

Basic Meta-shaped greeting was accepted safely without appointment side effects.

3. Flow 2 — Appointment Happy Path With Exact-Hour Franja Confirmation

Phone:

~~~txt
test-p6f926-happy-001
~~~

Important correction:

The accepted production happy path has four turns when the patient says `A las 3`, because exact-hour requests require explicit franja confirmation.

Turn sequence:

~~~txt
Quiero pedir una cita
El martes en la tarde
A las 3
Sí, registre esa franja
~~~

Final result:

- `status = sending_skipped`
- `intent = hora_cita`
- `estado_anterior = ST_CITA_FRANJA`
- `nuevo_estado = ST_CITA_PENDIENTE`
- `appointment_request_decision_reason = allowed_hora_cita_ready_for_human_review`
- `appointment_request != null`
- `estado_solicitud = pendiente_confirmacion`
- `fecha_solicitada = 2026-06-09`
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `source_interaction_id = wamid.p6f926.happy.004`
- `whatsapp_sending_enabled = false`

Conclusion:

Appointment request registration is accepted because the patient-facing confirmation response is backed by `appointment_request != null`.

4. Flow 4 — Ambiguous Slot Guard

Phone:

~~~txt
test-p6f926-ambiguous-001
~~~

Turn sequence:

~~~txt
Quiero pedir una cita
El martes en la tarde
En la tarde
~~~

Final result:

- `status = sending_skipped`
- `intent = hora_cita`
- `estado_anterior = ST_CITA_FRANJA`
- `nuevo_estado = ST_CITA_FRANJA`
- `appointment_request_decision_reason = skipped_wrong_state_or_action`
- `appointment_request = null`
- Elvira asks the patient to choose one concrete available franja
- `whatsapp_sending_enabled = false`

Conclusion:

Ambiguous generic time-window reply did not create AppointmentRequest and did not advance to `ST_CITA_PENDIENTE`.

5. Flow 5 — Duplicate WAMID Deduplication

Duplicated WAMID:

~~~txt
wamid.p6f926.ambiguous.003
~~~

Result on repeated payload:

- `status = ignored`
- `reason = duplicate_message`
- `whatsapp_message_id = wamid.p6f926.ambiguous.003`

Conclusion:

Duplicate Meta message was ignored and did not create duplicate operational effects.

6. Flow 6 — Opt-Out Safety Check

Phone:

~~~txt
test-p6f926-optout-001
~~~

WAMID:

~~~txt
wamid.p6f926.optout.001
~~~

Message:

~~~txt
No quiero recibir más mensajes
~~~

Result:

- `status = sending_skipped`
- `intent = optout`
- `estado_anterior = ST_INIT`
- `nuevo_estado = ST_OPTOUT`
- `appointment_request_decision_reason = skipped_non_appointment_intent`
- `appointment_request = null`
- `whatsapp_sending_enabled = false`

Conclusion:

Opt-out is handled safely, without creating AppointmentRequest and without real sending.

## Current Safety Baseline

Do not enable real sending yet.

Still active:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

Do not touch yet unless explicitly started as a later sprint:

- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy sessions module
- public patient traffic
- mass messaging
- marketing templates

## Next Sprint

P6-F.9.27 — Controlled Sending Activation Execution Checklist

Goal:

Prepare the exact execution checklist for enabling real WhatsApp sending only for one controlled internal test phone.

Important:

P6-F.9.27 should still be checklist/execution-prep oriented.

Do not broadly open production.

Do not enable public patient traffic.

Do not activate Google Sheets, Telegram, n8n, Calendar, doctor confirmation automation, or therapy session tracking.

Recommended next steps:

1. Confirm `git status --short` is clean.
2. Confirm `pytest -q` still returns 217 passed.
3. Confirm `/ready` still shows:
   - `whatsapp_sending_enabled = false`
   - `real_whatsapp_sending_allowed = false`
4. Define the exact internal test phone allowed for controlled sending.
5. Define rollback command/procedure before enabling sending.
6. Only then prepare the controlled activation sprint.

## Standing Development Rules

Use sprint-based SDD, not microphases.

Document at sprint/final checkpoint level, not after every tiny step.

For Markdown documentation:

- use one single copy-paste Bash block
- prefer `cat > file <<'EOF'` or `cat >> file <<'EOF'`
- do not use `python - <<'PY'` for Markdown files
- prefer `~~~` fences inside generated Markdown to avoid broken code fences
- avoid fragmented copy-paste blocks

Acceptance for conversational flows:

A flow is accepted only when response behavior and expected PostgreSQL effect are both correct.

For appointment requests, a response such as:

~~~txt
Hemos recibido su solicitud...
~~~

is valid only when:

~~~txt
appointment_request != null
and appointment_requests.estado_solicitud = pendiente_confirmacion
~~~

---

## Current Checkpoint — MVP Real Sending Action Plan Prepared

Status:

P6-F.9.27 ACTION PLAN CREATED / READY FOR NEXT CHAT / REAL SENDING STILL DISABLED

Current repository:

elvira-respirarte-agent

Current branch:

main

Latest closed sprint:

P6-F.9.26 — Final Webhook Dry-Run Regression Pack

Latest prepared sprint:

P6-F.9.27 — Controlled Real Sending MVP Action Plan

Document:

docs/P6-F.9.27_CONTROLLED_REAL_SENDING_MVP_ACTION_PLAN.md

Important discovery:

Meta / WhatsApp infrastructure is already more advanced than initially assumed.

Confirmed by user screenshots and prior real tests:

- Respirarte-WA-bot app exists
- app is Live
- WhatsApp product is configured
- webhook subscription for `messages` is active
- API version v25.0 is selected
- templates exist and are active
- German WhatsApp number is connected
- user already performed real tests with the German number
- Colombian Respirarte number exists in WABA but may still require verification / final readiness confirmation

Current operational conclusion:

It is time to move from documentation/dry-run into controlled real sending tests.

Do not open public patient traffic.

Do not activate broad production.

Next sprint should be practical execution:

P6-F.9.28 — First Controlled Real Sending Test

Recommended first path:

Use the already connected German number first if the Colombian number is still not fully verified.

Then repeat with the Colombian Respirarte number after verification.

Safety baseline:

~~~txt
WHATSAPP_SENDING_ENABLED=false
~~~

Controlled sending may be enabled only temporarily for one internal test phone in P6-F.9.28.

Do not touch yet:

- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy sessions module
- public patient traffic
- mass messaging
- marketing templates

Evidence hierarchy remains:

~~~txt
Swagger = manual inspection and safe pre-check surface
/webhook Meta-shaped = realistic WhatsApp ingress validation
LangSmith = observability and traceability evidence
PostgreSQL = final operational source of truth
~~~

Operational rule:

~~~txt
LangSmith explains what happened.
PostgreSQL proves what happened.
~~~

Next chat starting point:

Project: Elvira / Respirarte
Repo: elvira-respirarte-agent
Branch: main
Status: clean after commit expected

Start directly with:

P6-F.9.28 — First Controlled Real Sending Test

Goal:

Temporarily enable `WHATSAPP_SENDING_ENABLED=true` for one internal controlled test phone, verify real WhatsApp reply, DB evidence, LangSmith trace, then rollback to `WHATSAPP_SENDING_ENABLED=false`.


---

## P6-F.9.28 / P6-F.9.29 — Controlled Real Sending + Slot-Before-Date Guard

Current checkpoint:

P6-F.9.28 — First Controlled Real Sending Test

Status:

PARTIAL GREEN / REAL SENDING VALIDATED / BUG FOUND / ROLLBACK COMPLETED

Validated with internal controlled phone only:

- real WhatsApp inbound reached production `/webhook`
- real WhatsApp outbound response was sent
- `interactions.delivery_status = sent`
- `processed_messages` deduplication row was created
- patient state was persisted correctly
- no real patients were involved
- no public traffic was opened
- `WHATSAPP_SENDING_ENABLED` was rolled back to `false`
- `/ready` confirmed production safety after rollback

Bug found during controlled real sending:

When patient was in:

- `ST_CITA_FECHA`

and sent:

- `Para la de las 5`

the system incorrectly classified it as:

- `intent = general`
- `next_action = answer_general`

and Elvira re-greeted the patient.

This was safe from a persistence perspective, because no `AppointmentRequest` was created, but it was incorrect conversationally.

---

## P6-F.9.29 — Slot Preference Before Date Guard

Status:

CLOSED / GREEN / COMMITTED / PRODUCTION SAFE DRY-RUN GREEN

Commit:

12b12ce Add slot preference before date guard

Validation:

pytest -q → 220 passed

Changed files:

- app/services/intent.py
- app/graph/transitions.py
- app/services/llm.py
- tests/test_intent.py
- tests/test_state_machine.py
- docs/P6-F.9.29_SLOT_PREFERENCE_BEFORE_DATE_GUARD.md

Implemented behavior:

If:

- `estado_actual = ST_CITA_FECHA`
- patient mentions a slot/hour preference before giving a date, e.g.:
  - `Para la de las 5`
  - `Para la de las 3`
  - `La de las 5`

Then:

- `intent = hora_cita`
- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_date_for_slot_preference`
- `state_reason = slot_preference_before_date_guard`
- no `AppointmentRequest` is created
- Elvira does not greet again
- Elvira asks for the missing day/date

Approved response example:

`Claro, con gusto. ¿Me indica por favor para qué día o fecha desea revisar la franja de 5:00 p. m. a 7:00 p. m.?`

Production safe dry-run validated through:

POST `/test/message-stateful`

with real sending disabled.

Validated sequence:

1. `Quiero solicitar una cita`
   - `intent = cita`
   - `nuevo_estado = ST_CITA_FECHA`
   - `persisted_state = ST_CITA_FECHA`
   - `appointment_request = null`
   - `delivery_status = sending_skipped`

2. `Para la de las 5`
   - `estado_anterior = ST_CITA_FECHA`
   - `intent = hora_cita`
   - `nuevo_estado = ST_CITA_FECHA`
   - `next_action = ask_date_for_slot_preference`
   - `state_reason = slot_preference_before_date_guard`
   - `appointment_request = null`
   - `delivery_status = sending_skipped`

Current production safety:

- `WHATSAPP_SENDING_ENABLED=false`
- `/ready` confirmed safe
- no real sending currently active

Next recommended sprint:

P6-F.9.30 — Resume Controlled Real Sending Appointment Flow

Objective:

Deploy/keep the P6-F.9.29 fix in production, then reopen a short controlled real sending window only for one internal phone and validate the appointment flow again.

Still do not touch:

- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy sessions module
- campaigns / marketing
- real patients

---

## P6-F.9.31 — Webhook Exact-Hour State/Copy Guard

Status:

CLOSED / GREEN / COMMITTED

Reason:

During P6-F.9.30 controlled real WhatsApp sending, the message:

`Se puede a las 4?`

from state:

`ST_CITA_FRANJA`

incorrectly produced:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- response copy: `Perfecto, queda registrada su solicitud para esa franja...`

However, no `appointment_requests` row was created.

This created a dangerous product bug: Elvira told the patient that the request was registered while the backend had not persisted an AppointmentRequest.

Root cause:

The exact-hour franja clarification guard existed in the appointment request runtime/persistence layer, but the state machine could already move to:

- `ST_CITA_PENDIENTE`
- `confirm_appointment_request`

before persistence protection ran.

Therefore, the response layer could generate false registration copy too early.

Fix:

The exact-hour guard was moved earlier into the deterministic state transition layer.

Changed file:

- `app/graph/transitions.py`

The state machine now checks:

`is_exact_hour_without_explicit_franja_confirmation(state.mensaje_original)`

before allowing transition to:

`ST_CITA_PENDIENTE`

New expected behavior:

For:

`ST_CITA_FRANJA + "Se puede a las 4?"`

Elvira now returns:

- `intent = hora_cita`
- `nuevo_estado = ST_CITA_FRANJA`
- `next_action = ask_confirm_exact_hour_as_slot`
- `state_reason = requires_exact_hour_franja_confirmation`

and must not say:

`queda registrada`

Tests updated:

- `tests/test_state_machine.py`

The former broad Colombian time preference test was split into:

1. Explicit franja selection still moves to pending:
   - `La primera`
   - `La segunda`
   - `La primera franja`
   - `La segunda franja`

2. Loose exact-hour messages now require franja confirmation:
   - `A las 5 pm`
   - `A las cinco`
   - `Se puede a las 4?`

Validation:

`pytest -q`

Result:

`221 passed`

Safety boundaries preserved:

Still not touched:

- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy sessions
- campaigns
- real patients
- WhatsApp real sending

Production safety:

`WHATSAPP_SENDING_ENABLED` must remain `false` until the next controlled dry-run block.

Next recommended block:

P6-F.9.32 — Controlled Dry-Run Exact-Hour State/Copy Guard

Objective:

Validate the fixed behavior first without real sending.

Recommended validation path:

1. Deploy latest main.
2. Keep `WHATSAPP_SENDING_ENABLED=false`.
3. Confirm `/ready`.
4. Reset internal phone `4917655660163`.
5. Run `/webhook` or the safest available production dry-run surface with Meta-shaped payloads.
6. Validate:
   - `Se puede a las 4?` stays in `ST_CITA_FRANJA`
   - `next_action = ask_confirm_exact_hour_as_slot`
   - response does not contain `queda registrada`
   - `appointment_requests` remains empty until explicit confirmation
7. Only after this passes, consider reopening controlled real sending again.



---

## P6-F.9.34 — Simplify Exact-Hour Guard to Explicit Slot Selection

Status:

CLOSED / GREEN / SWAGGER DRY-RUN VALIDATED / COMMITTED PENDING IF NOT YET PUSHED

Reason:

P6-F.9.32 / P6-F.9.33 left the exact-hour confirmation flow too complex.

The previous approach tried to store a pending exact-hour franja and later allow vague follow-up confirmations such as:

- "sí"
- "esa franja"
- "sí, registre esa franja"

This created unsafe behavior:

- `pending_exact_hour_franja` was not reliable enough as a functional dependency.
- A vague confirmation could move the flow to `ST_CITA_PENDIENTE`.
- Elvira could say "queda registrada" even when `AppointmentRequest` was not actually created.
- Runtime persistence was protected, but state/copy could still lie to the patient.

Final MVP decision:

Exact-hour messages are clarification guards only.

They must not create a pending-franja confirmation flow.

Core product rule:

If the patient asks for a loose exact hour such as:

- "no se podría a las 4?"
- "se puede a las 4?"
- "a las 4"

Elvira must:

- stay in `ST_CITA_FRANJA`
- use `next_action = ask_confirm_exact_hour_as_slot`
- not persist `AppointmentRequest`
- not say "queda registrada"
- explain that domiciliary care is handled by franjas, not guaranteed exact hours
- ask the patient to explicitly choose one available franja

Approved exact-hour guard response:

"Con gusto. Le aclaro que las atenciones domiciliarias se manejan por franjas, no por una hora exacta garantizada. Para continuar, por favor elija una de las franjas disponibles: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Cuál le queda mejor?"

Allowed explicit selections:

- "la primera"
- "la segunda"
- "la primera franja"
- "la segunda franja"

Only explicit selections may move to:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- `appointment_request_decision.should_persist = true`
- `appointment_request != null`

Vague confirmations must not persist:

- "sí"
- "sí, registre esa franja"
- "esa franja"
- "registre esa franja"
- "entiendo, entonces agéndeme esa franja"

Final behavior for vague confirmations after exact-hour guard:

- `nuevo_estado = ST_CITA_FRANJA`
- `persisted_state = ST_CITA_FRANJA`
- `next_action = ask_confirm_exact_hour_as_slot`
- `state_reason = unsupported_slot_selection_guard`
- `appointment_request_decision.should_persist = false`
- `appointment_request_decision.reason = skipped_unsupported_slot_selection`
- `appointment_request = null`
- response asks the patient to choose one of the concrete available franjas
- response must not contain "queda registrada"

Files changed:

- app/main.py
- app/services/appointment_context.py
- app/services/llm.py
- tests/test_appointment_context.py
- tests/test_appointment_request_runtime_decision.py
- tests/test_stateful_appointment_context_carryover.py

Additional hotfix during Swagger dry-run:

`skipped_unsupported_slot_selection` now forces safe state/copy alignment.

Reason:

The decision layer correctly returned:

- `should_persist = false`
- `reason = skipped_unsupported_slot_selection`
- `appointment_request = null`

but the state/copy layer could still return:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- response: "queda registrada..."

This was fixed in `app/main.py` with:

- `_force_unsupported_slot_selection_guard_response(result)`

This guard forces:

- `nuevo_estado = ST_CITA_FRANJA`
- `next_action = ask_confirm_exact_hour_as_slot`
- `state_reason = unsupported_slot_selection_guard`
- safe explicit-franja-selection copy

Validation:

Local full suite:

- `222 passed`

Targeted stateful test after hotfix:

- `5 passed`

Swagger dry-run validated through:

POST `/test/message-stateful`

Real `/webhook` was not touched.

Real WhatsApp sending remained disabled.

Production safety flag remained:

- `WHATSAPP_SENDING_ENABLED=false`

Validated positive flow:

1. `quiero hacer una cita`
2. `para mañana`
3. `no se podria a las 4?`
4. `la primera`

Expected and observed final result:

- `appointment_request_decision.should_persist = true`
- `appointment_request != null`
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `estado_solicitud = pendiente_confirmacion`
- `delivery_status = sending_skipped`

Validated negative flow:

1. `quiero hacer una cita`
2. `para mañana`
3. `no se podria a las 4?`
4. `sí, registre esa franja`

Expected and observed final result:

- `nuevo_estado = ST_CITA_FRANJA`
- `persisted_state = ST_CITA_FRANJA`
- `next_action = ask_confirm_exact_hour_as_slot`
- `state_reason = unsupported_slot_selection_guard`
- `appointment_request_decision.should_persist = false`
- `appointment_request_decision.reason = skipped_unsupported_slot_selection`
- `appointment_request = null`
- response does not say "queda registrada"
- `delivery_status = sending_skipped`

Important operational note:

Dry-run does not send real WhatsApp messages, but `/test/message-stateful` does write test patient state, appointment context, interactions, and AppointmentRequests when persistence is intentionally reached.

Use fresh test phone identifiers for repeated Swagger validation.

Do not reset production DB unless reusing the same test phone and stale test state contaminates the flow.

Safety boundaries preserved:

Still not touched:

- real POST `/webhook`
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy session tracking
- campaigns
- real patients

Current conclusion:

P6-F.9.34 closes the exact-hour ambiguity bug.

Elvira no longer treats vague confirmations like "sí, registre esa franja" as a valid slot selection.

Elvira only registers an appointment request after the patient explicitly chooses one concrete offered franja.

Next recommended step:

If not already done:

1. Commit the hotfix:
   - `Guard unsupported exact-hour slot confirmations`
2. Push main.
3. Keep `WHATSAPP_SENDING_ENABLED=false`.
4. Do not move to controlled real sending until the production activation checklist is explicitly reopened and completed.

## P6-F.9.36 checkpoint — Post-Beta Fixes partial

Status: PARTIAL GREEN checkpoint before moving to a new chat.

### Environment / safety

Production/preproduction healthcheck confirmed:

- service: elvira-respirarte-agent
- environment: production
- app_version: 0.2.1
- WHATSAPP_SENDING_ENABLED=false
- real_whatsapp_sending_allowed=false
- database configured
- LangSmith tracing enabled in project `elvira-respirarte-prod`
- OpenAI configured
- WhatsApp configured
- hard_failures=[]

Post-beta cleanup completed:

- `appointment_requests` cleaned from beta/test rows.
- `interactions` kept intact as debugging evidence.
- `patients` kept intact.
- `processed_messages` kept intact.
- LangSmith traces kept intact.
- No destructive cleanup beyond beta `appointment_requests`.

### P6-F.9.36-A — ST_CITA_PENDIENTE general response guard

Implemented and GREEN.

Problem observed in beta:

- From `ST_CITA_PENDIENTE`, short messages like `Ok` could trigger a new greeting:
  `Hola, qué gusto saludarle...`
- This made Elvira sound as if the conversation had restarted.

Fix implemented:

- Added deterministic response guard in `app/services/response.py`.
- If:
  - `next_action == "answer_general"`
  - `nuevo_estado == "ST_CITA_PENDIENTE"`
  - `intent == "general"`
- Then Elvira responds as follow-up to an already registered request:
  `Con gusto. Su solicitud quedó registrada y la Dra. D'Aleman le confirmará posteriormente. Si necesita algo más, aquí estoy.`

Tests added:

- `tests/test_response_pending_general.py`

Validated:

- `Ok` from `ST_CITA_PENDIENTE` does not re-salute.
- `Muchas gracias` from `ST_CITA_PENDIENTE` does not restart the conversation.
- Targeted tests GREEN.

### P6-F.9.36-B.1 — KB matching logic for Colombian colloquial respiratory language

Implemented and GREEN at logic/test level.

Product decision:

- Elvira does not need to be clinically expert.
- Elvira must understand Colombian/Bogotá-style colloquial patient language and common WhatsApp misspellings well enough to map the message to Respirarte service categories.
- Elvira must not diagnose or suggest specific clinical procedures.
- Technical terms like oximetría, higiene bronquial, sibilancias, etc. are mainly for later doctor-facing/internal reasoning, not current patient-facing explanations.

Current MVP rule:

Patient colloquial language
→ deterministic service/category match
→ safe patient-facing response
→ appointment/consultation request registration
→ Dra. D'Aleman reviews and decides clinically.

Examples that must map to `SRV-01 — Terapia Respiratoria`:

- `Le silva el pecho`
- `Le silba el pecho`
- `Le suena el pecho`
- `El niño está muy mocoso`
- `Necesito que le saquen los mocos al niño`
- `Tiene mucha tos y carraspera`
- `Tiene tos de perro`
- `Hacen destete de oxigeno`

Important: these matches must not fall back to the full service portfolio.

Implemented in `app/services/kb.py`:

- `_normalize()` now removes accents and normalizes whitespace for deterministic KB matching.
- Added search-term helper functions:
  - `_split_search_terms`
  - `_service_matches_search_terms`
  - `_filter_services_by_search_terms`
- Added stricter matching logic:
  - exact term match first
  - single relevant token can match
  - multi-token terms require all relevant tokens
- Fixed search-term splitting bug so real newlines are handled correctly and the letter `n` is not treated as a separator.
- Adjusted service fallback logic to avoid full-portfolio fallback when service-owned `search_terms` exist and no match is found for a non-portfolio question.

Tests updated:

- `tests/test_kb_service.py`

Validated:

- Colombian colloquial respiratory language maps to `Terapia Respiratoria`.
- It does not include unrelated services like:
  - `Curso Profiláctico Materno`
  - `SST Salud Respiratoria Empresarial`
  - `Manejo de Pacientes Traqueotomizados`

Targeted tests GREEN:

- `tests/test_kb_service.py`
- `tests/test_kb_runtime_integration.py`
- `tests/test_response_pending_general.py`

### Important note

The current `search_terms` matching logic is implemented and tested with mocked KB rows.

Next required block:

## P6-F.9.36-B.2 — Persist `search_terms` into real KB schema/import/repository/CSV

Scope for next block:

1. Add `search_terms TEXT` to `kb_services` schema.
2. Add migration / production SQL for existing DB.
3. Update `scripts/import_kb_from_csv.py`:
   - INSERT `search_terms`
   - UPDATE `search_terms` on conflict
   - read `search_terms` from CSV
4. Update `app/repositories/kb_services.py`:
   - include `search_terms` in SELECTs
   - search `search_terms` in `search_services`
5. Update `data/kb/datakbKB_Servicios.csv` with `search_terms` column.
6. Add real repository/import tests if appropriate.
7. Run full targeted KB suite.
8. Keep `WHATSAPP_SENDING_ENABLED=false`.

Do not touch yet:

- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- campaigns
- Colombian number cutover
- real WhatsApp sending
- clinical diagnosis logic

### Next clean starting point

Start next chat at:

P6-F.9.36-B.2 — Persist search_terms into schema/import/repository/CSV

Current state before next chat:

- P6-F.9.36-A GREEN
- P6-F.9.36-B.1 GREEN
- Logic ready
- Production sending disabled
- Need to persist `search_terms` into real KB data path


---

## P6-F.9.36-B.2 — Persist search_terms into real KB

Status:

CLOSED / RED-THEN-GREEN / GREEN

Reason:

P6-F.9.36-B.1 validated Colombian colloquial respiratory matching with mocked/test `search_terms`, but the real production KB did not yet persist or expose `search_terms`.

Implemented changes:

- Added `search_terms TEXT` to `app/db/schema.sql`.
- Added migration draft:
  - `scripts/sql/003_add_kb_services_search_terms.sql`
- Updated `app/repositories/kb_services.py`:
  - `get_active_services()` now selects `search_terms`.
  - `get_service_by_id()` now selects `search_terms`.
  - `search_services()` now selects and searches `search_terms` with `ILIKE`.
- Updated `scripts/import_kb_from_csv.py`:
  - Uses real CSV filenames:
    - `datakbKB_Servicios.csv`
    - `datakbKB_Horarios.csv`
    - `datakbKB_Reglas.csv`
  - Inserts and updates `search_terms`.
- Added canonical versioned CSV:
  - `data/kb/datakbKB_Servicios.csv`
- Added repository/import tests:
  - `tests/test_kb_services_repository.py`
  - `tests/test_import_kb_from_csv.py`

Important product behavior now supported by real KB:

Colombian colloquial respiratory phrases such as:

- `le silva el pecho`
- `le silba el pecho`
- `le suena el pecho`
- `niño mocoso`
- `tos de perro`
- `destete de oxígeno`

can match:

- `SRV-01 — Terapia Respiratoria`

without loading or exposing the full service portfolio.

Safety boundaries preserved:

Still not touched:

- real `/webhook`
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- campaigns
- Colombian production number
- clinical diagnosis logic

Production migration still pending:

The production database still needs this controlled SQL migration before production KB import/runtime validation:

ALTER TABLE kb_services
ADD COLUMN IF NOT EXISTS search_terms TEXT;

Next recommended block:

P6-F.9.36-B.3 — Controlled production migration + KB import validation for `search_terms`

Objective:

1. Apply `scripts/sql/003_add_kb_services_search_terms.sql` to production PostgreSQL.
2. Run/import KB CSV safely.
3. Validate that `kb_services.search_terms` exists and SRV-01 contains colloquial respiratory search terms.
4. Validate via safe runtime surface only.
5. Keep `WHATSAPP_SENDING_ENABLED=false`.

Pending post-beta bugs after this block:

- BUG-1 — pure greeting from ST_INIT must not list the full portfolio.
- BUG-2 — Wednesday single-slot copy must not ask “¿Cuál le sirve mejor?”
- BUG-2B — exact-hour guard must use real `slots_candidatos`.
- Gap — exact-hour follow-up from `ST_CITA_PENDIENTE` must not re-register the request.
- FEAT-1 — capture `servicio_solicitado` in appointment flow remains optional / low priority.


---

## P6-F.9.36-B.3 — Controlled production migration + KB import validation for search_terms

Status:

CLOSED / PRODUCTION VALIDATED / SAFE RUNTIME GREEN

Production actions completed:

- Applied controlled production migration:
  - `ALTER TABLE kb_services ADD COLUMN IF NOT EXISTS search_terms TEXT;`
- Verified in pgweb:
  - `kb_services.search_terms` exists with type `text`.
- Updated production `SRV-01 — Terapia Respiratoria` with Colombian colloquial respiratory `search_terms`.
- Verified in pgweb that:
  - `search_terms IS NOT NULL` for SRV-01.
  - `ILIKE '%le silva%'` returns only SRV-01.

Safe runtime validation:

Endpoint:

- `/test/message-stateful`

Payload:

- telefono: `test-searchterms-b3-01`
- mensaje: `A mi niño le silva el pecho`

Observed result:

- `intent = general`
- `nuevo_estado = ST_GENERAL`
- `kb_used = true`
- `kb_sources = ["kb_services"]`
- `kb_context` included only:
  - `Terapia Respiratoria`
- No full service portfolio was loaded.
- `appointment_request = null`
- `delivery_status = sending_skipped`

Conclusion:

The real production KB now supports Colombian colloquial respiratory language for SRV-01 without exposing the full service portfolio.

Safety boundaries preserved:

Still not touched:

- real `/webhook`
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- campaigns
- Colombian production number
- clinical diagnosis logic

Remaining post-beta bugs:

- BUG-1 — pure greeting from ST_INIT must not list the full portfolio.
- BUG-2 — Wednesday single-slot copy must not ask “¿Cuál le sirve mejor?”
- BUG-2B — exact-hour guard must use real `slots_candidatos`.
- Gap — exact-hour follow-up from `ST_CITA_PENDIENTE` must not re-register the request.
- FEAT-1 — capture `servicio_solicitado` in appointment flow remains optional / low priority.

Next recommended block:

P6-F.9.37 — BUG-1 Pure greeting from ST_INIT must not list full portfolio


## Checkpoint — P6-F.9.42 Pre-LLM Appointment Context Enrichment

Status: PLANNED / SDD FIRST / NO RUNTIME CHANGES YET

After P6-F.9.41, Swagger validation exposed a broader architectural issue in the appointment flow.

Key observation:
- The deterministic resolver can already populate `fecha_solicitada`, `fecha_solicitada_texto`, and `slots_candidatos`.
- However, the state machine / response layer can still keep `next_action=ask_preferred_date`.
- This creates invalid states where Elvira asks for information that is already available.

Representative invalid payload:

```text
intent = cita
next_action = ask_preferred_date
fecha_solicitada = 2026-06-10
fecha_solicitada_texto = miércoles 10 de junio
slots_candidatos = ["3:00 p. m.–5:00 p. m."]

Architectural diagnosis:

This is not primarily a memory problem.
The issue is pipeline ordering.
Appointment context must be loaded and enriched before the final state transition / next_action decision and before the LLM response.

Target pipeline:

/webhook receives message
→ load patient state
→ load active appointment context
→ merge appointment context into ElviraState
→ sanitize input
→ resolve deterministic context
→ classify intent using enriched state
→ state machine decides next_state + next_action
→ appointment_request_decision
→ LLM receives complete final state
→ response generated
→ new context captured
→ persist state/context/appointment request
→ response returned

Critical invariants:

If fecha_solicitada != null and es_dia_disponible == true, final next_action must not be ask_preferred_date.
If an initial intent=cita message contains a valid requested date, Elvira must not ask for the date again.
If ST_CITA_FRANJA has a valid date and slots, an exact hour inside a candidate slot must map to that slot and persist an AppointmentRequest.
Natural confirmations like sí, ok, me sirve, or regístrela in ST_CITA_FRANJA must use pending appointment context instead of being treated as generic conversation.
The LLM must not repair state. It should only verbalize a final consistent state.

Next block:
P6-F.9.42 — Pre-LLM Appointment Context Enrichment Architecture.

Start with Phase A pipeline audit:

grep -R "appointment_context\|load.*context\|restore.*context\|node_resolve_date_context\|node_transition_state\|process_message\|appointment_request_decision\|ask_preferred_date\|ask_preferred_time\|generate.*response\|llm" -n app tests

Do not touch:

real WhatsApp sending
production DB data
Google Sheets
Telegram
n8n
Calendar
campaigns
Colombian production number

WHATSAPP_SENDING_ENABLED remains false.

---

## P6-F.9.42 — Pre-LLM Appointment Context Enrichment

Status:

PARTIALLY CLOSED / PHASE A-B-C GREEN / PHASE D PENDING

Reason for block:

A post-beta appointment flow bug showed that the graph was deciding state transitions before deterministic date context was available.

Observed production-like bug:

Patient message:

`quiero reservar una cita para el miercoles`

The date resolver correctly produced:

- fecha_solicitada = 2026-06-10
- fecha_solicitada_texto = miércoles 10 de junio
- slots_candidatos = ["3:00 p. m.–5:00 p. m."]

But the state machine still returned:

- next_action = ask_preferred_date

Root cause:

The graph pipeline order was wrong.

Previous order:

classify_intent
→ transition_state
→ resolve_date_context
→ load_kb_context

This allowed the state machine to decide with incomplete context.

Corrected order:

classify_intent
→ resolve_date_context
→ transition_state
→ load_kb_context

Completed phases:

### Phase A — Pipeline Audit

Status: CLOSED

Findings:

- The graph was transitioning before resolving date context.
- This caused contradictions such as `next_action=ask_preferred_date` while `fecha_solicitada` was already available.
- Post-hoc guards in `main.py` still exist and should not be expanded blindly.
- Exact-hour/franja logic still has post-hoc behavior in:
  - app/main.py
  - app/services/appointment_request_runtime.py
  - app/services/appointment_context.py
  - app/graph/transitions.py

### Phase B — Contract Tests

Status: PARTIALLY CLOSED

Added/validated contract:

Initial appointment intent with embedded valid date must skip ask_preferred_date.

Expected behavior:

- intent = cita
- fecha_solicitada present
- es_dia_disponible = true
- slots_candidatos not empty
- nuevo_estado = ST_CITA_FRANJA
- next_action = ask_preferred_time
- state_reason = appointment_intent_with_embedded_date

Test:

tests/test_state_machine.py::test_p6f942_embedded_date_in_initial_cita_skips_ask_preferred_date

### Phase C — Pipeline Refactor

Status: CLOSED / GREEN

Changed graph order in:

app/graph/graph.py

New graph order:

sanitize_input
→ classify_intent
→ resolve_date_context
→ transition_state
→ load_kb_context
→ generate_response

Additional state-machine fix:

app/graph/transitions.py now keeps unavailable dates protected.

Rules preserved:

- valid embedded appointment date advances to ST_CITA_FRANJA
- unavailable date, weekend, holiday, or missing slots stays in ST_CITA_FECHA
- no appointment request is persisted from unavailable dates

Copy alignment:

app/services/llm.py now asks explicitly:

`¿Para qué día entre semana le gustaría agendar su cita?`

This keeps ask_preferred_date responses aligned with tests and user intent.

Validation:

- .venv/bin/pytest tests/test_state_machine.py tests/test_llm_date_context.py -q → 32 passed
- .venv/bin/pytest tests/test_date_resolver.py tests/test_intent.py tests/test_state_machine.py tests/test_llm_date_context.py -q → 62 passed
- pytest -q → 238 passed

Changed files in this block:

- app/graph/graph.py
- app/graph/nodes.py
- app/graph/transitions.py
- app/services/llm.py
- tests/test_llm_date_context.py
- tests/test_state_machine.py

Commit to create if not already committed:

git add app/graph/graph.py app/graph/nodes.py app/graph/transitions.py app/services/llm.py tests/test_llm_date_context.py tests/test_state_machine.py
git commit -m "Fix embedded appointment date transition"

### Phase D — Remove or De-emphasize Post-Hoc Guards

Status: PENDING

Do not start Phase D globally yet.

Reason:

There are still appointment persistence and exact-hour behaviors depending on current guards. Removing them prematurely can reopen bugs.

Next debugging target:

P6-F.9.43 — Exact hour inside available slot maps to franja and persists

Follow the same A/B/C/D discipline:

1. Phase A — Audit exact-hour path
2. Phase B — Write contract test RED
3. Phase C — Minimal refactor/fix
4. Phase D — Remove or de-emphasize only the specific post-hoc guard made obsolete by the fix

Next bug to solve:

When patient is in ST_CITA_FRANJA with valid appointment_context and slots_candidatos, and says:

`A las 3`

If 3:00 p. m. falls inside:

`3:00 p. m.–5:00 p. m.`

Expected result:

- intent = hora_cita
- nuevo_estado = ST_CITA_PENDIENTE
- next_action = confirm_appointment_request
- franja_solicitada = "3:00 p. m.–5:00 p. m."
- appointment_request_decision.should_persist = true
- appointment_request != null

Important boundary:

Do not implement P6-F.9.43 before P6-F.9.42 is committed cleanly.

Do not touch:

- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking

Runtime safety remains:

WHATSAPP_SENDING_ENABLED=false


---

## P6-F.9.43 — Exact Hour Inside Available Slot Maps to Franja and Persists

Status:

CLOSED / RED-THEN-GREEN / GREEN / COMMITTED / PHASE D AUDIT-ONLY

Objective:

When the patient is in `ST_CITA_FRANJA`, has valid carried appointment context, and sends an exact hour that maps into a real available slot, the state machine must map that exact hour to the offered franja instead of forcing the old exact-hour clarification guard.

Example:

- Patient state: `ST_CITA_FRANJA`
- Message: `A las 3`
- Context:
  - `fecha_solicitada = 2026-06-17`
  - `fecha_solicitada_texto = miércoles 17 de junio`
  - `slots_candidatos = ["3:00 p. m.–5:00 p. m."]`
  - `es_dia_disponible = true`
  - `is_weekend = false`
  - `is_colombia_holiday = false`

Expected result:

- `intent = hora_cita`
- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- `franja_solicitada = 3:00 p. m.–5:00 p. m.`
- `state_reason = exact_hour_inside_available_slot`

Changed files:

- `app/graph/transitions.py`
- `tests/test_state_machine.py`

Implementation:

`app/graph/transitions.py` now imports and uses:

- `resolve_requested_slot_from_message(...)`

The state machine now calculates `matched_slot` before applying the old loose exact-hour guard.

If:

- previous state is `ST_CITA_FRANJA`
- message contains a loose exact hour
- the hour maps to one of the real `slots_candidatos`

Then the state machine moves directly to:

- `ST_CITA_PENDIENTE`
- `confirm_appointment_request`
- `franja_solicitada = matched_slot`
- `state_reason = exact_hour_inside_available_slot`

The previous fallback remains active:

- loose exact hour without real mappable slot context
- stays in `ST_CITA_FRANJA`
- `next_action = ask_confirm_exact_hour_as_slot`
- `state_reason = requires_exact_hour_franja_confirmation`

Validation:

- New RED contract added:
  - `test_p6f943_exact_hour_inside_available_slot_maps_to_slot_and_confirms`
- Targeted exact-hour tests:
  - `2 passed`
- State machine suite:
  - `26 passed`
- Appointment runtime/carryover targeted suite:
  - `54 passed`
- Full suite:
  - `239 passed`

Phase D result:

Audit-only.

No post-hoc guards were removed.

Reason:

The audit showed that `main.py`, `appointment_request_runtime.py`, and `appointment_context.py` still contain runtime guards used by existing covered flows:

- `requires_exact_hour_franja_confirmation`
- `ask_confirm_exact_hour_as_slot`
- pending exact-hour franja confirmation
- unsupported slot selection
- exact-hour follow-up after an already registered request

These guards remain necessary until a later dedicated cleanup/refactor block with explicit contract tests.

Safety boundaries preserved:

Still not touched:

- real `/webhook`
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session tracking


---

## 2026-06-12 — P6-F.9.35 / P6-F.9.36 Post-Beta Appointment Flow Checkpoint

### Current repository state

- Branch: `main`
- Latest known test status: `246 passed`
- `WHATSAPP_SENDING_ENABLED=false`
- Real WhatsApp sending must remain disabled.
- Do not touch real patients.
- Do not enable production sending until explicit checklist/review.

### Development workflow preference

For the next session:

- Work step by step.
- Use SDD/spec-first for each block.
- Use `sed`, `grep`, `cat`, `pytest`, Swagger/logs.
- Do not ask for `git diff`; if inspection is needed, use `sed` or `grep`.
- Do not use Python heredocs for documentation patches.
- Prefer small copy-paste friendly Bash blocks.
- Keep scope narrow and commit only after tests/validation.

---

## P6-F.9.35 — Post-beta 24h analysis summary

A controlled beta was analyzed using LangSmith traces and Swagger/runtime outputs with 3 real numbers:

- Nabit
- Dra. D'Aleman
- third test number

The appointment flow worked in several core cases, but multiple post-beta issues were identified and classified.

### BUG-4 — Closed

Problem:

Messages that were actually complaints/questions but contained numbers were being interpreted as slot selections.

Example:

```txt
pero usted dijo que solo habia atencion los miercoles de 3 a 6

Risk:

The system could create an AppointmentRequest from a complaint/question because resolve_requested_slot_from_message matched numbers as if they were time-slot selections.

Fix implemented:

Added _NON_SELECTION_SIGNALS inside resolve_requested_slot_from_message.
Location: app/services/appointment_request_runtime.py
Result: complaints/questions containing numbers no longer match as slot selections and no longer create AppointmentRequest.

Status: CLOSED.

BUG-3 — Closed

Problem:

The exact-hour/franja clarification response was hardcoded with generic weekday slots:

3:00 p. m. a 5:00 p. m.
5:00 p. m. a 7:00 p. m.

This was wrong when runtime slots_candidatos contained a different real candidate slot.

Fix implemented:

_build_exact_hour_franja_confirmation_response is now dynamic.
It uses real franja or slots_candidatos.
It no longer blindly prints generic L/M/J/V slots.

Status: CLOSED.

Product decision — Wednesday special logic removed

Decision:

The previous special Wednesday logic was removed.

Current product rule:

All weekdays now share the same two visible appointment slots:
- 3:00 p. m.–5:00 p. m.
- 5:00 p. m.–7:00 p. m.

This means:

No special Wednesday single-slot rule anymore.
Wednesday is aligned with the rest of weekdays.
This simplifies deterministic scheduling and avoids inconsistent copy.

Files already modified in the previous session:

app/services/calendar_service.py
data/kb/datakbKB_Horarios.csv
Pending production KB sync

PostgreSQL runtime KB is still outdated and may still show old Wednesday text such as:

Miércoles: 15:00–18:00
Solo Slot 1: 15:00–17:00

This must be updated manually in pgweb → Query tab.

Run:

UPDATE kb_schedules
SET
    day_name = 'Lunes a viernes incluyendo miércoles',
    end_time = '19:00',
    max_patients = 2,
    notes = 'Máximo 2 pacientes por día. Franja visible al paciente: 2 horas. Slot 1: 15:00–17:00. Slot 2: 17:00–19:00. Buffer de 60 min entre citas por desplazamiento en Bogotá.'
WHERE schedule_id = 'HOR-02';

UPDATE kb_rules
SET
    rule_description = 'Cada cita ocupa una franja de 2 horas. Máximo 2 citas por día todos los días hábiles. Slots visibles L/M/X/J/V: 15:00–17:00 y 17:00–19:00. Elvira puede presentar estas franjas como opciones de preferencia, pero no confirma la cita.'
WHERE rule_id = 'RULE-008';

After running the SQL:

Validate in Swagger that kb_context no longer shows the old Wednesday-specific rule.

Expected KB behavior:

Lunes a viernes incluyendo miércoles
15:00–19:00
Slot 1: 15:00–17:00
Slot 2: 17:00–19:00
Critical pending bug — "la de las 5"
Problem

Message:

la de las 5

Current bad runtime behavior:

state_reason = registered_request_exact_hour_followup
appointment_request_decision.should_persist = false
reason = skipped_unsupported_slot_selection
appointment_request = null

But response says something like:

Su solicitud ya quedó registrada...

This is wrong and critical.

Core rule violated:

Elvira must never say "queda registrada" unless an AppointmentRequest was actually created.
Root cause

In app/services/appointment_request_runtime.py, inside resolve_requested_slot_from_message, second_patterns does not capture:

la de las 5

Existing pattern like:

r"\b(a las )?5\b"

is not enough for the phrase:

la de las 5
Required fix

Open:

app/services/appointment_request_runtime.py

Find:

first_patterns
second_patterns

Add patterns such as:

r"\bde las \d\b"
r"\bla de las \d\b"

and equivalent word-based patterns if needed.

For the current product rule:

3:00 p. m.–5:00 p. m. = first slot
5:00 p. m.–7:00 p. m. = second slot

Expected result:

mensaje = "la de las 5"
slots_candidatos = ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."]
matched_slot = "5:00 p. m.–7:00 p. m."
appointment_request_decision.should_persist = true
appointment_request != null

Recommended next block:

P6-F.9.36 — Fix "la de las 5" + KB validation + commit

Suggested order:

Inspect with:
grep -n "first_patterns\|second_patterns\|registered_request_exact_hour_followup\|skipped_unsupported_slot_selection" app/services/appointment_request_runtime.py
sed -n '1,260p' app/services/appointment_request_runtime.py
Add RED test for "la de las 5".

Likely test files:

tests/test_appointment_request_runtime_decision.py
tests/test_stateful_appointment_context_carryover.py
Patch resolve_requested_slot_from_message.
Run:
pytest -q tests/test_appointment_request_runtime_decision.py
pytest -q tests/test_stateful_appointment_context_carryover.py
pytest -q
Validate Swagger stateful flow.
Run pgweb KB SQL update.
Validate Swagger kb_context.
Commit pending changes.
Pending uncommitted files from previous session

At session close, these files were modified but not committed:

M app/main.py
M app/services/appointment_request_runtime.py
M tests/test_appointment_request_runtime_decision.py
M tests/test_stateful_appointment_context_carryover.py

Before committing, ensure:

pytest -q

is still green.

Suggested commit message after fixing "la de las 5" and validating KB:

Fix exact-hour slot followup and sync appointment KB rules
Backlog post-beta
BUG-1 — Still open

Problem:

A greeting from ST_INIT can launch the full portfolio unexpectedly.

Example:

Hola buen día

Bad behavior:

Elvira may list services without being asked.

Severity:

Medium

Do not prioritize before fixing "la de las 5".

FEAT-1 — Optional / low priority

Feature:

Capture the type of therapy/service mentioned by the patient during appointment flow.

Example:

quiero una cita para terapia respiratoria

Possible future behavior:

servicio_solicitado = "Terapia Respiratoria"

Severity:

Low

Not required for the immediate stabilization block.

Current architectural rule

Keep this architecture intact:

KB = source of truth
Python = deterministic validation
State machine = safe transitions
LLM = wording / limited interpretation only
DB = auditable persistence

The LLM must not decide:

availability
schedules
slot validity
persistence
final appointment confirmation

Elvira only registers appointment requests for human review. Dra. D'Aleman confirms final appointments.

Out of scope for the next block

Do not touch:

Google Sheets
Telegram
n8n
Calendar
campaigns
real WhatsApp sending
WHATSAPP_SENDING_ENABLED=true
doctor confirmation automation
therapy/session packages
real patients

