# Elvira Respirarte Agent

Elvira is the conversational assistant for **Respirarte**, a respiratory therapy service led by Dra. D'Aleman.

This project is a Python-based agentic system designed to support controlled WhatsApp patient interactions through a deterministic, testable, auditable and production-ready architecture.

---

## Current Production MVP Status

Elvira is currently preparing for controlled production activation with the official Respirarte Colombian WhatsApp number.

Latest confirmed local validation:

```txt
214 passed
```

Current validated capabilities:

* Patient-facing WhatsApp conversational core.
* Deterministic intent and state handling.
* KB-backed responses about services, schedules, and operational rules.
* Safe appointment request intake.
* AppointmentRequest persistence in PostgreSQL.
* Explicit franja confirmation before request persistence.
* Human review and confirmation by Dra. D'Aleman.
* No automatic appointment confirmation.

Current safety mode:

* Real WhatsApp sending is disabled by default.
* `WHATSAPP_SENDING_ENABLED=false`.
* `/test/message-stateful` is the validated dry-run endpoint.
* Real `/webhook` activation/review is pending.
* Google Sheets, Telegram, n8n, and Calendar are not required for the initial controlled MVP launch.
* Appointment requests are registered for human review, not automatically confirmed.

Current production-preparation phase:

```txt
P6-F.9.18 — Production Activation Context Reconciliation
```

Next block:

```txt
P6-F.9.19 — Production Activation Checklist
```

---

## Production Safety Rule

Do not enable real WhatsApp sending or modify the real `/webhook` behavior until the production activation checklist and webhook readiness review are completed.

Elvira must never confirm appointments automatically.

---

## Core Architecture Principle

```txt
WhatsApp transports.
FastAPI receives.
PostgreSQL persists.
LangGraph orchestrates.
State machine decides.
KB informs.
LLM writes.
Logs audit.
Tests protect.
```

The LLM does not decide:

* intent
* state
* next action
* opt-out logic
* escalation logic
* deduplication
* business rules
* appointment availability
* KB truth
* appointment confirmation

Those responsibilities remain deterministic, testable and auditable.

---

## Current Architecture

Current implemented flow:

```txt
WhatsApp Cloud API
→ FastAPI webhook
→ WhatsApp payload parser
→ Message ID deduplication
→ Patient repository
→ Load current patient state
→ Input sanitization
→ Deterministic intent classifier
→ Pure state machine
→ Runtime KB context loader
→ LangGraph orchestration
→ LLM response generation
→ Save interaction
→ Update patient state
→ Safety-controlled WhatsApp Send API
→ LangSmith tracing
```

Current safety behavior:

```txt
WHATSAPP_SENDING_ENABLED=false
→ Webhook can receive messages
→ Elvira processes messages
→ State is loaded from PostgreSQL
→ Message is deduplicated
→ Response is generated
→ Interaction is logged
→ Patient state is persisted
→ WhatsApp reply is NOT sent
→ API response status is sending_skipped
```

---

## Project Status

Current repository:

* GitHub: `github.com/CRUX-75/elvira-respirarte-agent`
* Branch: `main`
* Visibility: Private
* Deployment: Easypanel on Hetzner
* Stable domain: `https://elvira.genflowautomation.com`
* Production health endpoint: `/health`
* Production readiness endpoint: `/ready`
* Production dry-run endpoint: `/test/message-stateful`
* Meta webhook endpoint: `/webhook`
* Current production safety mode: `WHATSAPP_SENDING_ENABLED=false`
* KB runtime: `KB_RUNTIME_ENABLED=true`
* LangSmith project: `elvira-respirarte-prod`

Current important boundary:

Real `/webhook` behavior and real WhatsApp sending must not be activated until the controlled production activation checklist and webhook readiness review are completed.

---

## Main Stack

* Python 3.12+
* FastAPI
* LangGraph
* Pydantic
* SQLAlchemy with raw SQL repositories
* PostgreSQL
* OpenAI for response wording only
* LangSmith for tracing
* WhatsApp Cloud API
* pytest
* Easypanel
* Hetzner

---

## Repository Structure

The repository uses:

```txt
elvira-respirarte-agent/
├── app/
├── docs/
├── tests/
├── scripts/
├── data/
├── requirements.txt
├── Dockerfile
└── README.md
```

Important rule:

Do not create a `src/` folder.
This repository uses `app/`.

---

## Main Production Components

### FastAPI

FastAPI owns the production runtime.

Responsibilities:

* receive WhatsApp webhook payloads
* verify Meta webhook challenge
* parse incoming WhatsApp messages
* deduplicate messages by `whatsapp_message_id`
* load and persist patient state
* execute deterministic routing and state transitions
* call the LLM only for wording
* persist interactions
* control real WhatsApp sending through feature flags

### PostgreSQL

PostgreSQL is the operational source of truth.

Main responsibilities:

* patients
* interactions
* processed messages
* runtime KB data
* AppointmentRequest persistence

Appointment requests are not Google Sheets-first objects.

Correct direction:

```txt
AppointmentRequest internal model
→ AppointmentRequestService
→ AppointmentRequestRepository
→ PostgreSQL source of truth
→ future human-visible inbox or notification adapter, optional
```

### Knowledge Base

Runtime KB source:

```txt
PostgreSQL
```

The KB informs answers about:

* services
* schedules
* operational rules
* appointment-related restrictions
* price communication boundaries
* urgency and escalation guidance

The KB does not decide state transitions.

### LLM

The LLM is used for response wording only.

It must not decide business logic, availability, state, appointment confirmation, opt-out, escalation, or persistence.

---

## Appointment Request Rules

Elvira may collect appointment request preferences.

Elvira may register:

* patient phone
* patient name when available
* requested date
* requested franja
* service requested
* relevant observations
* source interaction ID

Elvira must not:

* confirm appointments automatically
* promise exact appointment times
* approve or reject appointments
* reschedule confirmed appointments automatically
* cancel appointments automatically
* claim real availability without human confirmation

Human confirmation by Dra. D'Aleman remains required.

---

## Current Appointment Flow

Controlled MVP appointment flow:

```txt
Patient requests appointment
→ Elvira asks for preferred date
→ Elvira validates date deterministically
→ Elvira blocks weekends and Colombian holidays
→ Elvira offers KB-backed afternoon franjas
→ Patient selects or confirms a franja
→ AppointmentRequest is persisted in PostgreSQL
→ Elvira sends a final request-registration message
→ Dra. D'Aleman reviews and confirms manually
```

Important:

Elvira registers the request.
Elvira does not confirm the appointment.

---

## Current Production Scope

Included in the controlled MVP:

* Official WhatsApp Business Cloud API preparation.
* Patient-facing answers about services, schedules, and rules.
* Safe appointment request intake.
* AppointmentRequest persistence in PostgreSQL.
* Final patient-facing request-registration message.
* Human confirmation by Dra. D'Aleman.
* Production monitoring through logs, database checks, and LangSmith traces.

Explicitly out of scope for the initial controlled MVP:

* Google Sheets appointment handoff.
* Telegram doctor notification.
* n8n appointment orchestration.
* Calendar availability integration.
* Automatic appointment confirmation.
* Automatic rescheduling.
* Automatic cancellation.
* Payment workflows.
* Marketing campaigns.
* Mass outbound messaging.

---

## Environment Variables

Required app identity:

```env
APP_ENV=local
APP_NAME=elvira-respirarte-agent
```

Required for OpenAI:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

Required for LangSmith:

```env
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=elvira-respirarte-local
```

Production LangSmith project:

```env
LANGSMITH_PROJECT=elvira-respirarte-prod
```

Required for WhatsApp Cloud API:

```env
WHATSAPP_VERIFY_TOKEN=your_meta_verify_token_here
WHATSAPP_API_URL=https://graph.facebook.com/v19.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_TOKEN=your_whatsapp_cloud_api_token_here
```

Required for PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
```

Required safety flags:

```env
WHATSAPP_SENDING_ENABLED=false
KB_RUNTIME_ENABLED=true
```

Important:

`WHATSAPP_SENDING_ENABLED=false` means the webhook can receive and process messages, but Elvira will not send real WhatsApp replies.

Only set this to `true` during an explicitly approved controlled sending activation block.

Never commit `.env`.

Only `.env.example` should be versioned.

---

## Local Development

Create and activate virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "elvira-respirarte-agent"
}
```

---

## Production Health Checks

Production health endpoint:

```bash
curl https://elvira.genflowautomation.com/health
```

Production readiness endpoint:

```bash
curl https://elvira.genflowautomation.com/ready
```

Current expected production readiness:

```txt
status = ready
environment = production
whatsapp_sending_enabled = false
kb_runtime_enabled = true
database = configured
LangSmith project = elvira-respirarte-prod
OpenAI configured = true
WhatsApp configured = true
hard_failures = []
real_whatsapp_sending_allowed = false
```

---

## WhatsApp Webhook

Meta verifies the webhook through:

```txt
GET /webhook
```

The endpoint returns the raw `hub.challenge` as `text/plain` when:

* `hub.mode=subscribe`
* `hub.verify_token` matches `WHATSAPP_VERIFY_TOKEN`

Production webhook:

```txt
https://elvira.genflowautomation.com/webhook
```

Webhook subscribed field:

```txt
messages
```

Incoming WhatsApp messages are handled through:

```txt
POST /webhook
```

Current safety boundary:

Real `/webhook` behavior must be reviewed before controlled production activation.

---

## Test Endpoints

Safe stateful production dry-run endpoint:

```txt
POST /test/message-stateful
```

This endpoint:

* uses real patient state logic
* exercises the real LangGraph flow
* persists interactions
* updates patient state
* can validate AppointmentRequest behavior
* does not send real WhatsApp messages

This is the validated dry-run surface before real WhatsApp activation.

---

## Testing

Run all tests:

```bash
pytest -q
```

Current confirmed local validation:

```txt
214 passed
```

Do not commit if tests fail.

---

## Production DB Inspection

pgweb is available for controlled inspection of the production PostgreSQL database.

Production database:

```txt
elvira_respirarte_prod
```

pgweb may be used to inspect:

* patients
* interactions
* processed_messages
* appointment_requests
* kb_services
* kb_schedules
* kb_rules

Operational rule:

pgweb is for inspection and controlled SQL validation.
Do not use pgweb for casual production edits.

---

## Development Rules

* Work step by step.
* Follow SDD for non-trivial changes.
* Keep the state machine deterministic.
* Keep the LLM out of control decisions.
* Keep tests passing before every commit.
* Keep `.env` private.
* Keep WhatsApp as transport only.
* Prefer small, auditable changes.
* Do not use memory to decide state.
* Do not reactivate real WhatsApp sending casually.
* All production sends must be controlled by `WHATSAPP_SENDING_ENABLED`.
* Any new database write must be auditable.
* Any message from Meta must be traceable by `whatsapp_message_id`.
* PostgreSQL serves runtime KB data.
* KB informs, but the state machine decides.
* The LLM writes, but does not control the flow.
* Medical urgency must be detected deterministically before relying on wording.
* OPTOUT must win from any state.
* If `nuevo_estado = ST_OPTOUT`, patient `opt_out` must persist as true.
* Do not use `git diff` as an operational validation step.
* Validate documentation changes with `sed`, `grep`, `pytest`, and `git status`.

---

## SDD Protocol

For non-trivial changes, follow:

```txt
1. SPEC
2. DESIGN, if needed
3. CONTRACT, if needed
4. TESTS
5. IMPLEMENTATION
6. VALIDATION
7. DOCS UPDATE
8. COMMIT
```

Production activation work must remain documented and auditable.

---

## Current Baseline

Current stable baseline:

```txt
Branch: main
Tests: 214 passed
Production sending: disabled
Dry-run endpoint: /test/message-stateful
Real webhook review: pending
Next block: P6-F.9.19 — Production Activation Checklist
```

This is the current stable foundation for Elvira as a production-oriented conversational agent preparing for controlled WhatsApp activation.

---

## Manual Rollback Checklist

If any issue appears during controlled production activation preparation:

1. Keep real WhatsApp sending disabled:

```env
WHATSAPP_SENDING_ENABLED=false
```

2. If unsafe traffic reaches production:

```txt
Disable or unsubscribe the Meta webhook temporarily.
```

3. If the deployed version behaves unexpectedly:

```txt
Redeploy the previous stable commit from Easypanel or Git.
```

4. If the app must be stopped immediately:

```txt
Stop the Easypanel service temporarily.
```

5. For incident review:

```txt
Search interactions by whatsapp_message_id.
Search processed_messages by whatsapp_message_id.
Check the patient record in patients by telefono.
Review the corresponding LangSmith run in elvira-respirarte-prod.
```

Rollback priority:

```txt
Stop real sending first.
Preserve auditability.
Investigate by whatsapp_message_id.
Only redeploy after identifying the failing commit or behavior.
```