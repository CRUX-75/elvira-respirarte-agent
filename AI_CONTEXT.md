# AI_CONTEXT.md — Elvira / Respirarte Agent

## Purpose

This file is the **current operational context** for AI-assisted development on the Elvira / Respirarte project.

It must answer, quickly:

- what is running now;
- what Elvira can and cannot do;
- which architectural rules are non-negotiable;
- which production settings are active;
- what remains pending;
- what the next useful business or technical step is.

This file is **not a historical changelog**. Detailed phase closures remain in Git history and `docs/`. Do not append dozens of old sprint notes here again.

---

## Current Source of Truth

Repository:

```txt
elvira-respirarte-agent
github.com/CRUX-75/elvira-respirarte-agent
branch: main
```

Deployment:

```txt
Easypanel on Hetzner
https://elvira.genflowautomation.com
```

Current production status:

```txt
Elvira is active in production.
Real Meta webhook is active.
Real WhatsApp replies are active.
KB runtime is active.
Google Sheets human review inbox is active.
```

Latest confirmed full-suite baseline before the latest WhatsApp UX-only changes:

```txt
325 passed
```

Latest confirmed implementation commit shown during the current work:

```txt
87077fd Add minimum WhatsApp typing delay
```

At the start of every new development session, verify the actual repository state:

```bash
git status --short
git log --oneline --decorate -n 6
```

Do not assume a commit hash without checking.

---

## Current Production Configuration

Expected Easypanel values:

```env
WHATSAPP_SENDING_ENABLED=true
KB_RUNTIME_ENABLED=true
GOOGLE_SHEETS_ENABLED=true
WHATSAPP_API_URL=https://graph.facebook.com/v25.0
```

Other required configuration:

```env
DATABASE_URL=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=elvira-respirarte-prod
WHATSAPP_VERIFY_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_TOKEN=...
GOOGLE_SHEETS_SPREADSHEET_ID=...
GOOGLE_SHEETS_SOLICITUDES_CITA_TAB=Solicitudes_Cita
GOOGLE_SERVICE_ACCOUNT_JSON=...
```

Never commit secrets or real environment values.

Emergency stop:

```env
WHATSAPP_SENDING_ENABLED=false
```

Optional Sheets stop:

```env
GOOGLE_SHEETS_ENABLED=false
```

Keep this enabled during rollback unless the KB itself is the problem:

```env
KB_RUNTIME_ENABLED=true
```

---

## Current Production Capabilities

Elvira currently supports:

- real WhatsApp Cloud API conversations;
- Meta webhook verification and inbound message handling;
- message deduplication by `whatsapp_message_id`;
- persistent patient state in PostgreSQL;
- deterministic intent classification;
- deterministic state transitions;
- runtime KB answers about services, schedules, and rules;
- deterministic relative and absolute date resolution;
- Colombian holiday detection;
- weekend blocking;
- KB-driven appointment slots;
- appointment-context carryover across turns;
- deterministic slot selection;
- safe AppointmentRequest persistence;
- duplicate active-request prevention;
- Google Sheets human review inbox;
- deterministic opt-out from any state;
- LangSmith tracing and production logs;
- WhatsApp read receipts;
- WhatsApp typing indicator;
- a minimum natural typing delay for very fast responses.

Elvira uses the LLM for **wording only**.

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

The LLM must not decide:

- intent;
- state;
- next action;
- opt-out;
- escalation;
- deduplication;
- appointment availability;
- weekend or holiday rules;
- candidate slots;
- persistence eligibility;
- appointment confirmation;
- lifecycle transitions.

Critical business logic belongs in Python/FastAPI and PostgreSQL-backed services.

n8n may be used later for auxiliary workflows, but it must not own:

- patient state;
- appointment state;
- availability decisions;
- persistence rules;
- human review lifecycle;
- confirmation logic.

---

## Repository Structure

The repository uses:

```txt
app/
docs/
tests/
scripts/
data/
requirements.txt
Dockerfile
README.md
AI_CONTEXT.md
```

Do not create a `src/` directory.

---

## Current WhatsApp Runtime

Production flow:

```txt
Meta inbound message
→ FastAPI /webhook
→ payload extraction
→ required-field validation
→ deduplication
→ mark message as read
→ show typing indicator
→ load/create patient
→ load persisted state and appointment context
→ deterministic processing
→ AppointmentRequest runtime
→ minimum typing visibility when needed
→ send WhatsApp reply
→ save interaction
→ update patient state
→ mark inbound message as processed
→ trace/log
```

WhatsApp UX behavior:

- the patient's message receives blue read receipts;
- the typing indicator appears while Elvira processes;
- if processing is faster than two seconds, Elvira waits only for the remaining time;
- if processing already takes longer than two seconds, no extra delay is added;
- read/typing failure must not crash the main webhook flow.

Current API base:

```txt
https://graph.facebook.com/v25.0
```

---

## Appointment Architecture

Non-negotiable workflow:

```txt
FECHA → KB → SLOTS → CONTEXT
HORA → CONTEXT → SLOT SELECTION → APPOINTMENT_REQUEST
```

Meaning:

1. A date turn resolves the requested date deterministically.
2. The runtime checks weekends, Colombian holidays, and KB availability.
3. Candidate slots are generated from `kb_schedules`.
4. The complete result is stored as `appointment_context`.
5. A time/slot turn consumes that persisted context.
6. A valid slot selection may create or reuse an active AppointmentRequest.
7. The context is cleared only after successful persistence.

The graph must not let the LLM decide availability.

---

## Current Schedule

Production KB schedule:

```txt
Monday, Tuesday, Thursday, Friday:
- 15:00–17:00
- 17:00–19:00

Wednesday:
- 15:00–18:00

Saturday:
- unavailable

Sunday:
- unavailable

Colombian holidays:
- unavailable unless explicitly overridden in a future controlled phase
```

Product rule:

```txt
The system adapts to Dra. D'Aleman's real schedule.
The doctor is not forced into uniform slots because the code prefers them.
```

---

## Appointment Context Contract

Minimum operational shape:

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

For `hora_cita` turns, persisted appointment context is authoritative for:

- `fecha_solicitada`;
- `fecha_solicitada_texto`;
- `slots_candidatos`;
- `es_dia_disponible`;
- `is_weekend`;
- `is_colombia_holiday`;
- `colombia_holiday_name`.

### P6-F.9.90 root cause and fix

The first message could contain both appointment intent and an embedded date:

```txt
Quiero agendar una cita para el miércoles 22 de julio de 2026
```

The graph correctly produced:

```txt
intent = cita
nuevo_estado = ST_CITA_FRANJA
fecha_solicitada = 2026-07-22
slots_candidatos = ["3:00 p. m.–6:00 p. m."]
```

The bug was that `capture_appointment_context_from_state(...)` accepted only:

```txt
intent = fecha_cita
```

It now captures context for:

```python
{"cita", "fecha_cita"}
```

when:

```txt
nuevo_estado = ST_CITA_FRANJA
fecha_solicitada exists
```

P6-F.9.90 is closed and deployed.

---

## Slot Selection Rules

Single candidate slot:

- soft confirmation is accepted;
- examples: `sí`, `ok`, `esa`, `esa franja`, `me sirve`, `registre esa`.

Multiple candidate slots:

- explicit selection is required;
- examples: `la primera`, `la segunda`, `la de las 3`, `la de las 5`, `de 3 a 5`, `de 5 a 7`.

Ambiguous confirmation with multiple slots must not persist an AppointmentRequest.

Exact-hour requests:

- Elvira must not promise an exact arrival time;
- she explains that care is handled by franjas;
- she may map the hour to a valid franja;
- persistence waits for confirmation of the franja;
- final timing remains subject to Dra. D'Aleman's confirmation.

---

## AppointmentRequest Contract

PostgreSQL is the source of truth.

Correct direction:

```txt
AppointmentRequest model
→ AppointmentRequestService
→ AppointmentRequestRepository
→ PostgreSQL
→ Google Sheets human review adapter
```

Google Sheets is not the source of truth.

Persistence is allowed only when:

- intent is `hora_cita`;
- valid date context exists;
- the date is available;
- candidate slots exist;
- slot selection is valid;
- `franja_solicitada` is resolved;
- Elvira is registering a request, not confirming it.

New patient requests use:

```txt
estado_solicitud = pendiente_confirmacion
```

Elvira must never automatically return:

```txt
estado_solicitud = confirmada
```

Duplicate active requests are prevented through:

```txt
AppointmentRequestService.create_or_reuse_active_request(...)
```

Valid lifecycle statuses:

```txt
nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada
```

Forbidden legacy statuses:

```txt
pendiente
contraoferta
completada
```

A proposed alternative remains represented as:

```txt
pendiente_confirmacion
```

---

## Human Review and Google Sheets

Current patient flow:

```txt
Patient writes to Elvira
→ Elvira handles the conversation
→ AppointmentRequest is persisted in PostgreSQL
→ request appears in Solicitudes_Cita
→ Dra. D'Aleman reviews it
→ Dra. D'Aleman confirms or contacts the patient manually
```

Elvira registers requests.

Dra. D'Aleman confirms appointments.

Google Sheets must not:

- own lifecycle state;
- confirm appointments;
- trigger patient messages directly;
- bypass backend validation;
- replace PostgreSQL.

Doctor-facing review columns may include:

```txt
fecha_confirmada
franja_confirmada
accion_doctora
motivo_decision
revisado_por
fecha_revision
```

Supported internal human-review actions:

```txt
confirm
request_missing_data
propose_alternative
reschedule
cancel
close
```

The internal human-review endpoint exists and is protected by an admin token. A Swagger call returned:

```json
{"detail": "Invalid or missing internal admin token"}
```

This was rejected before `HumanReviewService` ran.

Do not debug this now unless automated doctor actions become an active requirement. Manual Google Sheets review is not blocked.

### Google Sheets ownership handoff

The operational spreadsheet should ultimately belong to Respirarte/Dra. D'Aleman, not remain dependent on the developer's personal Drive.

Recommended handoff:

1. Dra. D'Aleman makes a copy in her own Drive.
2. She shares the copy with the Google service account as Editor.
3. She sends the new spreadsheet link.
4. Update `GOOGLE_SHEETS_SPREADSHEET_ID` in Easypanel.
5. Redeploy.
6. Run one controlled request and confirm it appears in the new file.
7. Remove access to the old developer-owned file.

Do not switch IDs before the copied sheet and service-account access are ready.

---

## Patient Operational Fields

Production `appointment_requests` supports these nullable fields:

```txt
tipo_cita
eps
barrio
edad_paciente
notas_clinicas_breves
```

The current appointment conversation does not necessarily collect all of them yet.

Do not force additional intake questions into the live flow without an explicitly scoped product decision.

---

## Opt-Out

Opt-out already exists and has priority from any state.

Examples:

```txt
No quiero recibir más mensajes.
No me escriban más.
Salir.
Dar de baja.
```

Expected behavior:

```txt
any state
→ opt-out detected
→ nuevo_estado = ST_OPTOUT
→ patient.opt_out = true
```

Future outbound campaigns or warm-patient reactivation must check PostgreSQL `opt_out` immediately before every send.

A Google Sheet or exported database must never override the live PostgreSQL opt-out state.

---

## Current Production Rollout

Elvira may now receive real patient traffic.

Recommended rollout:

```txt
Dra. D'Aleman shares the official number gradually
→ patients contact Elvira
→ Elvira answers and registers requests
→ doctor reviews Google Sheets
→ doctor confirms manually
```

Current recommendation:

- allow gradual real-patient usage;
- do not return to endless artificial testing;
- monitor real failures, not hypothetical ones;
- patch only real blockers;
- do not launch uncontrolled mass messaging.

Organic acquisition direction:

```txt
Instagram/Facebook content
→ Respirarte landing page
→ WhatsApp button
→ Elvira
→ AppointmentRequest
→ Google Sheets
→ doctor confirmation
```

---

## Warm Patient Database Strategy

The doctor's database contains:

- previous Respirarte patients;
- patients referred by professional colleagues.

These are not necessarily cold contacts, but outreach must remain respectful and controlled.

Recommended future segmentation:

```txt
origen = paciente_anterior | referido
autorizado_contacto
fuente_autorizacion
fecha_autorizacion
opt_out
fecha_ultimo_contacto
numero_contactos
```

Possible future pilot:

- previous patients: one respectful reactivation template;
- referred patients: colleague introduction or explicit authorization first;
- small pilot of approximately 10 contacts;
- no automatic repeated follow-up;
- opt-out must be honored immediately.

This is a future campaign block, not part of the current live inbound MVP.

---

## Current Safety Boundaries

Do not add casually:

- automatic appointment confirmation;
- automatic rescheduling or cancellation;
- Calendar synchronization;
- Telegram notifications;
- n8n-owned appointment logic;
- payment workflows;
- uncontrolled campaigns;
- mass outbound messaging;
- therapy package/session tracking.

Do not alter production behavior simply because a trace, dashboard, or cosmetic field looks imperfect.

A real patient-facing failure is more important than observational polish.

---

## Known Non-Blocking Debt

Do not treat these as launch blockers:

1. Debug response shape may show top-level:

```txt
franja_solicitada = null
dia_semana_solicitado = null
```

while the correct operational values exist inside:

```txt
appointment_request_decision
appointment_request
```

2. `/test/message-stateful` still duplicates parts of `_apply_appointment_request_runtime(...)`.

3. A future graph cleanup could restore appointment context before transition logic more explicitly.

4. Human-review admin-token Swagger validation is not closed.

5. The latest read-receipt, typing-indicator, and delay changes were compiled and validated in production, but the last explicitly recorded full suite remains `325 passed` from before those UX-only changes.

Do not open any of these without a named reason or a real regression.

---

## Development Protocol

For non-trivial work:

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

For small, reversible production UX changes:

- inspect the exact code path;
- make one narrow change;
- compile/check syntax;
- inspect the diff;
- deploy;
- run one controlled real test;
- commit and document.

Avoid:

- random patching;
- switching tools or environments mid-task;
- huge command dumps;
- unnecessary Swagger matrices;
- reopening already closed blocks;
- using LangSmith exploration as a launch blocker when production behavior is already proven.

---

## Validation Surfaces

Local:

```bash
pytest -q
python -m py_compile app/main.py app/services/whatsapp.py app/config.py
git diff --check
```

Safe stateful endpoint:

```txt
POST /test/message-stateful
```

Production endpoints:

```txt
GET /health
GET /ready
GET /webhook
POST /webhook
```

Production evidence:

- WhatsApp conversation;
- Easypanel logs;
- PostgreSQL;
- Google Sheets;
- LangSmith, only when it adds concrete diagnostic value.

---

## Rollback

If patient-facing behavior becomes unsafe:

1. Disable outbound replies:

```env
WHATSAPP_SENDING_ENABLED=false
```

2. Redeploy/restart.

3. If Sheets is part of the incident:

```env
GOOGLE_SHEETS_ENABLED=false
```

4. Preserve evidence:

```txt
whatsapp_message_id
patient phone
patient state
interaction row
appointment request ID
deployment commit
```

5. Investigate the exact failure before patching.

If necessary:

- redeploy the previous stable commit;
- temporarily stop the Easypanel service;
- temporarily disable/unsubscribe the Meta webhook.

Priority:

```txt
Stop unsafe sending.
Preserve auditability.
Identify the failing behavior.
Patch only after root cause is understood.
```

---

## Current Closed Milestones

Relevant closed blocks only:

```txt
P6-F.9.38–P6-F.9.42
KB-driven appointment context, slots, selection, exact-hour behavior, and persistence

P6-F.9.43–P6-F.9.49
production readiness, real webhook validation, production evidence, and safety decisions

P6-F.9.50–P6-F.9.77
human review backend contract, repository integration, Google Sheets adapter, production schema, and doctor process

P6-F.9.78
controlled MVP live-release decision

P6-F.9.89
absolute dates, previous-date replacement, intent classification, missing-date safety, Wednesday rule, weekend/holiday guards, and callback observability

P6-F.9.90
Wednesday stateful appointment-context carryover regression fixed and Swagger-validated

P6-F.9.91
WhatsApp read receipt, typing indicator, and natural minimum delay validated in production

P6-F.9.92
Voice interaction architecture closed on the isolated branch; voice remains an I/O layer around the deterministic core

P6-F.9.93
Inbound WhatsApp voice notes, secure media handling, audio normalization, Spanish STT, webhook integration, and deterministic fallback implemented with voice flags disabled
```

Detailed closure evidence belongs in Git history and `docs/`, not in this file.

---

## Current Next Direction

Elvira remains online in production serving text conversations. Voice development remains isolated in:

```txt
feature/p6-f-9-92-voice-interaction
```

P6-F.9.92 — Voice Interaction Architecture and P6-F.9.93 — Inbound Voice Notes are closed on that branch. No voice code has been merged or activated in production.

The next engineering phase is:

```txt
P6-F.9.94 — Outbound Voice Replies
```

Authorized scope:

- convert the existing deterministic `result.respuesta` to speech;
- upload the generated audio through the WhatsApp transport boundary;
- send it as a WhatsApp voice note;
- fall back to the existing text response without rerunning the core;
- keep `VOICE_INPUT_ENABLED=false` and `VOICE_REPLIES_ENABLED=false` by default.

Meta remains transport-only. OpenAI provides STT/TTS. Elvira retains all conversational logic, state, persistence, safety decisions, and fallback behavior.

Still out of scope:

- multitenancy;
- patient follow-up;
- campaigns;
- Realtime;
- voice cloning;
- new conversational or appointment logic.

Production activation is not authorized before P6-F.9.95 safety, observability, rollback, and controlled-device validation.

Operational rollout and monitoring of the existing text service continue independently.

---

## Maintenance Rule for This File

When project status changes:

- update the relevant current section;
- remove obsolete statements;
- keep the file concise;
- do not append the entire history again;
- keep detailed sprint evidence in `docs/` and Git commits.

Target size:

```txt
A practical operational brief, not a 160,000-character archive.
```