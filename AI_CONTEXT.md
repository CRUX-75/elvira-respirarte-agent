# AI_CONTEXT.md — Elvira Respirarte Agent

## Purpose

This file is the operational context for AI-assisted development on the Elvira / Respirarte project.

It exists so ChatGPT or any coding assistant can understand the repository structure, architecture decisions, documentation hierarchy, and current phase without repeatedly rediscovering the repo from scratch.

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

The following phases are closed and committed:

- P6-F.9.2 — AppointmentRequest internal model spec
- P6-F.9.3 — AppointmentRequest model
- P6-F.9.4 — lifecycle validation spec
- P6-F.9.5 — lifecycle validator
- P6-F.9.6 — factory spec
- P6-F.9.7 — factory implementation and progress handoff

Last known test baseline:

```text
44 passed
Current Phase

Active phase:

P6-F.9.8 — AppointmentRequestService Contract

Objective:

Define the contract of the service that will orchestrate AppointmentRequest creation, lifecycle transitions, prevention of duplicate active requests, and preservation of id_solicitud during contraoffers and rescheduling.

This phase is specification-only.

No implementation code before the contract spec is reviewed and accepted.

P6-F.9.8 Scope

In scope:

Define AppointmentRequestService responsibilities.
Define duplicate active request prevention.
Define id_solicitud preservation.
Define future service operations.
Define service boundaries.
Keep deterministic ownership in Python.

Out of scope:

Database implementation
Google Sheets integration
Calendar integration
Telegram notifications
n8n workflows
WhatsApp sending changes
therapy session package tracking
remaining sessions tracking
executed sessions tracking
automatic appointment confirmation
Development Protocol

This project follows SDD: Specification-Driven Development.

No vibecoding.

For non-trivial changes, follow this order:

SPEC
DESIGN
CONTRACT
TESTS
IMPLEMENTATION
VALIDATION
DOCS UPDATE

Before creating production code, define the relevant specification and expected tests.

Working Rules

Work step by step.

Do not dump huge files unnecessarily.

Prefer copy-paste friendly Bash commands.

Prefer cat and sed for file creation and modification.

Avoid repeating large code blocks already created in the session.

Follow DRY principles.

Keep code clean, robust, typed, and testable.

Before adding new files, verify whether the target folder already exists.

For this repo, use app/, never src/.

Environment Note

If pytest fails with:

ModuleNotFoundError: No module named 'fastapi'

this is an environment/dependency issue, not necessarily a code regression.

Check:

echo $VIRTUAL_ENV
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest

