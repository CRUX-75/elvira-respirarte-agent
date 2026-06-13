# AI_CONTEXT.md — Elvira / Respirarte Agent

## Purpose

This file is the operational context for AI-assisted development on the Elvira / Respirarte project.

It exists so ChatGPT or any coding assistant can understand the current repository status, architecture decisions, safety boundaries, and next implementation block without rediscovering the project from scratch.

This file is not public-facing documentation. It is a working context file.

---

## Current Working Status

Current repository:

elvira-respirarte-agent

Repository:

github.com/CRUX-75/elvira-respirarte-agent

Current branch:

main

Current active block:

P6-F.9.37 — KB-Driven Appointment Workflow Architecture

Current status:

RESET / CLEAN ARCHITECTURE REPLANNING

Latest confirmed local validation:

247 passed

Current safety baseline:

* `WHATSAPP_SENDING_ENABLED=false`
* Real `/webhook` must not be touched.
* Real WhatsApp sending must not be enabled.
* Real patients must not be contacted.
* Google Sheets, Telegram, n8n, Calendar, campaigns, doctor confirmation automation, and therapy sessions remain out of scope.
* `/test/message-stateful` remains the only safe validation surface.

---

## Repository Structure

The repository uses:

* app/
* docs/
* tests/
* scripts/
* data/
* requirements.txt
* Dockerfile
* README.md

Do not create a `src/` folder.

This repository uses `app/`.

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
* Google Sheets only as future human-visible operational inbox when needed
* n8n only as future auxiliary workflow layer when needed

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

* appointment request state
* scheduling handoff logic
* deterministic validation
* patient state transitions
* persistence rules
* appointment request lifecycle

---

## Why P6-F.9.37 Exists

P6-F.9.36 showed that the appointment flow was becoming too fragile because the system mixed:

* current turn state
* restored appointment context
* default availability flags
* KB schedule data
* persistence guards

This caused contradictions such as:

* one turn showing valid slots for a date
* the next turn saying the same date was unavailable

The issue is not only `la de las 5`.

The real issue is workflow architecture.

The project is now being reset conceptually around a clean KB-driven appointment workflow.

---

## New Architecture Rule

The appointment flow must follow this rule:

FECHA → KB → SLOTS → CONTEXT
HORA → CONTEXT → SLOT SELECTION → APPOINTMENT_REQUEST

Meaning:

* A date turn resolves date, availability, and candidate slots from the KB.
* That result is saved as the active `appointment_context`.
* A time/slot turn must consume the saved `appointment_context`.
* A time/slot turn must not recalculate or contradict date availability.
* AppointmentRequest persistence happens only after a valid slot selection.

---

## KB Scheduling Source of Truth

The KB must represent the real operational availability of Dra. D'Aleman.

Current intended schedule:

* HOR-01: Lunes a viernes excepto miércoles, 15:00–19:00, max 2 patients, visible slots 15:00–17:00 and 17:00–19:00.
* HOR-02: Miércoles, 15:00–18:00, max 1 patient, visible slot 15:00–18:00.
* HOR-03: Saturday unavailable.
* HOR-04: Sunday unavailable.
* Colombia holidays are unavailable unless explicitly overridden later.

Important product rule:

The system must adapt to the doctor’s schedule.

The doctor must not be forced into uniform slots because the code prefers that.

---

## Local KB Files

The local KB files must stay aligned with production PostgreSQL.

Important local source:

`data/kb/datakbKB_Horarios.csv`

Expected current content:

```csv
schedule_id,day_type,day_name,modality,start_time,end_time,slot_duration_minutes,max_patients,location_type,is_available,notes
HOR-01,weekday,Lunes a viernes excepto miércoles,Domiciliaria,15:00,19:00,120,2,Domicilio paciente,true,Máximo 2 pacientes por día. Franja visible al paciente: 2 horas. Slot 1: 15:00–17:00. Slot 2: 17:00–19:00. Buffer de 60 min entre citas por desplazamiento en Bogotá.
HOR-02,wednesday,Miércoles,Domiciliaria,15:00,18:00,180,1,Domicilio paciente,true,Máximo 1 paciente los miércoles. Franja visible al paciente: 15:00–18:00. Elvira puede registrar esta franja como preferencia, pero no confirma la cita.
HOR-03,saturday,Sábado,Sin atención domiciliaria,—,—,—,0,—,false,Sin servicio domiciliario los sábados.
HOR-04,sunday,Domingo,Sin atención,—,—,—,0,—,false,Sin atención domingos ni festivos, salvo indicación expresa de la Dra. D'Aleman.
```

Important local rules source:

`data/kb/datakbKB_Reglas.csv`

RULE-008 must not force a uniform schedule. It must describe that visible slots depend on `KB_Horarios`.

Intended RULE-008 meaning:

* Lunes, martes, jueves y viernes: 15:00–17:00 and 17:00–19:00.
* Miércoles: 15:00–18:00.
* Elvira may register a preference, but must not confirm an appointment.

---

## Production DB Cleanup Status

The production DB was cleaned for safe re-architecture work.

Current intended state:

* Test patients reset or cleaned.
* Test appointment requests removed or ignored.
* `WHATSAPP_SENDING_ENABLED=false`.
* Production KB should represent the real Wednesday schedule again.
* Real patient flow must remain untouched.

Do not run real WhatsApp tests.

Use `/test/message-stateful` only.

---

## AppointmentRequest Architecture Decision

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

## AppointmentRequest Lifecycle Contract

Valid states:

* nueva
* pendiente_datos
* pendiente_confirmacion
* confirmada
* reagendada
* cancelada
* cerrada

Active states:

* nueva
* pendiente_datos
* pendiente_confirmacion
* confirmada
* reagendada

Terminal states:

* cancelada
* cerrada

Invalid/non-existing states that must not be used:

* pendiente
* contraoferta
* completada

Important clarification:

AppointmentRequestStatus is not an Enum with members such as `.PENDIENTE`.

It is treated according to the model's real Literal/string contract.

Contraoffer representation:

There is no separate `contraoferta` state in the model.

A contraoffer is represented operationally as:

pendiente_confirmacion

Meaning:

The request is waiting for patient acceptance, doctor review, or confirmation after a proposed change.

---

## AppointmentRequest Persistence Rule

AppointmentRequest can be created only when:

* intent is `hora_cita`
* date context exists
* selected date is available
* candidate slot selection is valid
* `franja_solicitada` is resolved
* Elvira is registering a request, not confirming an appointment

When persistence is allowed:

`estado_solicitud = pendiente_confirmacion`

The function must never return:

`estado_solicitud = confirmada`

Doctor/human confirmation remains a future flow.

Terminal patient copy after request registration:

“Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.”

---

## Appointment Context Contract

`appointment_context` is the operational package calculated after a valid date turn.

Expected minimum shape:

```json
{
  "flow": "appointment_request",
  "fecha_solicitada": "2026-06-17",
  "fecha_solicitada_texto": "miércoles 17 de junio",
  "slots_candidatos": ["3:00 p. m.–6:00 p. m."],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null
}
```

For `hora_cita` turns, this context must be treated as authoritative for:

* `fecha_solicitada`
* `fecha_solicitada_texto`
* `slots_candidatos`
* `es_dia_disponible`
* `is_weekend`
* `is_colombia_holiday`
* `colombia_holiday_name`

Do not restore appointment context field by field as missing values only.

For time/slot turns, restore the complete operational appointment package.

---

## Slot Selection Rules

If there is one candidate slot:

* Soft confirmations may be accepted.
* Examples: `sí`, `ok`, `listo`, `esa`, `esa franja`, `me sirve`, `registre esa`.
* The single slot can be used as `franja_solicitada`.

If there are multiple candidate slots:

* The patient must choose explicitly.
* Valid examples: `la primera`, `la segunda`, `la de las 3`, `la de las 5`, `de 3 a 5`, `de 5 a 7`.
* Ambiguous replies like `sí`, `ok`, `esa`, `en la tarde`, or `me sirve` must not persist an AppointmentRequest.

---

## Exact-Hour Behavior

Elvira must not promise exact arrival times.

If the patient asks for an exact hour inside a valid franja:

* Explain that care is handled by time windows/franjas.
* Map the exact hour to the corresponding available franja if possible.
* Ask for confirmation.
* Do not persist until the patient confirms the franja.

Example for Wednesday single slot:

Patient:

`no se puede a las 4?`

Expected behavior:

* Do not confirm exact 4 p. m.
* Explain that attention is by franja.
* Mention the available franja 15:00–18:00.
* Ask whether to register that franja as preference.
* Persist only after confirmation.

---

## Correct Workflow Map

1. Receive message.
2. Sanitize input.
3. Load patient + `appointment_context`.
4. Classify intent.
5. Run state transition.
6. If `fecha_cita`:

   * resolve date
   * query KB / calculate slots
   * validate weekend / holiday / availability
   * save full `appointment_context`
   * ask patient to choose slot
7. If `hora_cita`:

   * restore full authoritative `appointment_context`
   * resolve slot selection
   * validate selection
   * persist AppointmentRequest if valid
   * clear `appointment_context`
8. Save patient state.
9. Save interaction log.
10. Return response.

---

## Current Next Step

## Active Roadmap — P6-F.9.37+

This roadmap is the operational plan for the appointment workflow reset.

The project must move phase by phase.

No microphases.

No uncontrolled patching.

No implementation without SDD.

---

## Phase 1 — P6-F.9.37: KB-Driven Appointment Workflow Spec

Goal:

Define the new appointment workflow architecture before touching implementation.

Main deliverable:

`docs/P6-F.9.37_KB_DRIVEN_APPOINTMENT_WORKFLOW_SPEC.md`

Scope:

* Define FECHA → KB → SLOTS → CONTEXT.
* Define HORA → CONTEXT → SLOT SELECTION → APPOINTMENT_REQUEST.
* Define appointment_context contract.
* Define KB-driven slot generation.
* Define single-slot behavior.
* Define multi-slot behavior.
* Define exact-hour clarification behavior.
* Define AppointmentRequest persistence rules.
* Define Swagger validation plan.

Closure criteria:

* SDD/spec exists.
* Scope and out-of-scope are clear.
* Test plan is clear.
* Swagger validation plan is clear.
* No code touched yet.

---

## Phase 2 — P6-F.9.38: Appointment Context Authoritative Restore

Goal:

Refactor appointment context behavior so time/slot turns consume the saved appointment context as the operational source of truth.

Scope:

* Fix `apply_appointment_context_to_state`.
* Restore the full appointment context package for `hora_cita` turns.
* Do not restore only missing fields.
* Prevent recalculation from contradicting stored context.
* Add tests for available date staying available across turns.
* Add tests for no false `es_dia_disponible=false` after valid date context.

Closure criteria:

* Tests green.
* Full suite green.
* Swagger validates date → slot selection continuity.
* No real `/webhook`.
* No WhatsApp sending.

---

## Phase 3 — P6-F.9.39: KB-Driven Slot Generation

Goal:

Ensure candidate slots come from KB_Horarios, not hardcoded assumptions.

Scope:

* Monday/Tuesday/Thursday/Friday generate 15:00–17:00 and 17:00–19:00.
* Wednesday generates 15:00–18:00 only.
* Saturday/Sunday unavailable.
* Colombia holidays unavailable.
* Slot generation must respect KB schedule rows.
* No uniform weekday assumption.

Closure criteria:

* Local tests prove Wednesday special schedule.
* Local tests prove normal weekday two-slot schedule.
* Local tests prove weekend/holiday blocking.
* Swagger validates Tuesday and Wednesday flows separately.

---

## Phase 4 — P6-F.9.40: Slot Selection Rules

Goal:

Make slot selection deterministic and safe.

Scope:

* Single-slot days accept soft confirmation.
* Multi-slot days require explicit slot selection.
* Ambiguous replies do not persist AppointmentRequest.
* `la de las 5` maps correctly to second slot when two slots exist.
* `esa`, `sí`, `ok`, `me sirve` only persist when exactly one slot exists.

Closure criteria:

* Tests green for single-slot Wednesday.
* Tests green for multi-slot weekdays.
* Tests green for ambiguous replies.
* Swagger validates:

  * Wednesday + soft confirmation
  * Tuesday + explicit second slot
  * Tuesday + ambiguous reply blocked

---

## Phase 5 — P6-F.9.41: Exact-Hour Franja Clarification

Goal:

Handle exact-hour requests without promising exact arrival times.

Scope:

* If exact hour falls inside a visible franja, explain franja policy.
* Ask for confirmation before persistence.
* Do not persist immediately after exact-hour question.
* If patient confirms the proposed franja, persist.
* If exact hour is outside available franjas, ask patient to choose from visible slots.

Closure criteria:

* Tests green.
* Swagger validates:

  * `no se puede a las 4?`
  * confirmation after exact-hour clarification
  * unsupported hour outside slots

---

## Phase 6 — P6-F.9.42: AppointmentRequest Persistence Final Validation

Goal:

Validate that AppointmentRequest is created only when the workflow contract is satisfied.

Scope:

* Correct `appointment_request_decision`.
* Correct `appointment_request`.
* Correct `franja_solicitada`.
* Correct `fecha_solicitada`.
* Correct clearing of appointment_context after persistence.
* No duplicated active requests.
* No false terminal message if persistence did not happen.

Closure criteria:

* Full suite green.
* Swagger validates full appointment request happy paths.
* Swagger validates blocked paths.
* DB confirms correct rows.
* No real WhatsApp sending.
* Working tree clean.
* Phase documented as closed.

---

## Out of Scope Until Roadmap Completion

Do not touch:

* real `/webhook`
* real WhatsApp sending
* real patients
* Google Sheets adapter
* Telegram notifications
* n8n workflows
* Calendar integration
* doctor confirmation automation
* campaigns
* therapy session package tracking

These belong to later phases only after the appointment request workflow is stable.


Create the clean spec:

`docs/P6-F.9.37_KB_DRIVEN_APPOINTMENT_WORKFLOW_SPEC.md`

Then proceed with tests before implementation.

Do not patch individual symptoms again.

The next implementation must follow the architecture rule:

FECHA → KB → SLOTS → CONTEXT
HORA → CONTEXT → SLOT SELECTION → APPOINTMENT_REQUEST

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

## SDD Working Methodology — Mandatory Source of Truth

From this point forward, this project must be developed using a strict SDD methodology.

SDD means:

Specification-Driven Development.

The SDD document is the single source of truth for each phase or sprint.

No implementation may start before the current phase/sprint has a written SDD/spec that defines:

* objective
* scope
* out of scope
* workflow map
* contracts
* expected behavior
* test plan
* Swagger validation plan
* closure criteria

## Mandatory Development Style

Work must be done step by step.

Do not rush.

Do not dump many commands at once.

Do not throw random patches at symptoms.

Do not switch methodology midstream.

Use the same simple shell workflow consistently:

* `sed`
* `cat`
* `grep`
* simple Bash commands

Avoid Python patch scripts for Markdown/documentation files unless explicitly requested.

Avoid large uncontrolled code rewrites.

Every change must be understandable, reviewable, and aligned with the active SDD.

## Roadmap Structure

Work must be organized by:

* phases
* sprints
* clearly closed blocks

No more uncontrolled microphases.

A phase or sprint must have:

1. SDD/spec
2. implementation scope
3. tests
4. documentation update
5. Swagger validation when applicable
6. explicit closure note

A phase is not closed until it has been validated.

For conversational flows, local unit tests are not enough.

The final validation for a completed conversational phase must include Swagger validation through:

`/test/message-stateful`

Real `/webhook` validation remains out of scope unless explicitly planned in a controlled production activation phase.

## Phase Closure Rule

A phase is only considered closed when:

* the intended behavior is implemented
* relevant tests are green
* the workflow has been validated in Swagger when applicable
* the result is documented
* the working tree is clean or intentionally documented
* the next phase is clearly named

If a phase is partial, it must be marked as:

PARTIAL

Do not call partial work closed.

## Swagger Validation Rule

For appointment and conversational flows, each completed phase must be validated in Swagger using fresh test data.

Swagger validation must confirm:

* correct state transition
* correct patient-facing response
* correct persistence behavior
* correct `appointment_request_decision`
* correct `appointment_request` creation or non-creation
* `delivery_status = sending_skipped`
* no real WhatsApp sending

Do not use real patients for validation.

Do not enable real WhatsApp sending.

## Anti-Loop Rule

If a bug reveals architecture confusion, stop patching.

Do not keep adding field-by-field fixes.

Instead:

1. pause implementation
2. document the failure mode
3. update the SDD
4. redraw the workflow
5. continue only after the architecture is clear

The project must not continue in “patch symptoms” mode.

## Current Methodology Decision

The next work must start with:

`P6-F.9.37 — KB-Driven Appointment Workflow Architecture`

The first deliverable must be:

`docs/P6-F.9.37_KB_DRIVEN_APPOINTMENT_WORKFLOW_SPEC.md`

Only after that spec is written and accepted should implementation begin.

The architecture rule remains:

FECHA → KB → SLOTS → CONTEXT
HORA → CONTEXT → SLOT SELECTION → APPOINTMENT_REQUEST


## Working Rules

Work step by step.

Do not dump huge files unnecessarily unless replacing a context/spec file intentionally.

Prefer copy-paste friendly Bash commands.

Prefer `cat`, `sed`, `grep`, and simple shell tools for file creation and modification.

Avoid Python heredocs for Markdown documentation files unless explicitly requested.

Follow DRY principles.

Keep code clean, robust, typed, and testable.

Before adding new files, verify whether the target folder already exists.

For this repo, use `app/`, never `src/`.

---

## Environment Note

If pytest fails with:

`ModuleNotFoundError: No module named 'fastapi'`

this is an environment or dependency issue, not necessarily a code regression.

Check:

```bash
echo $VIRTUAL_ENV
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest
```

---

## Current Safety Boundaries

Do not touch yet:

* real POST `/webhook` integration
* WhatsApp sending
* real patients
* Google Sheets
* Telegram
* n8n
* doctor confirmation flow
* Calendar integration
* therapy package/session tracking
* campaigns

`WHATSAPP_SENDING_ENABLED` must remain false unless a later controlled sending block explicitly changes it.

---

## Current Source of Truth

Current true project status:

* Repo is not being deleted.
* Current work is an architecture reset for appointment workflow.
* KB must model real doctor availability.
* Wednesday may be special.
* Appointment flow must be KB-driven.
* Appointment context must be authoritative for time/slot turns.
* `/test/message-stateful` remains the safe validation surface.
* Full test suite was last confirmed locally with 247 passed before the architecture reset.
* Next block is P6-F.9.37 spec-first implementation.

---

## P6-F.9.38 Closure Note — Appointment Context Authoritative Restore

Status:

GREEN WITH KNOWN FOLLOW-UP

Implemented:

* `apply_appointment_context_to_state` now restores `appointment_context` as the authoritative operational package for `hora_cita` turns.
* The function no longer rejects context when the transient state contains a different `fecha_solicitada`.
* The function no longer restores only missing fields.
* For `hora_cita`, all fields in `APPOINTMENT_CONTEXT_FIELDS` are applied from stored context when valid context exists.

Validated locally:

* `tests/test_appointment_context.py`
* `tests/test_stateful_appointment_context_carryover.py`
* `tests/test_appointment_request_runtime_decision.py`
* `tests/test_stateful_appointment_request_wiring.py`
* `tests/test_webhook_persistence.py`
* full suite: 248 passed

Validated in Swagger through `/test/message-stateful` only:

Tuesday flow:

* `Quiero pedir una cita`
* `para el martes`
* `la de las 5`

Result:

* `fecha_solicitada=2026-06-16`
* `es_dia_disponible=true`
* `slots_candidatos=["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."]`
* `appointment_request_decision.should_persist=true`
* `appointment_request != null`
* `franja_solicitada="5:00 p. m.–7:00 p. m."`
* `delivery_status=sending_skipped`

Wednesday context validation:

* `Quiero pedir una cita`
* `para el miercoles`

Result:

* `fecha_solicitada=2026-06-17`
* `es_dia_disponible=true`
* `slots_candidatos=["3:00 p. m.–6:00 p. m."]`
* `appointment_request=null`
* `delivery_status=sending_skipped`

Known follow-up for P6-F.9.40:

* Single-slot soft confirmation is not yet accepted in Swagger.
* Example: `si, esa franja` after Wednesday single-slot context returned `skipped_unsupported_slot_selection`.
* This belongs to `P6-F.9.40 — Slot Selection Rules`, not to P6-F.9.38.
* Do not patch it as an isolated symptom.
* Implement it through the slot selection contract:
  * single-slot days accept soft confirmation
  * multi-slot days require explicit selection

Safety:

* Real `/webhook` not touched.
* Real WhatsApp sending not enabled.
* `WHATSAPP_SENDING_ENABLED=false`.
* Real patients not contacted.
* Google Sheets, Telegram, n8n, Calendar, campaigns and doctor confirmation automation remain out of scope.

Next phase:

P6-F.9.39 — KB-Driven Slot Generation


---

## P6-F.9.39 Closure Note — KB-Driven Slot Generation

Status:

GREEN

Objective:

Move appointment slot generation from hardcoded runtime assumptions toward KB-driven operational data.

Implemented:

* `CalendarService.build_slots_from_schedule_rows(...)` now builds appointment slot candidates from KB schedule rows.
* `date_resolver.resolve_requested_date(...)` now accepts optional `schedule_rows`.
* When `schedule_rows` is provided, `date_resolver` uses `CalendarService.build_slots_from_schedule_rows(...)`.
* When `schedule_rows` is not provided, `date_resolver` falls back to `CalendarService.build_default_slots(...)`.
* `node_resolve_date_context(...)` now loads KB schedule rows and passes them into `resolve_requested_date(...)`.
* KB schedule loading is protected by `settings.kb_runtime_enabled`.
* If `KB_RUNTIME_ENABLED=false`, the node does not attempt DB access.
* If KB schedule loading fails, the node logs a warning and falls back safely.

Architecture decision:

The deterministic scheduling flow is now:

FECHA → KB_Horarios → SLOTS → CONTEXT

The LLM does not decide availability or appointment slots.

Validation added:

* CalendarService unit test proving KB row values override hardcoded defaults.
* Date resolver test proving `schedule_rows` are used instead of default slots.
* Node integration test proving `node_resolve_date_context` passes KB schedule rows into `resolve_requested_date`.

Validated locally:

* `tests/test_calendar_service.py`
* `tests/test_date_resolver.py`
* `tests/test_kb_runtime_integration.py`
* full suite: 251 passed in 7.99s

Safety:

* Real `/webhook` not touched.
* Real WhatsApp sending not enabled.
* `WHATSAPP_SENDING_ENABLED=false`.
* Google Sheets, Telegram, n8n, Calendar, campaigns and doctor confirmation automation remain out of scope.
* Swagger validation still pending for this phase.

Next phase:

P6-F.9.40 — Slot Selection Rules

Known follow-up:

* Single-slot soft confirmation must be handled contractually in P6-F.9.40.
* Example from Swagger after Wednesday single-slot context: `si, esa franja` should select the only available slot, but this must be implemented as a slot-selection rule, not as a symptom patch.


---

## P6-F.9.39 Swagger Validation — KB-Driven Slot Generation

Status:

VALIDATED IN SWAGGER

Validated endpoint:

* `/test/message-stateful`

Safety:

* Real `/webhook` not used.
* Real WhatsApp sending remained disabled.
* `delivery_status=sending_skipped`.
* No real patients contacted.

Validated case — Wednesday:

Flow:

* `para una cita por favor`
* `para el dia miercoles me queda bien`

Result:

* `intent=fecha_cita`
* `nuevo_estado=ST_CITA_FRANJA`
* `fecha_solicitada=2026-06-17`
* `fecha_solicitada_texto=miércoles 17 de junio`
* `es_dia_disponible=true`
* `slots_candidatos=["3:00 p. m.–6:00 p. m."]`
* `appointment_request=null`
* `delivery_status=sending_skipped`

Validated case — Sunday:

Flow:

* `necesito una cita`
* `para el fin de semana, domingo`

Result:

* `intent=fecha_cita`
* `fecha_solicitada=2026-06-14`
* `fecha_solicitada_texto=domingo 14 de junio`
* `es_dia_disponible=false`
* `is_weekend=true`
* `slots_candidatos=[]`
* `appointment_request=null`
* `delivery_status=sending_skipped`

Conclusion:

P6-F.9.39 is validated. Slot generation now correctly uses KB schedule context in production Swagger validation.

Out-of-scope issue found:

Exact-hour clarification still uses generic weekday copy in a Wednesday single-slot context.

Example:

* User: `si por favor, es posible que lleguen a las 4?`
* Runtime context correctly preserved `slots_candidatos=["3:00 p. m.–6:00 p. m."]`
* Response incorrectly mentioned generic slots `3:00 p. m.–5:00 p. m.` and `5:00 p. m.–7:00 p. m.`

This belongs to:

P6-F.9.41 — Exact-Hour Franja Clarification

Do not patch it inside P6-F.9.39.



---

## P6-F.9.40 Closure Note — Slot Selection Rules

Status:

GREEN / VALIDATED IN SWAGGER

Objective:

Make appointment slot selection deterministic and safe after KB-driven slot generation.

Implemented:

* `resolve_requested_slot_from_message(...)` now accepts soft confirmations only when there is exactly one candidate slot.
* Single-slot confirmations such as `sí`, `sí, esa franja`, `sí por favor`, `me sirve`, `claro`, `perfecto`, `esa franja`, and similar safe confirmations resolve to the only visible slot.
* Multi-slot ambiguous confirmations remain blocked.
* Multi-slot flows still require explicit selection such as `la primera`, `la segunda`, `la de las 3`, `la de las 5`, `de 3 a 5`, or `de 5 a 7`.
* The existing non-selection guard still blocks complaints, questions, and non-selection messages before any slot can be resolved.

Files changed:

* `app/services/appointment_request_runtime.py`
* `tests/test_appointment_request_runtime_decision.py`

Local validation:

* Runtime decision tests GREEN.
* Targeted appointment context / wiring tests GREEN.
* Full suite GREEN before Swagger validation.

Swagger validation:

Endpoint:

* `/test/message-stateful`

Safety:

* Real `/webhook` not used.
* Real WhatsApp sending remained disabled.
* `WHATSAPP_SENDING_ENABLED=false`.
* `delivery_status=sending_skipped`.
* No real patients contacted.

Validated case — Wednesday single-slot soft confirmation:

Flow:

* `Para una cita , por favor`
* `para el dia miercoles me queda bien`
* `si, esa franja`

Result:

* `nuevo_estado=ST_CITA_PENDIENTE`
* `intent=hora_cita`
* `next_action=confirm_appointment_request`
* `appointment_request_decision.should_persist=true`
* `appointment_request_decision.reason=allowed_hora_cita_ready_for_human_review`
* `fecha_solicitada=2026-06-17`
* `franja_solicitada=3:00 p. m.–6:00 p. m.`
* `appointment_request != null`
* `estado_solicitud=pendiente_confirmacion`
* `delivery_status=sending_skipped`

Validated case — Tuesday multi-slot ambiguous confirmation blocked:

Flow:

* `necesito una cita`
* `para el martes`
* `si,esa franja`

Result:

* `nuevo_estado=ST_CITA_FRANJA`
* `intent=hora_cita`
* `appointment_request_decision.should_persist=false`
* `appointment_request_decision.reason=skipped_unsupported_slot_selection`
* `appointment_request=null`
* `delivery_status=sending_skipped`

Validated case — Tuesday multi-slot explicit second slot:

Flow:

* `para agendar una cita`
* `para el martes`
* `la de las 5`

Result:

* `nuevo_estado=ST_CITA_PENDIENTE`
* `intent=hora_cita`
* `next_action=confirm_appointment_request`
* `appointment_request_decision.should_persist=true`
* `appointment_request_decision.reason=allowed_hora_cita_ready_for_human_review`
* `fecha_solicitada=2026-06-16`
* `franja_solicitada=5:00 p. m.–7:00 p. m.`
* `appointment_request != null`
* `estado_solicitud=pendiente_confirmacion`
* `delivery_status=sending_skipped`

Known follow-up:

* The blocked multi-slot ambiguous case currently uses `next_action=ask_confirm_exact_hour_as_slot`, even though the issue is ambiguous slot selection rather than exact-hour clarification.
* This did not break safety because no AppointmentRequest was created.
* Do not patch this inside P6-F.9.40 unless a later response wording/state-action cleanup phase is opened.

Next phase:

P6-F.9.41 — Exact-Hour Franja Clarification

Objective:

Ensure exact-hour clarification responses use the real `slots_candidatos` from context instead of hardcoded generic weekday slots, especially for Wednesday single-slot context.


## Checkpoint — P6-F.9.41 CLOSED / GREEN / SWAGGER VALIDATED

P6-F.9.41 is now CLOSED after production-style Swagger validation through `/test/message-stateful` with `WHATSAPP_SENDING_ENABLED=false`.

Validated flow:

1. Patient starts appointment request from `ST_INIT`.
2. Patient asks for Wednesday.
3. System resolves Wednesday 2026-06-17 as available.
4. KB-driven Wednesday single-slot availability is correctly used:
   - `slots_candidatos = ["3:00 p. m.–6:00 p. m."]`
5. Patient confirms the only available franja while also asking about exact hour:
   - `"si por favor esa franja, podrian venir a las 4?"`
6. System correctly interprets the message as a valid single-slot confirmation, not as a new ambiguous exact-hour request.

Final validated Swagger result:

- `intent = hora_cita`
- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`
- `persisted_state = ST_CITA_PENDIENTE`
- `appointment_request_decision.should_persist = true`
- `appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review`
- `appointment_request_decision.estado_solicitud = pendiente_confirmacion`
- `appointment_request_decision.fecha_solicitada = 2026-06-17`
- `appointment_request_decision.franja_solicitada = 3:00 p. m.–6:00 p. m.`
- `appointment_request != null`
- `appointment_request.estado_solicitud = pendiente_confirmacion`
- `delivery_status = sending_skipped`

Important product interpretation:

- Elvira may register the available franja as patient preference.
- Elvira must not promise exact arrival at 4:00 p. m.
- The wording “La Dra. D'Aleman le confirmará la cita” is acceptable for now because final confirmation, including exact arrival feasibility, remains with the doctor.

Validated local test state:

- Full suite GREEN: `256 passed`
- Closed blocks:
  - P6-F.9.38 ✅
  - P6-F.9.39 ✅
  - P6-F.9.40 ✅
  - P6-F.9.41 ✅

Architecture note discovered during P6-F.9.41:

A deeper ordering issue exists between LangGraph transition logic and persisted appointment context restoration.

Current risk:

- `transition_state` can run before persisted `appointment_context` is available.
- This can produce cases where the final JSON shows restored `slots_candidatos`, but the state transition was already decided earlier without those slots.
- This should not be patched repeatedly with phrase-specific logic.

Future architecture debt:

- A clean future refactor should move appointment context restoration before `transition_state`.
- Candidate future graph order:
  - `sanitize_input`
  - `classify_intent`
  - `restore_appointment_context`
  - `resolve_date_context`
  - `transition_state`
  - `load_kb_context`
  - `generate_response`
- The graph should receive all deterministic state needed for transition decisions before transition logic runs.
- The graph itself should not query PostgreSQL; `main.py` should inject persisted context into the initial state.

Next planned block:

P6-F.9.42 — AppointmentRequest Persistence Final Validation

Scope reminder:

- Keep `WHATSAPP_SENDING_ENABLED=false`.
- Do not touch real `/webhook` activation.
- Do not touch real patients.
- Do not add Google Sheets, Telegram, n8n, Calendar, campaigns, or doctor confirmation automation yet.
- Focus only on final validation of AppointmentRequest persistence behavior before moving toward production readiness.

