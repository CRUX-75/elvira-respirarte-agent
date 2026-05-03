# Elvira Respirarte Agent

Elvira is the conversational assistant for **Respirarte**, a respiratory therapy service led by Dra. D'Aleman.

This project is a Python-based agentic system designed to replace the previous n8n prototype with a more deterministic, testable, auditable and production-ready architecture.

The current version focuses on a controlled conversational core for WhatsApp patient interactions, with FastAPI receiving Meta webhooks, LangGraph orchestrating the flow, deterministic logic controlling state transitions, and the LLM limited to response wording.

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
- Current phase: Sprint P3-G completed — Webhook Safety Patch
- Next phase: Sprint P4 — PostgreSQL Persistence Layer

Current production safety state:

- Previous n8n workflow: OFF
- Easypanel app: OFF by default for safety
- WhatsApp sending controlled by `WHATSAPP_SENDING_ENABLED`
- Real WhatsApp sending must remain disabled until persistence and deduplication are implemented

Completed:

- KB_Servicios created in Google Sheets
- KB_Horarios created in Google Sheets
- KB_Reglas created in Google Sheets
- Portfolio and schedule PDFs created
- Sprint P1 — Local Python core completed
- Sprint P2-A — LangSmith tracing completed
- Sprint P2-B — LangGraph structural flow completed
- Sprint P2-C — LLM response generation completed
- Sprint P2-D — Documentation and repo baseline completed
- Sprint P3 — WhatsApp Cloud API integration completed
- Sprint P3-G — Webhook safety flag and message metadata tracing completed
- GitHub private repo created
- `.gitignore` configured
- `.env` confirmed as not versioned
- Current test baseline: 15/15 tests passing

---

## Core Architecture Principle

```txt
WhatsApp transports.
FastAPI receives.
LangGraph orchestrates.
State machine decides.
KB informs.
LLM writes.
Database persists.
Logs audit.
Tests protect.

The LLM does not decide intent, state, next action, opt-out logic, escalation logic or business rules.

Those responsibilities remain deterministic, testable and auditable.

Current Architecture

Current implemented flow:

WhatsApp Cloud API
→ FastAPI webhook
→ WhatsApp payload parser
→ Input message model
→ LangSmith tracing
→ LangGraph orchestration
→ Deterministic intent classifier
→ Pure state machine
→ LLM response generation
→ Safety-controlled WhatsApp Send API
→ Local logs

Current safety behavior:

WHATSAPP_SENDING_ENABLED=false
→ Webhook receives message
→ Elvira processes message
→ Response is generated
→ Interaction is logged
→ WhatsApp reply is NOT sent

Target production flow for P4+:

WhatsApp Cloud API
→ FastAPI webhook
→ Message ID deduplication
→ Patient repository
→ Load current patient state
→ Input sanitization
→ Deterministic intent classifier
→ State machine
→ KB router
→ LangGraph orchestrator
→ LLM response generator
→ Save interaction
→ Update patient state
→ WhatsApp Send API
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
OpenAI GPT model for wording
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

Planned stack:

PostgreSQL
SQLAlchemy or SQLModel
Alembic
Docker hardening
Redis optional later, only if needed
Repository Structure
elvira-respirarte-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── graph/
│   │   ├── state.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── transitions.py
│   ├── services/
│   │   ├── intent.py
│   │   ├── response.py
│   │   ├── llm.py
│   │   ├── tracing.py
│   │   ├── safety.py
│   │   └── whatsapp.py
│   ├── repositories/
│   │   └── logs.py
│   ├── models/
│   │   ├── message.py
│   │   └── whatsapp.py
│   └── prompts/
│       └── elvira_system.txt
├── tests/
│   ├── test_intent.py
│   └── test_state_machine.py
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

Required safety flag:

WHATSAPP_SENDING_ENABLED=false

Important:

WHATSAPP_SENDING_ENABLED=false

means the webhook can receive and process messages, but Elvira will not send real WhatsApp replies.

Only set this to:

WHATSAPP_SENDING_ENABLED=true

when production persistence and deduplication are ready.

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
  "service": "elvira-respirarte-agent",
  "version": "0.2.1"
}
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
- message is processed
- response is generated
- interaction is logged
- real WhatsApp message is not sent
- API response status is "sending_skipped"

Example local webhook test:

curl -X POST "http://localhost:8000/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [
      {
        "changes": [
          {
            "value": {
              "contacts": [
                {
                  "profile": {
                    "name": "Nabit Mikan"
                  },
                  "wa_id": "4917655660163"
                }
              ],
              "messages": [
                {
                  "from": "4917655660163",
                  "id": "wamid.TEST123",
                  "timestamp": "1714694400",
                  "text": {
                    "body": "Hola"
                  },
                  "type": "text"
                }
              ]
            }
          }
        ]
      }
    ]
  }'

Expected response when sending is disabled:

{
  "status": "sending_skipped",
  "intent": "general",
  "respuesta": "Hola, qué gusto saludarle. Cuénteme, ¿en qué le podemos ayudar hoy en Respirarte?",
  "whatsapp_sending_enabled": false,
  "whatsapp_message_id": "wamid.TEST123",
  "whatsapp_timestamp": "1714694400"
}
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
  "respuesta": "Claro, con gusto le ayudamos a coordinarla. ¿Para qué día o franja horaria le gustaría revisar disponibilidad?",
  "state_reason": "Paciente quiere agendar una cita."
}
Testing

Run all tests:

pytest

Current baseline:

15/15 tests passing

Test coverage validates:

Deterministic intent classification
Opt-out priority rule
Appointment intent detection
Price intent detection
Service intent detection
Context-aware date detection
State machine transitions
End-to-end local flow

Important rule:

The LLM may improve wording, but must never decide intent, state, next action, opt-out logic, escalation logic or business rules.
LangSmith Tracing

Local project:

elvira-respirarte-local

Production project:

elvira-respirarte-prod

Tracing captures:

Incoming message
Detected intent
Previous state
New state
Next action
Generated response
State reason
Router version
State machine version
Escalation flag
KB usage flag

To disable tracing locally:

LANGSMITH_TRACING=false
Knowledge Base

Initial KB lives in Google Sheets and will be migrated to a stable backend in Sprint P5.

Current KB tabs:

KB_Servicios

Includes services such as:

Terapia Respiratoria
Pruebas de Función Pulmonar
Rehabilitación Pulmonar
Curso Profiláctico Materno
SST Salud Respiratoria Empresarial
KB_Horarios

Current operational reference:

Monday to Friday: home care 15:00–21:00
Saturday: in-person 08:00–12:00
Sunday: no service
Teleconsultation: pending
KB_Reglas

Includes operational rules for:

Scheduling
Cancellations
Urgency escalation
Out-of-hours requests
Price communication restrictions
Doctor-controlled medical decisions
Why n8n Was Replaced

n8n validated the concept but became too fragile for production due to:

Opaque execution
Fragile node references
Context loss after Google Sheets nodes
State contamination risk
Task runner instability
Limited testability
Difficult debugging
Hard-to-audit memory behavior

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
P4	PostgreSQL persistence — patients, interactions and processed messages	⏳ Next
P5	KB router — migrate Sheets to DB or stable backend	⏳ Planned
P6	Safety, hardening and Docker	⏳ Planned
P3-G Safety Patch Summary

Sprint P3-G added a safety layer before reactivating production.

Implemented:

WHATSAPP_SENDING_ENABLED=false/true
Webhook can process messages without sending replies
whatsapp_message_id extraction
whatsapp_timestamp extraction
Structured webhook processing output
Logs showing disabled-send behavior
Test baseline preserved: 15/15 passing

Validated behavior:

Webhook receives message ✅
Elvira processes message ✅
LLM generates response ✅
WhatsApp sending skipped when disabled ✅
Message ID extracted ✅
Timestamp extracted ✅
Webhook returns 200 OK ✅

This protects against accidental replies caused by Meta webhook retries or unstable redeploys.

Known Current Limitation

There is still no database persistence.

Current limitation:

Each webhook message currently starts with estado_actual="ST_INIT".

Impact:

Follow-up messages such as "mañana en la tarde" cannot yet recover the previous patient state.

This will be solved in Sprint P4 through PostgreSQL persistence.

Sprint P4 Target

P4 will introduce PostgreSQL persistence.

Target database:

elvira_respirarte_prod

Initial tables:

patients
interactions
processed_messages

P4 responsibilities:

Create or retrieve patient by phone
Store patient name
Store current state
Load estado_actual before processing
Save nuevo_estado after processing
Save every interaction
Deduplicate incoming WhatsApp messages by whatsapp_message_id
Prevent duplicate replies caused by Meta retries

Core P4 rule:

Deduplicate before responding.
Persist state before trusting conversation continuity.
Development Rules
Keep the state machine deterministic.
Keep the LLM out of control decisions.
Keep tests passing before every commit.
Keep .env private — never commit it.
Keep WhatsApp as transport only.
Prefer small, auditable changes.
Do not introduce memory until the core is stable.
Do not use memory to decide state.
Do not reactivate real WhatsApp sending until persistence and deduplication exist.
All production sends must be controlled by WHATSAPP_SENDING_ENABLED.
Any new database write must be auditable.
Any message from Meta must be traceable by whatsapp_message_id.
Current Baseline
Core local: working
FastAPI: working
Meta webhook verification: working
WhatsApp payload parser: working
WhatsApp Send API integration: working
Webhook safety flag: working
Message metadata tracing: working
Tests: 15/15 passing
LangSmith local: working
LangSmith production: working
LangGraph: working
LLM wording: working
GitHub repo: private and initialized
Deployment domain: configured
Easypanel app: kept off by default for safety

This is the current stable foundation for Elvira as a production-oriented conversational agent.

Next step: Sprint P4 — PostgreSQL Persistence Layer.
