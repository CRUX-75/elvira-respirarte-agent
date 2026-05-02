# Elvira Respirarte Agent

Elvira is the conversational assistant for **Respirarte**, a respiratory therapy service led by Dra. D'Aleman.

This project is a Python-based agentic system designed to replace the previous n8n prototype with a more deterministic, testable, auditable and production-ready architecture.

The current version focuses on a controlled conversational core for WhatsApp-style patient interactions.

---

## Project Status

Current repository:

- GitHub: `github.com/CRUX-75/elvira-respirarte-agent`
- Branch: `main`
- Visibility: Private
- Current phase: Sprint P2-D — Documentation and repository baseline

Completed:

- KB_Servicios created in Google Sheets
- KB_Horarios created in Google Sheets
- KB_Reglas created in Google Sheets
- Portfolio and schedule PDFs created
- Sprint P1 — Local Python core completed
- Sprint P2-A — LangSmith tracing completed
- Sprint P2-B — LangGraph structural flow completed
- Sprint P2-C — LLM response generation completed
- GitHub private repo created
- `.gitignore` configured
- `.env` confirmed as not versioned

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
```

The LLM does not decide intent, state or business rules.
Those responsibilities remain deterministic and testable.

---

## Current Architecture

Current local flow:

```txt
Incoming message
→ Input sanitization
→ Deterministic intent classifier
→ Pure state machine
→ LangGraph orchestration
→ Response generation
→ LangSmith tracing
→ FastAPI response
```

Target production flow:

```txt
WhatsApp Cloud API
→ FastAPI webhook
→ Input sanitization
→ Patient repository
→ Deterministic intent classifier
→ State machine
→ KB router
→ LangGraph orchestrator
→ LLM response generator
→ Log repository
→ WhatsApp Send API
```

---

## Tech Stack

Current stack:

- Python 3.12+
- FastAPI
- Pydantic + Pydantic Settings
- LangGraph
- LangChain + LangChain OpenAI
- LangSmith
- pytest
- python-dotenv
- Uvicorn

Planned stack:

- PostgreSQL or Supabase
- SQLAlchemy
- Redis (optional)
- Docker
- WhatsApp Cloud API

---

## Repository Structure

```txt
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
│   │   └── safety.py
│   ├── repositories/
│   │   └── logs.py
│   ├── models/
│   │   └── message.py
│   └── prompts/
│       └── elvira_system.txt
├── tests/
│   ├── test_intent.py
│   └── test_state_machine.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Environment Variables

Create a local `.env` file based on `.env.example`.

Required for LangSmith:

```env
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=elvira-respirarte-local
```

Required for OpenAI:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

Never commit `.env`. Only `.env.example` should be versioned.

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
  "version": "0.2.0"
}
```

---

## Test Endpoint

```bash
curl -X POST "http://127.0.0.1:8000/test/message" \
  -H "Content-Type: application/json" \
  -d '{
    "telefono": "573001112233",
    "mensaje": "Quiero pedir una cita",
    "nombre": null,
    "estado_actual": "ST_INIT",
    "opt_out": false
  }'
```

Expected behavior:

```json
{
  "intent": "cita",
  "nuevo_estado": "ST_CITA_FECHA",
  "next_action": "ask_preferred_date",
  "respuesta": "Claro, con gusto le ayudamos a coordinarla. ¿Para qué día o franja horaria le gustaría revisar disponibilidad?",
  "state_reason": "Paciente quiere agendar una cita."
}
```

---

## Testing

Run all tests:

```bash
pytest
```

Current baseline: **15/15 tests passing**

Test coverage validates:

- Deterministic intent classification
- Opt-out priority rule
- Appointment intent detection
- Price intent detection
- Service intent detection
- Context-aware date detection
- State machine transitions
- End-to-end local flow

Important rule: the LLM may improve wording but must never decide intent, state, next action, opt-out logic, escalation logic or business rules.

---

## LangSmith Tracing

Current project: `elvira-respirarte-local`

Tracing captures:

- Incoming message and sanitized input
- Detected intent
- Previous and new state
- Next action
- Generated response
- State reason
- Router and state machine versions
- Escalation and KB usage flags

To disable tracing locally:

```env
LANGSMITH_TRACING=false
```

---

## Knowledge Base

Initial KB lives in Google Sheets and will be migrated to a stable backend in Sprint P5.

Current KB tabs:

**KB_Servicios** — services including Terapia Respiratoria, Pruebas de Función Pulmonar, Rehabilitación Pulmonar, Curso Profiláctico Materno and SST Salud Respiratoria Empresarial.

**KB_Horarios** — Monday to Friday home care 15:00–21:00, Saturday in-person 08:00–12:00, Sunday no service, teleconsultation pending.

**KB_Reglas** — operational rules for scheduling, cancellations, urgency escalation and out-of-hours requests.

---

## Why n8n Was Replaced

n8n validated the concept but became too fragile for production due to opaque execution, fragile node references, context loss after Sheets nodes, state contamination risk, task runner instability and limited testability.

Decision: n8n validated the concept. Python owns production logic.

---

## Sprint Roadmap

| Sprint | Description | Status |
|---|---|---|
| P1 | Core local — intent, state machine, response | ✅ Done |
| P2-A | LangSmith tracing | ✅ Done |
| P2-B | LangGraph structural flow | ✅ Done |
| P2-C | LLM response generation | ✅ Done |
| P2-D | Documentation and repo baseline | ✅ Done |
| P3 | WhatsApp Cloud API integration | ⏳ Next |
| P4 | Persistence layer — patient and log repos | ⏳ Planned |
| P5 | KB router — migrate Sheets to DB | ⏳ Planned |
| P6 | Safety, hardening and Docker | ⏳ Planned |

---

## Development Rules

- Keep the state machine deterministic.
- Keep the LLM out of control decisions.
- Keep tests passing before every commit.
- Keep `.env` private — never commit it.
- Keep WhatsApp as transport only.
- Prefer small, auditable changes.
- Do not introduce memory until the core is stable.
- Do not use memory to decide state.

---

## Current Baseline

- Core local: working
- Tests: 15/15 passing
- LangSmith: working
- LangGraph: working
- LLM wording: working
- GitHub repo: private and initialized

This is the first stable foundation for Elvira as a production-oriented conversational agent.
