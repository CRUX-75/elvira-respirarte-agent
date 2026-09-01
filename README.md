# Elvira Respirarte Agent

Elvira is the conversational assistant for **Respirarte**, a respiratory therapy service led by Dra. D'Aleman.

This project is a Python-based agentic system designed to support real WhatsApp patient interactions through a deterministic, testable, auditable, and production-ready architecture.

This repository contains the real production implementation for Respirarte.
It is not a separate Demo system or a multitenant SaaS. It is the current
production foundation from which future business-specific implementations may
be scoped after commercial validation.

---

## Current Production Status

Elvira is currently active in production with the official Respirarte WhatsApp number.

Current repository:

```txt
Repository: github.com/CRUX-75/elvira-respirarte-agent
Branch: main
Deployment: Easypanel on Hetzner
Production domain: https://elvira.genflowautomation.com
```

Latest confirmed production baseline:

```txt
HEAD: f689bf339cdc6708077170183b854d5ba8bc5c18
Full suite: 890 passed
Production: stable
```

Current validated production capabilities:

* Patient-facing WhatsApp conversational core.
* Real Meta webhook reception.
* Real outbound WhatsApp replies.
* Voice-note interaction through STT and TTS.
* Message deduplication by `whatsapp_message_id`.
* Deterministic intent and state handling.
* Persistent patient state in PostgreSQL.
* Runtime KB-backed responses about services, schedules, and operational rules.
* Deterministic Colombian date resolution.
* Weekend and Colombian holiday blocking.
* KB-driven appointment slot generation.
* Safe appointment request intake.
* AppointmentRequest persistence in PostgreSQL.
* Human review inbox through Google Sheets.
* Explicit franja confirmation before request persistence.
* Human confirmation by Dra. D'Aleman.
* No automatic appointment confirmation.
* WhatsApp read receipts.
* WhatsApp typing indicator.
* Minimum natural typing delay before sending fast responses.
* Deterministic opt-out from any state.
* LangSmith tracing and production auditability.
* Human escalation when required.
* Controlled proactive contact through approved WhatsApp templates.
* Normal conversational continuation after proactive contact.
* Delivery and read lifecycle tracking.

Current production configuration:

```env
WHATSAPP_SENDING_ENABLED=true
KB_RUNTIME_ENABLED=true
GOOGLE_SHEETS_ENABLED=true
WHATSAPP_API_URL=https://graph.facebook.com/v25.0
```

Current production block:

```txt
P6-F.11 — Patient Reactivation via WhatsApp: CLOSED
PRE-DEMO H1-H5 Governance & Compliance Hardening: CLOSED
Production validation: GREEN
Controlled proactive flow: validated end-to-end
Campaign behavior: single send, no resend, completed
```

Current operational direction:

```txt
Stable Respirarte production operation
→ commercial market validation
→ no additional development before demand validation
→ future business-specific adaptations only after a validated customer need
```

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
* weekend or holiday availability
* persistence eligibility

Those responsibilities remain deterministic, testable, and auditable.

---

## Current Architecture

Current production flow:

```txt
WhatsApp Cloud API
→ FastAPI webhook
→ WhatsApp payload parser
→ Message ID deduplication
→ Mark message as read
→ Show typing indicator
→ Patient repository
→ Load current patient state
→ Input sanitization
→ Deterministic intent classifier
→ Pure state machine
→ Runtime KB context loader
→ LangGraph orchestration
→ LLM response generation
→ AppointmentRequest runtime
→ Save interaction
→ Update patient state
→ Send WhatsApp reply
→ Mark message as processed
→ LangSmith tracing
```

Current appointment architecture:

```txt
FECHA → KB → SLOTS → CONTEXT
HORA → CONTEXT → SLOT SELECTION → APPOINTMENT_REQUEST
```

Meaning:

* A date turn resolves date, availability, and candidate slots deterministically.
* The result is stored as `appointment_context`.
* A time or slot turn consumes the stored context.
* A time or slot turn must not contradict previously resolved availability.
* AppointmentRequest persistence happens only after a valid slot selection.
* The context is cleared only after successful request persistence.

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
* Google Sheets human review adapter
* pytest
* Easypanel
* Hetzner

---

## Repository Structure

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

```txt
Do not create a src/ folder.
This repository uses app/.
```

---

## Main Production Components

### FastAPI

FastAPI owns the production runtime.

Responsibilities:

* receive WhatsApp webhook payloads
* verify Meta webhook challenge
* parse incoming WhatsApp messages
* deduplicate messages by `whatsapp_message_id`
* mark valid inbound messages as read
* trigger the WhatsApp typing indicator
* load and persist patient state
* execute deterministic routing and state transitions
* call the LLM only for wording
* persist interactions
* control real WhatsApp sending through feature flags
* invoke AppointmentRequest runtime logic
* expose controlled internal human-review endpoints

### PostgreSQL

PostgreSQL is the operational source of truth.

Main responsibilities:

* patients
* patient state
* patient opt-out
* appointment context
* interactions
* processed messages
* runtime KB data
* AppointmentRequest persistence
* human review lifecycle data

Appointment requests are not Google Sheets-first objects.

Correct direction:

```txt
AppointmentRequest internal model
→ AppointmentRequestService
→ AppointmentRequestRepository
→ PostgreSQL source of truth
→ Google Sheets human review inbox
```

Google Sheets is an operational review surface.

It is not the lifecycle source of truth.

### Google Sheets

Google Sheets acts as a human-visible inbox for Dra. D'Aleman.

Current operational tab:

```txt
Solicitudes_Cita
```

The doctor may review requests there, but backend state and lifecycle rules remain in PostgreSQL and Python.

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

## WhatsApp Production Experience

Elvira currently uses the official WhatsApp Cloud API.

For each valid inbound patient message:

```txt
Inbound message received
→ message deduplicated
→ message marked as read
→ typing indicator shown
→ Elvira processes the request
→ minimum typing visibility is enforced for very fast responses
→ reply is sent
```

Current UX behavior:

* blue read receipts are visible
* typing dots are visible
* fast responses wait long enough to avoid an unnatural instant-reply effect
* longer responses are not delayed unnecessarily
* typing-indicator failure must not break the main webhook flow

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
* claim final availability without human confirmation

Human confirmation by Dra. D'Aleman remains required.

---

## Current Appointment Schedule

Current production schedule:

* Monday, Tuesday, Thursday, and Friday:
  * 15:00–17:00
  * 17:00–19:00
* Wednesday:
  * 15:00–18:00
* Saturday:
  * unavailable
* Sunday:
  * unavailable
* Colombian holidays:
  * unavailable unless explicitly overridden in a future controlled phase

Important product rule:

```txt
The system adapts to the doctor's schedule.
The doctor is not forced into uniform slots because the code prefers them.
```

---

## Current Appointment Flow

```txt
Patient requests appointment
→ Elvira asks for or resolves the preferred date
→ Elvira validates the date deterministically
→ Elvira blocks weekends and Colombian holidays
→ Elvira offers KB-backed afternoon franjas
→ Patient selects or confirms a franja
→ AppointmentRequest is persisted in PostgreSQL
→ Request is written to the Google Sheets human review inbox
→ Elvira sends the request-registration message
→ Dra. D'Aleman reviews and confirms manually
```

Important:

```txt
Elvira registers the request.
Elvira does not confirm the appointment.
```

Terminal patient copy after successful registration:

```txt
Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.
```

---

## Appointment Context Contract

`appointment_context` is the operational package calculated after a valid date turn.

Expected minimum shape:

```json
{
  "flow": "appointment_request",
  "fecha_solicitada": "2026-07-22",
  "fecha_solicitada_texto": "miércoles 22 de julio",
  "slots_candidatos": ["3:00 p. m.–6:00 p. m."],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null
}
```

For `hora_cita` turns, this context is authoritative for:

* `fecha_solicitada`
* `fecha_solicitada_texto`
* `slots_candidatos`
* `es_dia_disponible`
* `is_weekend`
* `is_colombia_holiday`
* `colombia_holiday_name`

---

## Slot Selection Rules

If there is one candidate slot:

* soft confirmations may be accepted
* examples:
  * `sí`
  * `ok`
  * `esa`
  * `esa franja`
  * `me sirve`
  * `registre esa`

If there are multiple candidate slots:

* the patient must choose explicitly
* valid examples:
  * `la primera`
  * `la segunda`
  * `la de las 3`
  * `la de las 5`
  * `de 3 a 5`
  * `de 5 a 7`

Ambiguous replies must not persist an AppointmentRequest when multiple slots exist.

---

## Exact-Hour Behavior

Elvira must not promise exact arrival times.

If the patient asks for an exact hour inside a valid franja:

* explain that care is handled by time windows
* map the hour to the corresponding available franja when possible
* ask for confirmation
* do not persist until the patient confirms the franja

Final confirmation remains with Dra. D'Aleman.

---

## Opt-Out

Opt-out is deterministic and has priority from any conversational state.

Examples of opt-out intent:

```txt
No quiero recibir más mensajes.
No me escriban más.
Salir.
Dar de baja.
```

Expected behavior:

```txt
Any state
→ opt-out intent detected
→ nuevo_estado = ST_OPTOUT
→ patient opt_out = true
→ future outbound campaigns must exclude that phone
```

Critical rule:

```txt
OPTOUT must win from any state.
```

Google Sheets or campaign exports must never override PostgreSQL opt-out state.

---

## Human Review

Supported internal human-review actions:

* confirm
* request missing data
* propose alternative
* reschedule
* cancel
* close

Valid AppointmentRequest states:

* nueva
* pendiente_datos
* pendiente_confirmacion
* confirmada
* reagendada
* cancelada
* cerrada

Forbidden legacy states:

* pendiente
* contraoferta
* completada

A proposed alternative remains represented operationally as:

```txt
pendiente_confirmacion
```

The internal human-review endpoint is protected by an admin token.

It is not required for the current manual Google Sheets review workflow.

---

## Current Production Scope

Included:

* official WhatsApp Business Cloud API
* real Meta webhook
* real WhatsApp sending
* read receipts
* typing indicator
* natural minimum typing delay
* patient-facing service and schedule answers
* safe appointment request intake
* AppointmentRequest persistence in PostgreSQL
* Google Sheets human review inbox
* deterministic Colombian holidays
* human confirmation by Dra. D'Aleman
* production logging
* LangSmith tracing
* opt-out persistence

Not currently implemented or intentionally out of scope:

* automatic appointment confirmation
* automatic rescheduling
* automatic cancellation
* Calendar synchronization
* Telegram notifications
* n8n-owned appointment logic
* payment workflows
* uncontrolled mass campaigns
* uncontrolled real-patient outreach

---

## Environment Variables

Required app identity:

```env
APP_ENV=production
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
LANGSMITH_PROJECT=elvira-respirarte-prod
```

Required for WhatsApp Cloud API:

```env
WHATSAPP_VERIFY_TOKEN=your_meta_verify_token_here
WHATSAPP_API_URL=https://graph.facebook.com/v25.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_TOKEN=your_whatsapp_cloud_api_token_here
WHATSAPP_SENDING_ENABLED=true
```

Required for PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
```

Required for runtime KB:

```env
KB_RUNTIME_ENABLED=true
```

Required for Google Sheets human review inbox:

```env
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_SHEETS_SOLICITUDES_CITA_TAB=Solicitudes_Cita
GOOGLE_SERVICE_ACCOUNT_JSON=your_service_account_json_here
```

Important:

* Never commit `.env`.
* Only `.env.example` should be versioned.
* Production values belong in Easypanel environment variables.
* `WHATSAPP_SENDING_ENABLED=false` remains the emergency stop for outbound replies.

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
  "service": "elvira-respirarte-agent",
  "version": "0.2.1"
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

Expected production characteristics:

```txt
environment = production
whatsapp_sending_enabled = true
kb_runtime_enabled = true
database = configured
OpenAI = configured
WhatsApp = configured
Google Sheets = configured when enabled
hard_failures = []
```

---

## WhatsApp Webhook

Meta verification:

```txt
GET /webhook
```

Production webhook:

```txt
https://elvira.genflowautomation.com/webhook
```

Webhook subscribed field:

```txt
messages
```

Inbound WhatsApp messages:

```txt
POST /webhook
```

The webhook currently handles:

* payload extraction
* no-message status callbacks
* required-field validation
* deduplication
* patient loading
* stateful processing
* read receipt
* typing indicator
* AppointmentRequest runtime
* WhatsApp sending
* interaction persistence
* patient state persistence
* processed-message persistence

---

## Test Endpoints

Safe stateful endpoint:

```txt
POST /test/message-stateful
```

This endpoint:

* uses real patient state logic
* exercises the real LangGraph flow
* persists interactions
* updates patient state
* can validate AppointmentRequest behavior
* never sends a WhatsApp message

It remains useful for controlled debugging, but production behavior has already been validated through the real Meta webhook.

---

## Testing

Run all tests:

```bash
pytest -q
```

Latest confirmed full-suite baseline:

```txt
890 passed
HEAD: f689bf339cdc6708077170183b854d5ba8bc5c18
```

This baseline includes the P6-F.11 closure, PRE-DEMO H1-H5 hardening,
voice interaction, proactive WhatsApp contact, callback observability and
the natural spirometry grounding regression fix.

Before future non-trivial releases, run the relevant targeted tests and full suite when appropriate.

---

## Production DB Inspection

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

```txt
pgweb is for inspection and controlled SQL validation.
Do not use pgweb for casual production edits.
```

---

## Development Rules

* Work step by step.
* Follow SDD for non-trivial changes.
* Keep the state machine deterministic.
* Keep the LLM out of control decisions.
* Keep `.env` private.
* Keep WhatsApp as transport only.
* Prefer small, auditable changes.
* Do not use memory to decide state.
* Any new database write must be auditable.
* Any message from Meta must be traceable by `whatsapp_message_id`.
* PostgreSQL serves runtime KB data.
* KB informs, but the state machine decides.
* The LLM writes, but does not control the flow.
* Medical urgency must be detected deterministically.
* OPTOUT must win from any state.
* If `nuevo_estado = ST_OPTOUT`, patient `opt_out` must persist as true.
* Google Sheets is a human review adapter, not the source of truth.
* Elvira registers appointment requests but does not confirm them.
* Do not run uncontrolled outbound campaigns.
* Production behavior changes must remain auditable and reversible.

---

## SDD Protocol

For non-trivial changes:

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

Small operational UX changes may use a reduced controlled workflow when the scope is narrow, observable, and reversible.

---

## Controlled Production Rollout

Current recommended rollout:

```txt
Phase 1
→ Dra. D'Aleman shares the official number gradually
→ real patients contact Elvira
→ requests appear in Google Sheets
→ doctor confirms manually

Phase 2
→ monitor real conversations
→ review unexpected wording or edge cases
→ fix only real blockers

Phase 3
→ publish the number on landing page and social profiles
→ start organic social content
→ drive qualified traffic to WhatsApp
```

Do not begin with uncontrolled mass outbound messaging.

---

## Manual Rollback Checklist

If any production issue appears:

1. Stop outbound replies:

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

---

## Current Baseline

```txt
Branch: main
Production webhook: active
Real WhatsApp sending: active
Graph API: v25.0
KB runtime: active
Google Sheets human review inbox: active
Read receipts: active
Typing indicator: active
Minimum typing delay: active
Appointment confirmation: human-only
Opt-out: deterministic and persistent
Voice interaction: active
Human escalation: active
Controlled proactive contact: validated
Latest confirmed full suite: 890 passed
P6-F.11: CLOSED
PRE-DEMO H1-H5: CLOSED
Current phase: commercial market validation
```

Elvira is operating as a controlled production conversational system for
Respirarte. No separate Demo implementation is required before validating
demand for future business-specific implementations.
