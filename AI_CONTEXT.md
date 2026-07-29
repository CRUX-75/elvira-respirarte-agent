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

P6-F.9.94
Outbound TTS, secure temporary audio, WhatsApp media upload, voice-note delivery, deterministic text fallback, and webhook integration implemented with voice flags disabled

P6-F.9.95
Atomic voice-processing lease, allowlist and media safety gates, privacy-safe observability, rollback validation, and controlled production voice activation completed
```

Detailed closure evidence belongs in Git history and `docs/`, not in this file.

---

## Current Active Sprint — P6-F.9.97

P6-F.9.97 — Conversational Continuity and KB-Grounded Services has completed
local implementation and automated validation.

Implementation commit:

84c1ac0 — Implement conversational continuity and KB grounding

Validated behavior:

greetings occur only in ST_INIT;
active conversations do not restart after a general fallback;
3 and 5 select the actual candidate appointment franjas only in
ST_CITA_FRANJA;
service questions take priority over stale appointment routing while preserving
the existing appointment state;
service matching includes approved KB_Servicios fields such as
techniques;
service grounding records the matched service, term, field and status;
grounding statuses are exact, partial and not_found;
oximetría is an exact SRV-01 technique match;
oximetría dinámica is a partial match and triggers safe escalation;
unknown services do not claim availability, schedulability or clinical
equivalence;
candidate slots are described only as preferences or options to review;
existing WhatsApp message-id idempotency remains unchanged;
no PostgreSQL or Google Sheets changes were made.

Validation evidence:

P6-F.9.97 regression tests: 14 passed
KB and propagation tests: 27 passed
complete suite: 410 passed
Python compilation: passed
git diff --check: passed
forbidden availability-language scan: no matches

Specification and evidence:

docs/P6-F.9.97_CONVERSATIONAL_CONTINUITY_KB_GROUNDED_SERVICES_SDD.md

Current status:

Implementation validated locally. Pending branch review, merge, deployment and
controlled production validation by text and voice.

P6-F.9.96 global voice wildcard changes remain preserved separately in the
named Git stash and are not part of this sprint.

## Current Next Direction

Elvira remains online in production. Existing text conversations continue operating normally.

Voice phases P6-F.9.92 through P6-F.9.95 are closed.

Current controlled production state:

```env
VOICE_INPUT_ENABLED=true
VOICE_REPLIES_ENABLED=true
VOICE_REPLY_TO_AUDIO_ONLY=true
VOICE_ALLOWED_PHONE_NUMBERS=<one controlled test number>
```

Voice is active only for one allowlisted operator-controlled number. Global voice activation is not authorized.

Production validation completed:

PostgreSQL backup and Git rollback tag created;
additive voice_processing_claims migration applied;
/health and /ready returned 200;
production text regression passed;
inbound audio-to-text passed;
outbound audio-to-audio passed;
configuration rollback was validated;
privacy stop condition was detected and corrected;
production privacy fix was merged in 571b19e;
voice logs now redact content as msg=None | resp=None;
full suite passed with 377 tests.

The production voice is functional and understandable. Natural intonation and consistently clear pronunciation of “Elvira” remain future quality improvements, not functional blockers. Post-closure stabilization fixed repeated AI disclosure in `393d659`, merged in `277fd05`; `ST_INIT` retains disclosure while later states omit it. The full suite passed with 385 tests, health and readiness returned 200, and controlled WhatsApp validation passed.

Duplicate-work, non-allowlisted sender, and delivery-fallback contracts remain covered by automated regression tests. Global rollout requires a separate explicit decision.

Still out of scope: multitenancy, patient follow-up, campaigns, Realtime, voice cloning, and new conversational or appointment logic.

Patient follow-up remains the next major roadmap candidate after voice stabilization, but it is not yet authorized.

## Current Independent Debugging Status

DBG-001 — Absolute Date Resolution Regression is closed.

Production merge `c0c150c` restores deterministic support for textual dates without a year and numeric `DD/MM/YYYY` or `DD-MM-YYYY` dates. Production `/health` and `/ready` returned HTTP 200, and the three reported cases passed through the non-persistent production test endpoint.

Validation coverage was completed in two partitions: 94 critical appointment tests plus 289 remaining repository tests, for 383 tests total.

Rollback reference: `pre-dbg-001-absolute-date-fix-2026-07-18`.

No environment variable, database schema, voice behavior or roadmap milestone changed.

DBG-002 — Slot Range Mapping Regression remains separate and has not started.

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

<!-- BEGIN P6-F.9.98-P6-F.10 CONTEXT -->

## Current baseline — P6-F.9.98 to P6-F.10

### Repository and production

- Repository: `elvira-respirarte-agent`.
- Working baseline: `main`.
- Elvira remains online in production during development.
- Before controlled production tests, verify that Easypanel is running the latest `main`.
- Do not change production environment variables unless the active sprint explicitly requires it.

### Current voice configuration

- `VOICE_INPUT_ENABLED=true`
- `VOICE_REPLIES_ENABLED=true`
- `VOICE_REPLY_TO_AUDIO_ONLY=true`
- `VOICE_ALLOWED_PHONE_NUMBERS=*`
- `VOICE_TTS_MODEL=gpt-4o-mini-tts`
- `VOICE_TTS_VOICE=marin`
- `VOICE_TTS_RESPONSE_FORMAT=opus`

Voice pipeline:

`WhatsApp audio -> STT -> deterministic core -> TTS -> WhatsApp voice note`

Voice and text share the same deterministic clinical and appointment core.

### P6-F.9.98 — Clinical KB Services Update

Status: **closed**.

The approved clinical catalog is versioned in:

- `data/kb/datakbKB_Servicios.csv`
- `app/services/approved_service_catalog.py`

The approved catalog acts as a read-only runtime overlay so that stale PostgreSQL content cannot override the current clinical service information.

PostgreSQL and Google Sheets were not modified during this sprint.

Current clinical service policy:

#### Respiratory Therapy

- Active.
- Domiciliary.
- Does not require a prior medical order.
- Approximate duration: 30 to 45 minutes.
- Requires three hours of fasting.
- Includes aerosol therapy, postural drainage, bronchial hygiene, inhalotherapy and oximetry.
- Does not include domiciliary oxygen therapy.

#### Dynamic Oximetry — `SRV-07`

- Active and independent domiciliary service.
- Requires a medical order.
- Requires prior clinical validation.
- An informational question does not begin an appointment flow.
- A service request enters `ST_OXIMETRIA_DINAMICA_VALIDACION`.
- No medical order:
  - `escalation_required=true`
  - `next_action=escalate_dynamic_oximetry_missing_order`
- Oxygen support for 15 days or more:
  - `escalation_required=true`
  - `next_action=escalate_dynamic_oximetry_long_oxygen_support`
- Medical order and fewer than 15 days with oxygen:
  - continues to `ST_CITA_FECHA`
  - `next_action=ask_preferred_date`

#### Temporarily inactive or retired services

- Tracheostomized patients:
  - temporarily inactive;
  - cannot be scheduled;
  - requires specialist assessment;
  - escalation is required.
- Domiciliary oxygen therapy:
  - not offered by Respirarte;
  - only available institutionally when an appropriate oxygen point exists.
- Maternal psychoprophylactic course:
  - retired.

Pulmonary function tests, pulmonary rehabilitation and business services were also updated in the approved catalog.

### P6-F.9.99 — Voice Naturalness and Conversational Prosody

Status: **closed**.

Implemented:

- `app/services/voice_text_normalizer.py`
- integration immediately before TTS in `app/services/text_to_speech.py`

The speech normalizer:

- converts written hours into natural spoken hours;
- converts quantities and numeric ranges;
- expands safe abbreviations such as `Dra.`;
- converts visual lists into spoken pauses;
- preserves clinical facts and meaning;
- does not modify `state.respuesta`;
- does not modify intent, state, `next_action` or escalation;
- does not modify the original WhatsApp text fallback.

Examples:

- `3:00 p. m. a 5:00 p. m.` becomes `tres de la tarde a cinco de la tarde`.
- `entre 30 y 45 minutos` becomes `entre treinta y cuarenta y cinco minutos`.
- `3 horas de ayuno` becomes `tres horas de ayuno`.
- `Dra. D'Aleman` becomes `doctora D'Aleman`.

Approved TTS configuration:

- Model: `gpt-4o-mini-tts`
- Voice: `marin`
- Format: OGG/Opus
- Spanish: neutral Colombian
- Pronunciation: soft Bogota-style pronunciation
- Latin American seseo
- Avoid Spanish peninsular pronunciation, rhythm and intonation
- Warm, calm and professional conversational delivery

Final validation:

- Real TTS preview listened to and approved.
- **444 tests passed**.
- Python compilation passed.
- `git diff --check` passed.

### Next sprint — P6-F.10 Human Escalation via WhatsApp

Status: **planned; implementation not started**.

Confirmed business decision:

> Human escalation notifications must be delivered to the WhatsApp number of Dr. Paola D'Aleman.

Elvira can already detect escalation conditions through:

- `escalation_required=true`
- a specific `next_action`
- a clinical or operational reason
- a safe conversational state

The actual outbound WhatsApp notification to the doctor has not yet been implemented.

Target flow:

`Elvira detects escalation`
`-> creates or records a human-review event`
`-> sends a WhatsApp notification to Dr. D'Aleman`
`-> records pending, sent or failed`
`-> prevents duplicates`
`-> supports safe retry`
`-> preserves the link to the patient and conversation`

Initial escalation cases:

- Dynamic oximetry without a medical order.
- Dynamic oximetry with oxygen support for 15 days or more.
- Tracheostomized patient requiring specialist assessment.
- Special clinical conditions or insufficient information.
- Existing flows that already produce `escalation_required=true`.

The doctor's WhatsApp number must:

- come from secure configuration;
- never be hardcoded;
- not be confused with `VOICE_ALLOWED_PHONE_NUMBERS`;
- not be exposed in logs, tests or documentation.

### Active restrictions

- Keep Elvira online in production.
- Do not implement multitenant.
- Do not resume P7.
- Do not implement patient follow-up yet.
- Do not change the approved clinical rules from P6-F.9.98.
- Do not change the approved Marin voice.
- Do not change `VOICE_ALLOWED_PHONE_NUMBERS=*`.
- Do not modify PostgreSQL or Google Sheets without an explicit, justified technical need.
- Do not send raw voice audio to the doctor.
- Do not log full clinical messages or unnecessary patient data.
- The user executes all commands.
- Avoid splitting commands unnecessarily.
- Avoid repetitive validation rounds.
- Use targeted tests before the full suite.

### P6-F.10 design document

The initial design document is:

`docs/sdd/P6-F.10_HUMAN_ESCALATION_WHATSAPP_SDD.md`

The new sprint must begin with one focused architecture audit before finalizing persistence and delivery details.

<!-- END P6-F.9.98-P6-F.10 CONTEXT -->

## P6-F.10 — Human Escalation via WhatsApp (Cerrado en producción)

Estado final: cerrado y operativo en producción.

### Implementación final

- El disparo ocurre únicamente cuando:
  - `result.escalation_required is True`
  - `result.next_action` pertenece al conjunto aprobado.
- El evento se registra en PostgreSQL antes de la entrega externa.
- La unicidad natural es:
  `(inbound_whatsapp_message_id, escalation_action)`.
- El envío a revisión humana es best-effort y nunca altera ni bloquea
  la respuesta o el estado conversacional del paciente.
- El número del profesional se configura mediante:
  `HUMAN_ESCALATION_WHATSAPP_NUMBER`.
- La función se controla mediante:
  `HUMAN_ESCALATION_ENABLED`.

### Entrega mediante plantilla

- Plantilla aprobada por Meta: `revision_humana`.
- Idioma configurado para Cloud API: `es_CO`.
- El aviso utiliza diez parámetros mínimos y ordenados:
  paciente, teléfono, servicio, motivo, resumen, orden médica,
  dato relevante, estado conversacional, fecha y referencia interna.
- No se envían audios, transcripciones completas, historial completo
  ni payloads crudos del proveedor.

### Persistencia y estados

Migraciones aplicadas en producción:

- `006_create_human_escalation_events.sql`
- `007_human_escalation_template_delivery_status.sql`

Estados soportados:

- `pending`
- `accepted`
- `sent`
- `delivered`
- `read`
- `failed`

Los webhooks de estado se correlacionan mediante
`provider_message_id`. Las actualizaciones no retroceden un evento
cuando Meta entrega callbacks fuera de orden.

### Validación productiva

- Commit desplegado: `7c8baf1`.
- Suite completa: `497 passed`.
- Caso controlado:
  `escalate_dynamic_oximetry_missing_order`.
- Secuencia persistida:
  `accepted -> sent -> delivered`.
- `provider_message_id` registrado.
- Sin error de proveedor.
- La Dra. D'Aleman confirmó directamente la recepción del mensaje
  en WhatsApp.
- La respuesta al paciente permaneció correcta e independiente del
  resultado de la notificación humana.

### Decisión de cierre

P6-F.10 queda cerrada. No se requiere trabajo adicional para su uso
productivo normal. Futuras mejoras de panel operativo, reintentos
administrativos o métricas pertenecen a fases posteriores y no forman
parte de este alcance.

## P6-F.11 — Patient Reactivation via WhatsApp

Estado: implementación parcial segura. P6-F.11.1 y P6-F.11.2 están cerradas; la campaña continúa desactivada y sin persistencia productiva.

### Separación de procesos

Respirarte tendrá dos procesos independientes:

1. Reactivación histórica:
   - Base entregada por la Dra. Paola D'Aleman.
   - 65 registros totales.
   - 49 contactos marcados como atendidos.
   - Objetivo: presentar nuevamente los servicios de Respirarte.
   - No constituye seguimiento clínico ni posatención.

2. Seguimiento posatención:
   - Fase futura e independiente.
   - Aplicará a pacientes atendidos desde el 1 de agosto de 2026.
   - Utilizará una tabla separada con fecha de atención, servicio
     recibido y datos específicos del seguimiento.
   - Queda fuera del alcance de P6-F.11.

### Objetivo de P6-F.11

Realizar un contacto único por WhatsApp con los pacientes históricos
elegibles, presentar de forma general los servicios respiratorios
domiciliarios de Respirarte y permitir que las personas interesadas
continúen dentro del flujo normal de Elvira.

El mensaje inicial:

- debe identificar a Elvira y Respirarte;
- no debe mencionar diagnósticos;
- no debe mencionar tratamientos o servicios anteriores;
- no debe afirmar que el receptor es paciente;
- no debe incluir información clínica;
- debe permitir rechazar futuros contactos.

### Elegibilidad

La población inicial son los 49 registros con `ATENDIDO=SI`.

Antes de enviar deben excluirse:

- teléfonos inválidos;
- números duplicados;
- contactos con opt-out vigente;
- pacientes con inconformidad previa conocida;
- casos sensibles definidos por la doctora;
- contactos que no cumplan las condiciones de autorización;
- registros marcados con `ATENDIDO=NO`.

Los teléfonos se normalizarán al formato internacional E.164.

### Comportamiento de la campaña

- Un solo mensaje comercial por contacto.
- Si no responde, no se insiste.
- Un retry técnico no puede generar un segundo mensaje comercial.
- Si la persona muestra interés, entra al flujo normal de servicios
  y solicitud de cita de Elvira.
- Si presenta una queja o solicita atención humana, se aplican las
  reglas de escalamiento existentes.
- La campaña permanecerá desactivada durante la auditoría,
  implementación y pruebas iniciales.

### Opt-out semántico

El opt-out no dependerá únicamente de una respuesta literal `NO`.

Elvira debe reconocer como rechazo:

- negativas directas;
- falta de interés;
- solicitudes de no volver a escribir;
- solicitudes de eliminar el número;
- objeciones de privacidad;
- respuestas hostiles;
- insultos o malas palabras usados como rechazo;
- errores ortográficos y abreviaciones;
- lenguaje coloquial colombiano;
- mayúsculas y repeticiones;
- emojis hostiles dentro del contexto;
- mensajes de voz cuya transcripción exprese rechazo.

Ejemplos:

- `No gracias`
- `No me interesa`
- `No me escriban`
- `Déjenme en paz`
- `Bórrenme de su lista`
- `No autorizo estos mensajes`
- `Dejen de molestar`
- respuestas insultantes sin otra solicitud concreta

Resultado esperado:

- `intent=optout`
- `next_action=confirm_optout`
- `nuevo_estado=ST_OPTOUT`
- `opt_out=true`

Respuesta:

`Entendido. No le enviaremos más mensajes de Respirarte.
Que tenga un buen día.`

Elvira no debe discutir, responder al insulto, preguntar por qué ni
intentar recuperar la venta.

### Diferencia entre queja y opt-out

Una queja no implica automáticamente opt-out.

- Queja con solicitud de solución:
  escalamiento humano, sin asumir opt-out.
- Queja acompañada de solicitud de no contacto:
  escalamiento humano y opt-out.
- Hostilidad o insulto aislado como rechazo:
  opt-out.

Categorías seguras propuestas:

- `explicit_refusal`
- `stop_contact_request`
- `hostile_rejection`
- `privacy_objection`

No debe almacenarse el insulto completo en el registro de campaña.

### Persistencia e idempotencia

La persistencia conceptual debe incluir:

- campaña;
- contacto de campaña;
- referencia de origen;
- nombre;
- teléfono normalizado;
- elegibilidad y motivo de exclusión;
- estado de envío;
- `provider_message_id`;
- clasificación de respuesta;
- opt-out y motivo seguro;
- escalamiento;
- referencia interna.

Unicidad propuesta:

`UNIQUE (campaign_id, phone_e164)`

Un contacto no puede recibir dos mensajes de la misma campaña. Una
nueva importación tampoco puede reactivar un opt-out existente.

### Reutilización técnica prevista

P6-F.11 podrá reutilizar, después de auditar el código:

- transporte de templates de WhatsApp;
- procesamiento de estados del proveedor;
- correlación mediante `provider_message_id`;
- flujo determinístico actual de Elvira;
- estado `ST_OPTOUT`;
- KB de servicios;
- flujo de solicitud de cita;
- voz para mensajes entrantes de audio;
- escalamiento humano de P6-F.10.

No se modificará el comportamiento clínico ni el flujo actual de citas.

### P6-F.11.1 — Reactivation Architecture and Source Audit

Estado: **cerrada arquitectónicamente**.

La campaña aún no está implementada ni habilitada.

Decisiones cerradas:

- se reutiliza el spreadsheet existente `Respirarte CRM`;
- se creó la pestaña `Reactivacion_Historica`;
- solo se incorporarán contactos realmente utilizables;
- Google Sheets funciona como superficie de preparación y revisión;
- PostgreSQL continúa siendo la fuente de verdad;
- no se reutiliza `human_escalation_events`;
- no se enviaron mensajes;
- no se aplicaron migraciones;
- no se modificó Easypanel ni producción.

Contrato aprobado de `Reactivacion_Historica`:

- `source_reference`
- `nombre`
- `telefono_original`
- `atendido`
- `autorizado_contacto`
- `telefono_e164`
- `revision_doctora`
- `motivo_exclusion`
- `estado_reactivacion`
- `observaciones`

Propiedad de columnas:

- fuente histórica:
  `source_reference`, `nombre`, `telefono_original`, `atendido`;
- revisión humana:
  `autorizado_contacto`, `revision_doctora`, `motivo_exclusion`,
  `observaciones`;
- sistema:
  `telefono_e164`, `estado_reactivacion`.

Listas configuradas:

- `atendido`: `SI`, `NO`;
- `autorizado_contacto`: `PENDIENTE`, `SI`, `NO`;
- `revision_doctora`: `PENDIENTE`, `APROBADO`, `EXCLUIR`.

Se cargaron cinco contactos únicamente para validar la estructura de la
pestaña. Permanecen sin normalización, sin elegibilidad calculada y sin
envío.

La integración reutilizará:

- `app/adapters/google_sheets_client.py`;
- `send_whatsapp_template_message(...)`;
- `WhatsAppPayload.extract_status_updates()`;
- el flujo determinístico actual de Elvira;
- `ST_OPTOUT`;
- la KB, las citas, la voz y el escalamiento existentes.

No se reutilizará el writer específico de `Solicitudes_Cita`. Se creará un
adapter separado para `Reactivacion_Historica`.

Persistencia conceptual aprobada:

- `reactivation_campaigns`;
- `reactivation_campaign_contacts`;
- `UNIQUE (campaign_id, phone_e164)`.

`patients.opt_out` debe comprobarse inmediatamente antes de cada envío.
La consulta debe ser read-only y no puede usar
`get_or_create_patient_by_phone(...)`.

El webhook actual continúa entregando todos los callbacks de estado al
runtime de P6-F.10 y retorna inmediatamente. P6-F.11.2 implementó el
router genérico best-effort en
`app/services/whatsapp_status_runtime.py`, pero todavía no está conectado
a `/webhook`. Cada dominio conservará persistencia, métricas e
idempotencia independientes.

Templates activos observados en Meta:

- `revision_humana`;
- `franja_no_disponible`;
- `cita_confirmada`;
- `franja_atencion_prompt`;
- `solicitud_cita_recibida`;
- `hello_world`.

Ninguno es adecuado para el primer contacto de reactivación.

Template creado para P6-F.11:

- nombre: `reactivacion_respirarte`;
- categoría: `Marketing`;
- idioma: `Spanish (COL)` / `es_CO`;
- header de texto: `Respirarte`;
- parámetro del body `{{1}}`: nombre del contacto;
- footer: ninguno;
- botones: ninguno;
- estado: enviado a revisión de Meta.

La plantilla todavía no está aprobada y no puede utilizarse hasta confirmar
su aprobación.

El opt-out determinístico actual se conserva y P6-F.11.2 amplió su
cobertura semántica mediante pruebas para reconocer rechazo directo,
falta de interés en contexto de reactivación, privacidad, lenguaje
coloquial colombiano, errores ortográficos, hostilidad e insultos usados
como rechazo.

Los rechazos fuertes se reconocen globalmente. Los rechazos suaves como
`No gracias` o `No me interesa` requieren contexto explícito de campaña.
Una queja con solicitud de solución no implica automáticamente opt-out;
una queja acompañada de solicitud de no contacto produce escalamiento y
opt-out. La decisión semántica no almacena el mensaje hostil completo.

### Protocolo de trabajo constituido

- documentar `AI_CONTEXT.md` y el SDD en una sola ventana;
- no repetir bloques ni comandos ya ejecutados;
- avanzar paso a paso, con cada objetivo explicado;
- documentar después de cada fase;
- usar `grep`, `cat` y `sed` para inspección y validación.

### P6-F.11.2 — Campaign Domain Contracts and Test-First Foundation

Estado: **cerrada técnicamente y validada localmente**.

Rama de implementación:

`feature/p6-f-11-2-campaign-domain-contracts`

Implementación añadida:

- `app/models/reactivation_campaign.py`
  - modelos puros de campaña y contacto;
  - estados explícitos de campaña;
  - estados explícitos de contacto;
  - autorización y revisión humana;
  - motivos seguros de exclusión;
  - contratos de elegibilidad.
- `app/services/reactivation_domain.py`
  - transiciones válidas de campaña y contacto;
  - normalización E.164 para importación;
  - evaluación determinística de elegibilidad;
  - clave estable de idempotencia;
  - bloqueo de segundo envío comercial;
  - reducción monotónica de callbacks;
  - clasificación semántica segura de respuestas.
- `app/repositories/patients.py`
  - `find_patient_by_phone_read_only(...)`;
  - consulta mínima por teléfono;
  - únicamente `SELECT`;
  - no crea, actualiza ni elimina pacientes.
- `app/services/intent.py`
  - rechazos fuertes de no contacto y privacidad tienen prioridad global;
  - rechazos suaves permanecen limitados al contexto explícito de campaña.
- `app/services/whatsapp_status_runtime.py`
  - router genérico best-effort;
  - copias aisladas por dominio;
  - fallo de un handler no bloquea al otro;
  - sin SQL, repositorios ni conocimiento de tablas;
  - todavía no conectado a `/webhook`.

Estados de campaña definidos:

- `draft`
- `ready`
- `active`
- `paused`
- `completed`
- `cancelled`

Estados de contacto definidos:

- `staged`
- `excluded`
- `eligible`
- `pending`
- `accepted`
- `sent`
- `delivered`
- `read`
- `failed`
- `opted_out`

Contratos de seguridad cerrados:

- `accepted`, `sent`, `delivered` y `read` bloquean otro envío;
- un `provider_message_id` existente bloquea otro intento comercial;
- solo un fallo retryable anterior a la aceptación puede reintentarse;
- los callbacks repetidos o fuera de orden no regresan el estado;
- el router no deduplica: cada repositorio de dominio conserva esa autoridad;
- la elegibilidad utiliza motivos seguros, no información clínica libre;
- el opt-out vigente se consulta sin crear pacientes;
- no se almacena el insulto o mensaje hostil completo;
- queja con solicitud de solución no implica opt-out automático;
- queja con solicitud de no contacto implica escalamiento y opt-out.

Evidencia de validación:

- pruebas nuevas de P6-F.11.2: **147 passed**;
- regresiones dirigidas de P6-F.10, callbacks, webhook y voz:
  **57 passed**;
- suite completa del repositorio: **644 passed**;
- compilación Python: aprobada;
- `git diff --check`: aprobado;
- `app/main.py`: sin cambios.

No implementado todavía:

- tablas PostgreSQL;
- migraciones aplicadas;
- repositorios persistentes de campaña;
- importación desde Google Sheets;
- adapter de `Reactivacion_Historica`;
- envío del template;
- handler persistente de callbacks de reactivación;
- conexión del router genérico a `/webhook`;
- activación de campaña.

No se modificó Easypanel, no se aplicaron migraciones y no se enviaron
mensajes.

### Próximo sprint

`P6-F.11.3 — Campaign Persistence Schema and Repository Foundation`

Objetivos:

1. definir el esquema SQL de `reactivation_campaigns`;
2. definir el esquema SQL de `reactivation_campaign_contacts`;
3. proteger `UNIQUE (campaign_id, phone_e164)`;
4. implementar contratos de repositorio para campaña y contacto;
5. crear o reutilizar contactos de forma idempotente;
6. implementar claim atómico para un intento de entrega;
7. persistir `provider_message_id` y estados de entrega;
8. proteger callbacks repetidos y fuera de orden en PostgreSQL;
9. comprobar `patients.opt_out` inmediatamente antes del claim o envío;
10. escribir primero las pruebas de repositorio;
11. mantener la campaña desactivada;
12. crear migraciones versionadas, pero no aplicarlas sin autorización;
13. no conectar todavía el envío ni modificar `/webhook`;
14. no modificar Easypanel ni realizar mensajes reales.
