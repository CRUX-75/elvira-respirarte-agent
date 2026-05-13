# Elvira Respirarte Agent

Elvira is the conversational assistant for **Respirarte**, a respiratory therapy service led by Dra. D'Aleman.

This project is a Python-based agentic system designed to replace the previous n8n prototype with a deterministic, testable, auditable and production-ready architecture.

The current version focuses on a controlled conversational core for WhatsApp patient interactions, with FastAPI receiving Meta webhooks, PostgreSQL providing operational persistence, LangGraph orchestrating the flow, deterministic logic controlling intent/state transitions, a runtime Production DB Inspection

pgweb has been activated for the Elvira production PostgreSQL database.

Purpose:

- inspect production tables safely
- validate KB records after imports
- review interactions during dry-runs
- verify processed_messages deduplication
- check patient state and opt_out persistence
- support incident review without modifying application logic

Current pgweb database:

elvira_respirarte_prod

Validated through pgweb:

- kb_rules visible and active
- obsolete `RULE-003 teleconsulta` removed from production
- obsolete `RULE-007 appointment_confirmation` removed from production
- `RULE-008 appointment_slot_policy` updated to present candidate preference windows without confirming the appointment
- obsolete `HOR-05 Teleconsulta` removed from production
- `HOR-03` Saturday note simplified to reflect the current domiciliary flow
- kb_services, kb_schedules, patients, interactions and processed_messages accessible

Operational rule:

pgweb is for inspection and controlled SQL validation.
Do not use pgweb for casual production edits.
KB edits remain managed through the agreed KB import/update process.

Knowledge Base informing answers, and the LLM limited to response wording.

---

## Project Status

Current repository:

- GitHub: `github.com/CRUX-75/elvira-respirarte-agent`
- Branch: `main`
- Visibility: Private
- Deployment: Easypanel on Hetzner
- Stable domain: `https://elvira.genflowautomation.com`
- Meta webhook: `https://elvira.genflowautomation.com/webhook`
- Webhook subscribed field: `messages`
- Current phase: Sprint P6-F.8 completed — Appointment Request Containment & Human Handoff design sealed
- Next phase: P6-F.9 — Appointment Request Persistence & Human Review Handoff

Current production safety state:

- Previous n8n workflow: OFF
- FastAPI app deployed on Easypanel
- PostgreSQL operational on Easypanel
- pgweb activated for production PostgreSQL inspection
- WhatsApp sending controlled by `WHATSAPP_SENDING_ENABLED`
- Current safety mode: `WHATSAPP_SENDING_ENABLED=false`
- KB runtime enabled: `KB_RUNTIME_ENABLED=true`
- LangSmith active in project: `elvira-respirarte-prod`
- Production status endpoint: `/ready`
- Production status: `ready`
- Hard failures: none

Completed:

- Sprint P1 — Local Python core completed
- Sprint P2-A — LangSmith tracing completed
- Sprint P2-B — LangGraph structural flow completed
- Sprint P2-C — LLM response generation completed
- Sprint P2-D — Documentation and repo baseline completed
- Sprint P3 — WhatsApp Cloud API integration completed
- Sprint P3-G — Webhook safety flag and message metadata tracing completed
- Sprint P4 — PostgreSQL persistence layer completed
- Sprint P5-A — KB schema tables created
- Sprint P5-B — KB repositories created
- Sprint P5-C — CSV import script created and KB loaded into PostgreSQL production
- Sprint P5-D — Deterministic KB service created
- Sprint P5-E — KB context integrated into runtime flow
- Sprint P5-F — KB routing optimization completed
- Sprint P5-G — KB answer quality and minimal guardrails completed
- Sprint P6-A — Production Safety Checklist completed
- Sprint P6-B — Failure Handling v1 completed
- Sprint P6-C — Medical & Response Safety Boundaries completed
- Sprint P6-D — Production Dry-Run Validation completed
- Sprint P6-E — Pre-Go-Live Final Gate completed
- Sprint P6-F.7.1 — Colombian Appointment Time Preference Context fix completed and production dry-run validated
- Sprint P6-F.8 — Appointment Request Containment completed and production-validated
- GitHub private repo created
- `.gitignore` configured
- `.env` confirmed as not versioned
- P6-F operational runbook created: `docs/P6-F_CONTROLLED_SENDING_ACTIVATION_PLAN.md`
- P6-F.8 canonical decision document created: `docs/P6-F.8_APPOINTMENT_REQUEST_CONTAINMENT_AND_HANDOFF.md`
- P6-F.7.1 completed: Colombian appointment-time preference context fixed and validated in production dry-run
- P6-F.7.1 result: natural patient replies such as `La de 5 de la tarde` are now classified deterministically as `hora_cita`
- P6-F.7.1 safety: appointment-time preference moves to `ST_CITA_PENDIENTE`, loads `kb_schedules + kb_rules`, and does not confirm real availability
- P6-F.8 completed: relative appointment dates are resolved and repeated in human language, weekends and Colombian 2026 public holidays are blocked deterministically, and valid dates expose afternoon candidate preference windows only
- P6-F.8 production validation: `/test/message-stateful` confirmed correct handling for `Mañana` and `El domingo`
- P6-F.8 bugfix: weekday references such as `El domingo` inside `ST_CITA_FECHA` are now classified as `fecha_cita`, not `horarios`
- P6-F.8 architectural decision: Elvira does not require external calendar integration in the current phase; the next operational layer will use `Solicitudes_Cita` plus human review by Dra. D'Aleman
- P6-F production default rule: `WHATSAPP_SENDING_ENABLED=false` and `real_whatsapp_sending_allowed=false`
- Current full test baseline: 76/76 tests passing

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

The LLM does not decide:

intent
state
next action
opt-out logic
escalation logic
deduplication
business rules
appointment availability
KB truth

Those responsibilities remain deterministic, testable and auditable.

Current Architecture

Current implemented flow:

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

Current safety behavior:

WHATSAPP_SENDING_ENABLED=false
→ Webhook receives message
→ Elvira processes message
→ State is loaded from PostgreSQL
→ Message is deduplicated
→ Response is generated
→ Interaction is logged
→ Patient state is persisted
→ WhatsApp reply is NOT sent
→ API response status is sending_skipped
Tech Stack

Current stack:

Python 3.12+
FastAPI
Pydantic
Pydantic Settings
LangGraph
LangChain
LangChain OpenAI
LangSmith
OpenAI model for wording
PostgreSQL
SQLAlchemy
httpx
pytest
python-dotenv
Uvicorn

Deployment stack:

Easypanel
Hetzner
GitHub private repository
WhatsApp Cloud API
Meta webhook verification
PostgreSQL service
LangSmith production tracing
Repository Structure
elvira-respirarte-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── graph/
│   │   ├── state.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── transitions.py
│   ├── services/
│   │   ├── intent.py
│   │   ├── response.py
│   │   ├── llm.py
│   │   ├── kb.py
│   │   ├── calendar_service.py
│   │   ├── tracing.py
│   │   ├── safety.py
│   │   └── whatsapp.py
│   ├── repositories/
│   │   ├── patients.py
│   │   ├── interactions.py
│   │   ├── processed_messages.py
│   │   ├── kb_services.py
│   │   ├── kb_schedules.py
│   │   └── kb_rules.py
│   ├── models/
│   │   ├── message.py
│   │   └── whatsapp.py
│   └── prompts/
│       └── elvira_system.txt
├── tests/
│   ├── test_intent.py
│   ├── test_state_machine.py
│   ├── test_kb_service.py
│   ├── test_kb_runtime_integration.py
│   ├── test_calendar_service.py
│   ├── test_p6c_prompt_safety.py
│   └── test_webhook_persistence.py
├── scripts/
│   └── import_kb_from_csv.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
Environment Variables

Create a local .env file based on .env.example.

Required for app identity:

APP_ENV=local
APP_NAME=elvira-respirarte-agent

Required for LangSmith:

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=elvira-respirarte-local

Production LangSmith project:

LANGSMITH_PROJECT=elvira-respirarte-prod

Required for OpenAI:

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

Required for WhatsApp Cloud API:

WHATSAPP_VERIFY_TOKEN=your_meta_verify_token_here
WHATSAPP_API_URL=https://graph.facebook.com/v19.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_TOKEN=your_whatsapp_cloud_api_token_here

Required for PostgreSQL:

DATABASE_URL=postgresql+psycopg://user:password@host:5432/database

Required safety flags:

WHATSAPP_SENDING_ENABLED=false
KB_RUNTIME_ENABLED=true

Important:

WHATSAPP_SENDING_ENABLED=false

means the webhook can receive and process messages, but Elvira will not send real WhatsApp replies.

Only set this to:

WHATSAPP_SENDING_ENABLED=true

when production sending is intentionally activated.

Never commit .env.

Only .env.example should be versioned.

Local Development

Create and activate virtual environment:

python3 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Run the FastAPI server:

uvicorn app.main:app --reload

Health check:

curl http://127.0.0.1:8000/health

Expected response:

{
  "status": "ok",
  "service": "elvira-respirarte-agent"
}
Production Health Checks

Production health endpoint:

curl https://elvira.genflowautomation.com/health

Expected:

{
  "status": "ok",
  "service": "elvira-respirarte-agent",
  "version": "0.2.1"
}

Production readiness endpoint:

curl https://elvira.genflowautomation.com/ready

Current validated production readiness:

status = ready
environment = production
whatsapp_sending_enabled = false
kb_runtime_enabled = true
database = configured
patients repository = configured
interactions repository = configured
processed_messages repository = configured
kb repository = configured
LangSmith project = elvira-respirarte-prod
OpenAI configured = true
WhatsApp configured = true
hard_failures = []
WhatsApp Webhook Verification

Meta verifies the webhook through:

GET /webhook

The endpoint returns the raw hub.challenge as text/plain when:

hub.mode=subscribe
hub.verify_token matches WHATSAPP_VERIFY_TOKEN

Production webhook:

https://elvira.genflowautomation.com/webhook

Webhook subscribed field:

messages

The Meta handshake has been validated successfully.

WhatsApp Webhook Processing

Incoming WhatsApp messages are handled through:

POST /webhook

The parser extracts:

telefono
mensaje
nombre
msg_type
whatsapp_message_id
whatsapp_timestamp

Current supported message type:

text

Non-text messages and status notifications are ignored safely.

Current safety behavior:

If WHATSAPP_SENDING_ENABLED=false:

message is received
deduplication is checked
patient state is loaded
response is generated
interaction is logged
patient state is updated
real WhatsApp message is not sent
API response status is sending_skipped
Test Endpoint

Local test endpoint:

POST /test/message

Example:

curl -X POST "http://127.0.0.1:8000/test/message" \
  -H "Content-Type: application/json" \
  -d '{
    "telefono": "573001112233",
    "mensaje": "Quiero pedir una cita",
    "nombre": null,
    "estado_actual": "ST_INIT",
    "opt_out": false
  }'

Expected behavior:

{
  "intent": "cita",
  "nuevo_estado": "ST_CITA_FECHA",
  "next_action": "ask_preferred_date",
  "state_reason": "Paciente quiere agendar una cita."
}
Testing

Run all tests:

pytest

Current full test baseline:

76 passed

Run KB tests:

pytest tests/test_kb_service.py tests/test_kb_runtime_integration.py -v

P5-G KB baseline:

12/12 KB tests passing

Current test coverage validates:

deterministic intent classification
state machine transitions
opt-out handling
respiratory urgency detection
webhook persistence
message deduplication
patient state persistence
interaction logging
KB service routing for service questions
explicit service intent overrides appointment state
service questions inside ST_CITA_FRANJA use only kb_services
schedule questions use kb_schedules
price questions use operational rules and do not invent prices
irrelevant messages do not force KB usage
runtime KB node preserves deterministic state decisions
runtime KB fails safely when unavailable
runtime KB skips correctly when disabled
prompt safety constraints for medical/response boundaries

Important rule:

The LLM may improve wording, but must never decide intent, state, next action, opt-out logic, escalation logic or business rules.

LangSmith Tracing

Local project:

elvira-respirarte-local

Production project:

elvira-respirarte-prod

Tracing captures:

incoming message
sanitized input
detected intent
previous state
new state
next action
generated response
state reason
router version
state machine version
escalation flag
KB usage flag
KB sources
KB context
timezone context

To disable tracing locally:

LANGSMITH_TRACING=false
PostgreSQL

Production database:

elvira_respirarte_prod

Main operational tables:

patients
interactions
processed_messages
kb_services
kb_schedules
kb_rules

PostgreSQL responsibilities:

create or retrieve patient by phone
store patient name
store current state
store opt-out flag
load estado_actual before processing
save nuevo_estado after processing
save every interaction
deduplicate incoming WhatsApp messages by whatsapp_message_id
serve runtime KB data to Elvira

Core persistence rule:

Deduplicate before responding.
Persist state before trusting conversation continuity.
Persist opt_out=true when the user opts out.

Current relevant patient columns:

telefono
nombre
estado_actual
opt_out
created_at
updated_at
last_message_at

Current relevant interaction columns:

telefono
nombre
mensaje
respuesta
intent
estado_anterior
nuevo_estado
next_action
state_reason
router_version
state_machine_version
kb_used
escalation_required
whatsapp_message_id
whatsapp_timestamp
delivery_status
created_at

Current relevant processed message columns:

whatsapp_message_id
telefono
processed_at
Production DB Inspection

pgweb has been activated for the Elvira production PostgreSQL database.

Purpose:

- inspect production tables safely
- validate KB records after imports
- review interactions during dry-runs
- verify processed_messages deduplication
- check patient state and opt_out persistence
- support incident review without modifying application logic

Current pgweb database:

elvira_respirarte_prod

Validated through pgweb:

- kb_rules visible and active
- obsolete `RULE-003 teleconsulta` removed from production
- obsolete `RULE-007 appointment_confirmation` removed from production
- `RULE-008 appointment_slot_policy` updated to present candidate preference windows without confirming the appointment
- obsolete `HOR-05 Teleconsulta` removed from production
- `HOR-03` Saturday note simplified to reflect the current domiciliary flow
- kb_services, kb_schedules, patients, interactions and processed_messages accessible

Operational rule:

pgweb is for inspection and controlled SQL validation.
Do not use pgweb for casual production edits.
KB edits remain managed through the agreed KB import/update process.

Knowledge Base

Current KB source of truth for runtime:

PostgreSQL

Google Sheets remains the editing surface for KB data.

Operational rule:

Google Sheets edits.
PostgreSQL queries.

Current KB tables:

kb_services

Includes active services such as:

Terapia Respiratoria
Manejo de Pacientes Traqueotomizados
Pruebas de Función Pulmonar
Rehabilitación Pulmonar
Curso Profiláctico Materno
kb_schedules

Current operational reference:

- Monday, Tuesday, Thursday and Friday: domiciliary consultations 15:00–19:00
- Wednesday: domiciliary consultations 15:00–18:00
- Saturday: no domiciliary service
- Sunday and Colombian public holidays: no service
kb_rules

Includes operational rules for:

scheduling
capacity
cancellations
urgency escalation
out-of-hours requests
price communication restrictions
doctor-controlled medical decisions
unknown services
P5-G KB Answer Quality & Minimal Guardrails

Sprint P5-G closed the current KB phase by adding minimal answer quality safeguards.

Implemented:

KB answer guardrails added to LLM prompt construction
Elvira instructed not to invent services outside KB
Elvira instructed not to invent prices, costs, promotions or discounts
Price questions without explicit KB price are answered prudently
Unknown services are not confirmed as offered
Technical internals are hidden from the patient
Service questions use only kb_services
Schedule questions use kb_schedules
Runtime KB node preserves deterministic state decisions
Tests added for KB service and runtime routing behavior

Validated in LangSmith production:

Services question inside appointment state

Input:

Me podría decir que servicios ofrecen?

Validated output:

intent = servicios
next_action = answer_services
kb_used = true
kb_sources = ["kb_services"]
nuevo_estado = ST_CITA_FRANJA

Result:

Elvira answered with active services from KB only.
Schedule question

Input:

Qué horarios manejan?

Validated output:

kb_used = true
response = Monday to Friday 3:00 PM to 8:00 PM, Saturday 8:00 AM to 12:00 PM, no Sunday/holiday service

Result:

Elvira answered using the corrected kb_schedules record.
Price question

Input:

Cuanto cuesta una terapia respiratoria?

Validated output:

intent = pago
next_action = answer_payment_general
kb_used = true
response = no invented price

Result:

Elvira did not invent a price and redirected politely to valuation/confirmation by Dra. D'Aleman.
P6-A Production Safety Checklist

Sprint P6-A added a production readiness endpoint and safety checklist.

Implemented:

/ready endpoint
environment visibility
repository readiness checks
LangSmith status check
OpenAI configuration check
WhatsApp configuration check
hard failure list
explicit production safety status
confirmation that real WhatsApp sending remains disabled

Validated production state:

status = ready
environment = production
WHATSAPP_SENDING_ENABLED=false
KB_RUNTIME_ENABLED=true
hard_failures=[]
P6-B Failure Handling v1

Sprint P6-B hardened webhook behavior for failure scenarios.

Implemented:

safer webhook failure handling
controlled error responses
better distinction between ignored, failed and processed messages
protection against unsafe processing states
tests for failure paths

Validated:

Webhook failures do not trigger uncontrolled behavior.
Messages are not marked processed when extraction or processing fails unexpectedly.
P6-C Medical & Response Safety Boundaries

Sprint P6-C reinforced medical safety boundaries.

Implemented:

prompt medical safety rules strengthened in app/prompts/elvira_system.txt
deterministic respiratory urgency patterns added in app/services/intent.py
static prompt safety tests added
controlled LLM prompt test added with monkeypatch
permanent urgency classification test added

Critical issue resolved:

Input:
Tengo dolor fuerte en el pecho y me cuesta respirar

Previous behavior:
intent = general
safe wording came only from prompt

Fixed behavior:
intent = urgencia
next_action = escalate_urgent_case
nuevo_estado = ST_URGENCIA
escalation_required = true

Validated response:

Por lo que me comenta, es importante que busque atención médica urgente o se comunique con un profesional de salud. Respirarte no gestiona urgencias por este medio. Cuídese mucho.

Commit:

bdf7e2f fix: enforce respiratory urgency safety boundaries
P6-D Production Dry-Run Validation

Sprint P6-D validated production end-to-end with real WhatsApp sending disabled.

Production dry-run safety mode:

WHATSAPP_SENDING_ENABLED=false

Validated production endpoints:

/health = ok
/ready = ready
environment = production
kb_runtime_enabled = true
hard_failures = []
LangSmith project = elvira-respirarte-prod

Validated dry-run paths:

General greeting

Input:

Hola buen día

Validated:

HTTP = 200
status = sending_skipped
intent = general
whatsapp_sending_enabled = false
Deduplication

Repeated same whatsapp_message_id.

Validated:

HTTP = 200
status = ignored
reason = duplicate_message
Appointment request

Input:

Quiero pedir una cita

Validated:

intent = cita
estado_anterior = ST_GENERAL
nuevo_estado = ST_CITA_FECHA
delivery_status = sending_skipped
Appointment context continuation

Input:

Mañana en la tarde

Validated:

intent = fecha_cita
estado_anterior = ST_CITA_FECHA
nuevo_estado = ST_CITA_FRANJA
delivery_status = sending_skipped
Respiratory urgency

Input:

Tengo dolor fuerte en el pecho y me cuesta respirar

Validated:

intent = urgencia
next_action = escalate_urgent_case
estado_anterior = ST_CITA_FRANJA
nuevo_estado = ST_URGENCIA
escalation_required = true
delivery_status = sending_skipped

Validated in LangSmith production:

project = elvira-respirarte-prod
input = Tengo dolor fuerte en el pecho y me cuesta respirar
intent = urgencia
next_action = escalate_urgent_case
nuevo_estado = ST_URGENCIA
escalation_required = true
timezone_contexto = America/Bogota

Validated in PostgreSQL interactions:

intent = urgencia
estado_anterior = ST_CITA_FRANJA
nuevo_estado = ST_URGENCIA
next_action = escalate_urgent_case
escalation_required = true
delivery_status = sending_skipped

Validated in PostgreSQL processed_messages:

whatsapp_message_id registered
telefono registered
processed_at registered
unique constraint active

Validated in PostgreSQL patients:

estado_actual = ST_URGENCIA
last_message_at updated
OPTOUT from urgency

Input:

No quiero recibir más mensajes

Validated:

intent = optout
estado_anterior = ST_URGENCIA
nuevo_estado = ST_OPTOUT
next_action = confirm_optout
delivery_status = sending_skipped

Issue found during P6-D:

patients.estado_actual changed to ST_OPTOUT,
but patients.opt_out remained false.

Fix implemented:

update_patient_state now accepts optional opt_out.
main.py passes result.opt_out into patient persistence.

Validated after redeploy:

patients.estado_actual = ST_OPTOUT
patients.opt_out = true
interactions.intent = optout
interactions.next_action = confirm_optout
processed_messages registered

Commit:

73b05f6 fix: persist opt-out flag on patient state updates

P6-D final production validation:

Webhook production OK
Payload final OK
sending_skipped OK
LangSmith tracing OK
PostgreSQL interactions OK
processed_messages dedupe OK
patients state persistence OK
urgencia respiratoria OK
OPTOUT from urgency OK
opt_out=true corrected and validated OK
P6-E Pre-Go-Live Final Gate

Sprint P6-E prepared Elvira for the final controlled sending phase without enabling real WhatsApp sending.

Implemented:

KB production records updated and validated:
- kb_schedules HOR-01 to HOR-04 are the current active operational schedules
- obsolete HOR-05 Teleconsulta removed from production during P6-F.8 cleanup
- obsolete RULE-003 teleconsulta removed from production during P6-F.8 cleanup
- obsolete RULE-007 appointment_confirmation disclaimer removed from production
- RULE-008 updated as the current appointment slot preference policy

ADR-001 sealed:

Option C — internal Python `CalendarService` inside the repository.

Architecture decision updated after P6-F.8:

Elvira keeps deterministic architecture.
The LLM does not decide availability.
The LLM does not confirm exact appointment times.
The current Respirarte operating model does **not** require an external calendar integration.
The internal `CalendarService` remains useful only as deterministic candidate-slot logic for the current appointment request flow.
The next operational handoff will be based on `Solicitudes_Cita` plus human review by Dra. D'Aleman, not automated calendar booking.

Implemented in P6-E:

- appointment-state KB routing loads kb_rules for:
  - ST_CITA_CONFIRMADA
  - ST_CITA_PENDIENTE
  - ST_CITA_FRANJA
- explicit service intent still overrides appointment state and uses only kb_services
- Elvira prompt and deterministic response logic preserve the boundary between preference capture and appointment confirmation
- Elvira may present system-provided candidate slot windows as preferences
- Elvira must never confirm an appointment by itself
- the obsolete appointment time-slot disclaimer was removed in P6-F.8
- KB runtime tests were updated to validate the current appointment slot preference policy
- internal CalendarService scaffold remains available as deterministic candidate-slot logic
- CalendarService builds deterministic candidate slots only
- CalendarService does not confirm real availability
- external calendar integration is intentionally not part of the current operational phase

Calendar scaffold:

app/services/calendar_service.py

Current internal slot policy scaffold:

- Monday, Tuesday, Thursday, Friday:
  - 15:00–17:00
  - 17:00–19:00
- Wednesday:
  - 15:00–17:00
- Sunday:
  - no slots

Current CalendarService rule:

It only builds appointment slot candidates.
It does not confirm availability.
It does not send messages.
It does not modify Elvira state.
It remains an internal deterministic helper; current production workflow does not require external calendar integration.

Tests added:

- appointment-state KB context includes the current slot preference policy rule
- service questions inside appointment state exclude appointment rules
- CalendarService not configured without provider
- CalendarService builds two slots for Monday
- CalendarService builds one slot for Wednesday
- CalendarService builds no slots for Sunday
- CalendarService check_availability returns scaffold result
- P6-F.8 date resolver tests cover human-readable dates, weekend blocking and Colombian public holidays
- P6-F.8 graph-flow tests cover `Mañana`, `Pasado mañana en la mañana`, `El domingo` and holiday containment

Validated baseline:

76/76 tests passing

Commits:

23ca6b1 feat: load appointment rules for appointment states
86ed5a5 chore: add appointment time-slot guardrail to Elvira prompt
9ab14a9 test: cover appointment disclaimer KB runtime behavior
886b67e feat: scaffold internal calendar service

P6-E.11 KB runtime optimization:

- simple greetings inside appointment states no longer force unnecessary KB loading
- appointment-state service questions still correctly prioritize kb_services
- runtime KB remains informational only

P6-E.12 deterministic relative date resolver:

- app/services/date_resolver.py implemented
- relative phrases such as “mañana”, “pasado mañana”, “hoy” and weekday references are resolved using Colombia timezone
- date context is connected to the real LangGraph flow
- ElviraState now includes:
  - fecha_actual_colombia
  - fecha_solicitada
  - dia_semana_solicitado
  - es_dia_disponible
  - slots_candidatos
  - date_resolution_source
- app/services/llm.py receives deterministic date context before wording generation
- CalendarService still only generates candidate slots
- no real calendar availability is confirmed yet

P6-E.13 appointment availability wording guardrail:

- Elvira must not say:
  - “tenemos disponibilidad”
  - “hay disponibilidad”
  - “disponemos de”
  - “franjas disponibles”
- candidate slots must be presented only as options to review or validate
- approved wording includes:
  - “podemos revisar”
  - “podemos validar disponibilidad”
  - “las franjas que podemos validar son”
  - “puedo registrar su preferencia”
- production Swagger validation confirmed the improved wording:
  - “Las franjas que podemos validar son de 3:00 PM a 5:00 PM y de 5:00 PM a 7:00 PM.”

Production validation after P6-E final:

- /ready status = ready
- environment = production
- WHATSAPP_SENDING_ENABLED=false
- KB_RUNTIME_ENABLED=true
- real_whatsapp_sending_allowed=false
- /test/message validated with:
  - mensaje = “Mañana en la tarde”
  - estado_actual = ST_CITA_FRANJA
  - intent = fecha_cita
  - nuevo_estado = ST_CITA_FRANJA
  - fecha_actual_colombia = 2026-05-11
  - fecha_solicitada = 2026-05-12
  - dia_semana_solicitado = martes
  - es_dia_disponible = true
  - slots_candidatos = ["15:00–17:00", "17:00–19:00"]

Additional commits:

- feat: add deterministic relative date resolver
- feat: connect deterministic date context to Elvira flow
- test: enforce appointment availability guardrail
- fix: tighten appointment availability wording guardrail

Why n8n Was Replaced

n8n validated the concept but became too fragile for production due to:

opaque execution
fragile node references
context loss after Google Sheets nodes
state contamination risk
task runner instability
limited testability
difficult debugging
hard-to-audit memory behavior

Decision:

n8n validated the concept.
Python owns production logic.
Sprint Roadmap
Sprint	Description	Status
P1	Core local — intent, state machine, response	✅ Done
P2-A	LangSmith tracing	✅ Done
P2-B	LangGraph structural flow	✅ Done
P2-C	LLM response generation	✅ Done
P2-D	Documentation and repo baseline	✅ Done
P3	WhatsApp Cloud API integration	✅ Done
P3-G	Webhook safety flag and message metadata tracing	✅ Done
P4	PostgreSQL persistence — patients, interactions and processed messages	✅ Done
P5-A	KB schema tables	✅ Done
P5-B	KB repositories	✅ Done
P5-C	CSV import and production KB load	✅ Done
P5-D	Deterministic KB service	✅ Done
P5-E	Runtime KB context integration	✅ Done
P5-F	KB routing optimization	✅ Done
P5-G	KB answer quality and minimal guardrails	✅ Done
P6-A	Production Safety Checklist	✅ Done
P6-B	Failure Handling v1	✅ Done
P6-C	Medical & Response Safety Boundaries	✅ Done
P6-D	Production Dry-Run Validation	✅ Done
P6-E	Pre-Go-Live Final Gate	✅ Done
P6-F	Controlled Sending Activation Plan	⏳ Next
Development Rules
Keep the state machine deterministic.
Keep the LLM out of control decisions.
Keep tests passing before every commit.
Keep .env private — never commit it.
Keep WhatsApp as transport only.
Prefer small, auditable changes.
Do not use memory to decide state.
Do not reactivate real WhatsApp sending casually.
All production sends must be controlled by WHATSAPP_SENDING_ENABLED.
Any new database write must be auditable.
Any message from Meta must be traceable by whatsapp_message_id.
Google Sheets edits KB data.
PostgreSQL serves runtime KB data.
KB informs, but the state machine decides.
The LLM writes, but does not control the flow.
Medical urgency must be detected deterministically before relying on wording.
OPTOUT must win from any state.
If nuevo_estado = ST_OPTOUT, patient opt_out must persist as true.
Current Baseline
Core local: working
FastAPI: working
Meta webhook verification: working
WhatsApp payload parser: working
WhatsApp Send API integration: working
Webhook safety flag: working
Message metadata tracing: working
Production readiness endpoint: working
PostgreSQL persistence: working
Patient state persistence: working
Patient opt_out persistence: working
Message deduplication: working
Interactions logging: working
Processed messages audit: working
Runtime KB: working
KB services routing: working
KB schedules routing: working
KB rules routing: working
KB answer guardrails: working
Medical urgency classification: working
Urgency escalation state: working
OPTOUT from any state: working
LangSmith local: working
LangSmith production: working
LangGraph: working
LLM wording: working
GitHub repo: private and initialized
Deployment domain: configured
Current safety mode: WHATSAPP_SENDING_ENABLED=false
Current KB mode: KB_RUNTIME_ENABLED=true
Current full test baseline: 60 passed

This is the current stable foundation for Elvira as a production-oriented conversational agent.

Next step: Sprint P6-F — Controlled Sending Activation Plan.

---

## P6-E Manual Rollback Checklist

If any issue appears during pre-go-live or controlled activation preparation:

1. Keep real WhatsApp sending disabled:
   - `WHATSAPP_SENDING_ENABLED=false`

2. If unsafe traffic reaches production:
   - Disable or unsubscribe the Meta webhook temporarily.

3. If the deployed version behaves unexpectedly:
   - Redeploy the previous stable commit from Easypanel or Git.

4. If the app must be stopped immediately:
   - Stop the Easypanel service temporarily.

5. For incident review:
   - Search `interactions` by `whatsapp_message_id`.
   - Search `processed_messages` by `whatsapp_message_id`.
   - Check the patient record in `patients` by `telefono`.
   - Review the corresponding LangSmith run in `elvira-respirarte-prod`.

6. Safety rule:
   - Do not enable `WHATSAPP_SENDING_ENABLED=true` until the controlled activation plan is explicitly approved.

Rollback priority:
- Stop real sending first.
- Preserve auditability.
- Investigate by `whatsapp_message_id`.
- Only redeploy after identifying the failing commit or behavior.

---

## P6-F — Controlled Sending Activation Plan

### Activation Scope

P6-F is the final technical phase before controlled real go-live for Elvira on WhatsApp.

The goal of this phase is to prepare and validate controlled message sending using the official Colombian Respirarte WhatsApp number, without changing the conversational architecture that has already been validated.

Current rule:

- `WHATSAPP_SENDING_ENABLED=false` remains mandatory until all P6-F gates are completed.
- No real WhatsApp sending is activated during the initial readiness steps.
- The current German WhatsApp test number remains available until the Colombian number is fully verified and operational.
- Easypanel production variables must not be changed until the new Colombian `WHATSAPP_PHONE_NUMBER_ID` is available.

Scope included in P6-F:

- Add or verify the Colombian Respirarte number in WhatsApp Manager.
- Obtain the new Colombian Phone Number ID.
- Confirm display name, number status, messaging limits, quality rating and two-step verification.
- Keep Icebreakers disabled for now.
- Keep Commands disabled for now.
- Define a minimal future template strategy, without blocking the first controlled real test if the patient/user writes first.
- Align production environment variables only after WhatsApp Manager readiness is complete.
- Validate dry-run behavior with sending still disabled.
- Activate real sending only for an authorized internal controlled test.
- Audit DB, LangSmith and Meta after the controlled test.
- Execute rollback drill by disabling sending again.

Operational boundaries:

- Do not change the state machine unless a critical bug is found.
- Do not change KB routing unless a critical bug is found.
- Do not change database schema unless strictly necessary.
- Keep all changes small, testable and auditable.

Production principle:

> WhatsApp transports. The workflow controls. The KB informs. The model writes. The state machine protects. The log enables audit.

