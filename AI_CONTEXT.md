# AI_CONTEXT.md — Elvira Respirarte Agent

## Purpose

This file is the operational context for AI-assisted development on the Elvira / Respirarte project.

It exists so ChatGPT or any coding assistant can understand the repository structure, architecture decisions, documentation hierarchy, and current phase without repeatedly rediscovering the repo from scratch.

This file is not public-facing documentation. It is a working context file.

---

## Repository Structure

Current root structure:

- Dockerfile
- README.md
- requirements.txt
- app/
- data/
- docs/
- scripts/
- tests/
- P6F_CONTROLLED_SENDING_CHECKLIST.md
- P6F_DRY_RUN_VALIDATION.md
- P6F_PRODUCTION_ENV_ALIGNMENT.md
- P6F_TEMPLATES_STRATEGY.md
- P6F_WHATSAPP_MANAGER_CHECKLIST.md

Current Python structure:

- app/__init__.py
- app/config.py
- app/db/__init__.py
- app/db/session.py
- app/graph/__init__.py
- app/graph/graph.py
- app/graph/nodes.py
- app/graph/state.py
- app/graph/transitions.py
- app/main.py
- app/models/__init__.py
- app/models/message.py
- app/models/whatsapp.py
- app/repositories/__init__.py
- app/repositories/interactions.py
- app/repositories/kb_rules.py
- app/repositories/kb_schedules.py
- app/repositories/kb_services.py
- app/repositories/logs.py
- app/repositories/patients.py
- app/repositories/processed_messages.py
- app/services/__init__.py
- app/services/calendar_service.py
- app/services/date_resolver.py
- app/services/intent.py
- app/services/kb.py
- app/services/llm.py
- app/services/readiness.py
- app/services/response.py
- app/services/safety.py
- app/services/tracing.py
- app/services/whatsapp.py

Do not create a src/ folder. This repository uses app/.

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

## Current Architecture

Main stack:

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

Current app structure:

- app/models/ contains Pydantic models.
- app/graph/ contains LangGraph state and transitions.
- app/services/ contains deterministic services and response/LLM orchestration.
- app/repositories/ contains database persistence access.
- app/db/ contains SQLAlchemy engine/session setup.
- tests/ contains the validation suite.

---

## Current Pydantic Model Style

Current models are simple Pydantic BaseModel classes.

Existing examples:

- app/models/message.py
- app/models/whatsapp.py
- app/graph/state.py

Style conventions:

- Use BaseModel + Field.
- Use Optional from typing.
- Use Literal where useful for constrained string values.
- Avoid overengineering with custom validators unless needed.
- Keep models readable and explicit.
- Prefer defaults that match the current state-machine conventions.
- Timezone context defaults to America/Bogota.

---

## Canonical Documentation Map

The current documentation hierarchy for appointment request work is:

- docs/P6-F.8_APPOINTMENT_REQUEST_CONTAINMENT_AND_HANDOFF.md
- docs/P6-F.9.1_SOLICITUDES_CITA_OPERATIONAL_CONTRACT.md
- docs/P6-F.9.2_APPOINTMENT_REQUEST_INTERNAL_MODEL.md [next document to create]

Meaning:

- P6-F.8 defines the architectural decision: Elvira does not schedule appointments automatically; it contains the request and prepares human handoff.
- P6-F.9.1 defines the operational contract for Solicitudes_Cita, the human review inbox for Dra. D'Aleman.
- P6-F.9.2 must define the internal Python model AppointmentRequest, aligned with the validated Solicitudes_Cita contract, before implementing persistence or Google Sheets integration.

P6-F.9.1_SOLICITUDES_CITA_OPERATIONAL_CONTRACT.md is the source of truth for the fields and lifecycle that AppointmentRequest must represent.

Do not duplicate or rewrite P6-F.8 or P6-F.9.1 inside P6-F.9.2.

P6-F.9.2 should only translate the validated operational contract into an internal Python model specification.

---

## Current Phase

Active phase:

P6-F.9.2 — AppointmentRequest internal model

First objective:

Define the internal Python model AppointmentRequest, aligned 1:1 with the validated Solicitudes_Cita contract, without implementing Google Sheets yet.

---

## Previous Closed Block

P6-F.9.1 was closed with doctor validation.

Dra. D'Aleman validated the appointment request flow.

Confirmed doctor feedback:

1. The flow reflects how she wants to manage appointment requests.
2. The state distinction is correct.
3. She normally offers alternatives when a requested slot is unavailable.
4. Contraoffer / renegotiation should remain in the same appointment request, not create a new request.
5. Add an additional state: reagendada.
6. The request table must show:
   - punto o dirección del domicilio
   - servicio solicitado

The later idea of tracking treatment session packages must not be mixed into Solicitudes_Cita.

That belongs to a future separate module, likely:

- Plan_Terapia
- Sesiones_Terapia

---

## Appointment Request Design Decision

Solicitudes_Cita must not be treated as a Google Sheets-first object.

Correct direction:

AppointmentRequest internal model
→ future repository/service layer
→ future Google Sheets adapter / human inbox
→ future Telegram notification, optional

Google Sheets is only the visible operational inbox for the doctor.

The source of truth for appointment request rules must remain in Python.

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

Before creating production code, define the relevant specification and expected tests.

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

When possible, add small tests immediately after creating a model.

---

## Current Next Step

Create the SDD specification document first:

docs/P6-F.9.2_APPOINTMENT_REQUEST_INTERNAL_MODEL.md

Purpose:

Define the internal Python model AppointmentRequest, aligned 1:1 with the validated Solicitudes_Cita contract, without implementing Google Sheets yet.

After the spec is approved, create:

- app/models/appointment_request.py
- tests/test_appointment_request_model.py

The model should include:

- AppointmentRequestStatus
- AppointmentRequestSource
- AppointmentRequest
- basic field validation
- timestamps
- alignment with Solicitudes_Cita
