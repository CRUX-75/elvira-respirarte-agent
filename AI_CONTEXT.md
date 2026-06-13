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


## P6-F.9.42 — AppointmentRequest Persistence Final Validation / Scope

P6-F.9.42 starts after P6-F.9.41 was closed, GREEN, and Swagger-validated.

Goal:

Validate final AppointmentRequest persistence behavior before moving toward production readiness.

Scope:

1. Validate that `appointment_request` is persisted correctly in PostgreSQL.
2. Validate that `appointment_context` is cleared after successful persistence.
3. Validate that duplicate active AppointmentRequests are not created for the same patient.
4. Validate that `persisted_state = ST_CITA_PENDIENTE` after successful request registration.
5. Document `franja_solicitada = null` at top-level response as minor non-blocking response-shape debt.

Decision:

The top-level `franja_solicitada = null` observed in the Swagger response is not a blocker because the operational persistence sources are correct:

- `appointment_request_decision.franja_solicitada` is correct.
- `appointment_request.franja_solicitada` is correct.
- `estado_solicitud = pendiente_confirmacion` is correct.
- `appointment_request != null` is correct.
- `persisted_state = ST_CITA_PENDIENTE` is correct.

This should not distract P6-F.9.42. It can be cleaned later as response-shape polish.

Out of scope:

- No graph refactor.
- No `restore_appointment_context` node yet.
- No Google Sheets.
- No Telegram.
- No n8n.
- No Calendar.
- No campaigns.
- No doctor confirmation automation.
- No real patient traffic.
- Keep `WHATSAPP_SENDING_ENABLED=false`.


---

## P6-F.9.42 Closure Note — AppointmentRequest Persistence Final Validation

Status:

GREEN / VALIDATED IN SWAGGER / DB VALIDATED

Objective:

Validate final AppointmentRequest persistence behavior before moving toward production readiness.

Local validation:

* Targeted persistence/service/repository/context tests GREEN:
  * `34 passed in 2.98s`
* Full suite GREEN:
  * `256 passed in 10.61s`
* Working tree was clean before documentation update.

Swagger validation:

Endpoint:

* `/test/message-stateful`

Safety:

* Real `/webhook` not used.
* Real WhatsApp sending remained disabled.
* `WHATSAPP_SENDING_ENABLED=false`.
* `delivery_status=sending_skipped`.
* No real patients contacted.

Validated happy path:

Phone:

* `573009420001`

Flow:

* `Quiero pedir una cita`
* `para el miercoles`
* `sí, esa franja`

Final validated result:

* `nuevo_estado = ST_CITA_PENDIENTE`
* `persisted_state = ST_CITA_PENDIENTE`
* `intent = hora_cita`
* `next_action = confirm_appointment_request`
* `appointment_request_decision.should_persist = true`
* `appointment_request_decision.reason = allowed_hora_cita_ready_for_human_review`
* `appointment_request_decision.estado_solicitud = pendiente_confirmacion`
* `appointment_request_decision.fecha_solicitada = 2026-06-17`
* `appointment_request_decision.franja_solicitada = 3:00 p. m.–6:00 p. m.`
* `appointment_request != null`
* `appointment_request.id_solicitud = SOL-20260613-080057-585753-0001`
* `appointment_request.estado_solicitud = pendiente_confirmacion`
* `appointment_request.fecha_solicitada = 2026-06-17`
* `appointment_request.franja_solicitada = 3:00 p. m.–6:00 p. m.`

DB validation:

Confirmed:

* `patients.estado_actual = ST_CITA_PENDIENTE`
* `appointment_requests.id_solicitud = SOL-20260613-080057-585753-0001`
* Active request count remained `1`, confirming no duplicate active AppointmentRequests were created for the same patient.

Persistence behavior validated:

* AppointmentRequest is created only after a valid slot/franja selection.
* Successful persistence stores the request with `estado_solicitud = pendiente_confirmacion`.
* Patient state persists as `ST_CITA_PENDIENTE`.
* Appointment context is cleared after successful persistence.
* Duplicate active requests are prevented by `AppointmentRequestService.create_or_reuse_active_request(...)`.

Known non-blocking debt:

* Top-level response field `franja_solicitada = null` may still appear in debug response after persistence.
* This is cosmetic response-shape debt only.
* Operational fields are correct in:
  * `appointment_request_decision.franja_solicitada`
  * `appointment_request.franja_solicitada`
* Do not block production readiness on this.

Architecture debt documented but not addressed in this phase:

* `/test/message-stateful` still duplicates parts of `_apply_appointment_request_runtime(...)`.
* A future cleanup may centralize runtime logic fully through the shared helper.
* This was intentionally left untouched because P6-F.9.42 was validation-only.

Out of scope respected:

* No graph refactor.
* No `restore_appointment_context` node.
* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No campaigns.
* No doctor confirmation automation.
* No real WhatsApp sending.
* No real patients.

Conclusion:

P6-F.9.42 is CLOSED.

Next recommended block:

P6-F.9.43 — Production Readiness Checklist / Controlled Activation Preparation

Purpose:

Prepare the controlled production activation checklist before touching the real WhatsApp Cloud API webhook or enabling real outbound sending.


---

## P6-F.9.43 Closure Note — Production Readiness Checklist / Controlled Activation Preparation

Status:

CLOSED / PRE-ACTIVATION READINESS VALIDATED

Objective:

Prepare and validate the controlled production readiness checklist before touching the real WhatsApp Cloud API webhook or enabling real outbound WhatsApp sending.

Documentation created:

* `docs/P6-F.9.43_PRODUCTION_READINESS_CHECKLIST.md`

Safety baseline maintained:

* `WHATSAPP_SENDING_ENABLED=false`
* Real `/webhook` not changed.
* Real WhatsApp sending not enabled.
* Real patients not contacted.
* `/test/message-stateful` remains the safe validation surface.
* Google Sheets, Telegram, n8n, Calendar, campaigns and doctor confirmation automation remain out of scope.

Environment readiness:

Validated manually without exposing secrets:

* `DATABASE_URL` present.
* `OPENAI_API_KEY` present.
* WhatsApp Cloud API credentials present.
* KB runtime configuration present.
* LangSmith configuration reviewed.
* No secrets were pasted into chat or committed to Git.
* `WHATSAPP_SENDING_ENABLED=false` remains the safety baseline.

Database schema readiness:

Validated in production PostgreSQL / pgweb:

Required tables exist:

* `appointment_requests`
* `interactions`
* `kb_rules`
* `kb_schedules`
* `patients`

Additional relevant runtime tables observed:

* `kb_services`
* `processed_messages`

AppointmentRequest status readiness:

Validated current production statuses:

* `pendiente_confirmacion`

No invalid statuses observed:

* `pendiente`
* `contraoferta`
* `completada`

KB schedules readiness:

Validated `kb_schedules` production rows:

* `HOR-01`: weekday / Lunes a viernes excepto miércoles / 15:00–19:00 / 120 minutes / max 2 / available.
* `HOR-02`: wednesday / Miércoles / 15:00–18:00 / 180 minutes / max 1 / available.
* `HOR-03`: saturday / Sábado / unavailable.
* `HOR-04`: sunday / Domingo / unavailable.

KB rules readiness:

Validated `kb_rules` production schema uses:

* `response_rule` instead of `rule_description`.

Validated relevant active rules:

* `RULE-001`: Elvira cannot confirm appointments outside `KB_Horarios`.
* `RULE-004`: If a requested slot is full, offer the next available alternative; Elvira cannot overbook patients.
* `RULE-008`: Appointment slot policy is active and aligned with KB-driven scheduling:
  * Monday, Tuesday, Thursday and Friday: 15:00–17:00 and 17:00–19:00.
  * Wednesday: 15:00–18:00.
  * Elvira may present candidate time windows as patient preference.
  * Elvira must not confirm the appointment.

Conclusion:

P6-F.9.43 is CLOSED.

The system is ready for the next review block, but not yet for real sending.

Next recommended block:

P6-F.9.44 — Real Webhook Readiness Review

Purpose:

Review the real `/webhook` code path before any controlled activation.

Important boundary:

Do not enable `WHATSAPP_SENDING_ENABLED=true` yet.


---

## P6-F.9.44 Closure Note — Real Webhook Readiness Review

Status:

CLOSED / WEBHOOK READINESS REVIEW GREEN

Objective:

Review the real `/webhook` code path before any controlled activation.

Important boundary:

This phase did not activate real WhatsApp sending.

Safety baseline maintained:

* `WHATSAPP_SENDING_ENABLED=false`
* Real outbound WhatsApp sending not enabled.
* Real patients not contacted.
* No Google Sheets, Telegram, n8n, Calendar, campaigns or doctor confirmation automation added.
* No production activation performed.

Webhook verification readiness:

Validated:

* Meta verification endpoint exists.
* The endpoint returns raw `hub.challenge` as `PlainTextResponse`.
* Invalid verification token returns `403`.

Webhook POST readiness:

Validated code path:

* Payload extraction is wrapped in `try/except`.
* Payload extraction failure returns `payload_extraction_failed`.
* Empty payload/no message returns `ignored / no_message`.
* Missing required fields returns `ignored / missing_required_message_fields`.
* Deduplication check runs before LangGraph/LLM.
* Duplicate messages return `ignored / duplicate_message`.
* Deduplication failure returns safely without processing or marking the message as processed.
* Patient is loaded/created before message processing.
* Persisted patient state is used as `estado_actual`.
* `/webhook` calls `traced_process_message(process_message, message)`.
* `/webhook` uses `_apply_appointment_request_runtime(...)`.
* Appointment runtime receives the real WhatsApp message ID as `source_interaction_id`.
* Appointment request metadata is returned in the webhook response.
* If `WHATSAPP_SENDING_ENABLED=false`, response delivery is skipped with `delivery_status=sending_skipped`.
* If WhatsApp send fails, the code stores a `send_failed` interaction but does not update patient state and does not mark the message as processed.
* Successful processing saves interaction, updates patient state, updates last message timestamp, and marks the WhatsApp message as processed.

Validated tests:

* `tests/test_webhook_persistence.py` GREEN:
  * `10 passed`
* Full suite GREEN:
  * `256 passed`

Relevant test coverage confirmed:

* Duplicate guard before LLM/LangGraph.
* Sending disabled path.
* Send failure path.
* `processed_marked=false` on failures.
* Successful path calls `mark_message_processed`.
* Successful path calls `save_interaction`.
* Successful path calls `update_patient_state`.
* Appointment runtime wiring in `/webhook`.

Known non-blocking test gap:

* The webhook appointment runtime test validates that `_apply_appointment_request_runtime(...)` is called and receives `source_interaction_id` correctly.
* It does not yet test actual AppointmentRequest persistence from the real `/webhook` path.
* This is not blocking for P6-F.9.44 because persistence was validated in P6-F.9.42 via `/test/message-stateful` and DB evidence.
* A future controlled webhook dry-run phase can add or validate this with Meta-shaped payloads while keeping sending disabled.

Conclusion:

P6-F.9.44 is CLOSED.

The real `/webhook` code path is ready for controlled dry-run validation with sending disabled.

Next recommended block:

P6-F.9.45 — Controlled Webhook Dry-Run With Sending Disabled

Purpose:

Validate the real `/webhook` path using Meta-shaped payloads while keeping `WHATSAPP_SENDING_ENABLED=false`.

Important boundary:

Do not enable real outbound WhatsApp sending yet.


---

## P6-F.9.45 Closure Note — Controlled Webhook Dry-Run With Sending Disabled

Status:

CLOSED / META-SHAPED WEBHOOK PAYLOAD VALIDATED / GREEN

Objective:

Validate the real `/webhook` path using Meta-shaped WhatsApp payloads while keeping real outbound sending disabled.

Important boundary:

This phase did not enable real WhatsApp sending.

Safety baseline maintained:

* `WHATSAPP_SENDING_ENABLED=false`
* Real outbound WhatsApp sending not enabled.
* Real patients not contacted.
* No Google Sheets, Telegram, n8n, Calendar, campaigns or doctor confirmation automation added.
* No production activation performed.

Implemented validation:

Created:

* `tests/test_whatsapp_payload_model.py`

Validated `WhatsAppPayload.extract_message()` with Meta-shaped payloads:

* Text message payload is parsed correctly.
* Status notifications return `None`.
* Unsupported message types such as `audio` return `None`.

Validated extracted fields:

* `telefono`
* `mensaje`
* `nombre`
* `msg_type`
* `whatsapp_message_id`
* `whatsapp_timestamp`

Validated real `/webhook` path with `WhatsAppPayload` instead of `FakeWhatsAppPayload`:

* `/webhook` accepts Meta-shaped text payload.
* `WHATSAPP_SENDING_ENABLED=false` produces `status=sending_skipped`.
* `whatsapp_sending_enabled=false` is returned.
* WhatsApp message ID and timestamp are preserved.
* Patient is loaded/created.
* Interaction is saved with `delivery_status=sending_skipped`.
* Patient state is updated.
* Patient last message timestamp is updated.
* Message is marked as processed only after successful processing.
* No real WhatsApp send is attempted.

Local validation:

* Full suite GREEN:
  * `260 passed in 9.45s`

Conclusion:

P6-F.9.45 is CLOSED.

The real webhook path now has local test coverage with Meta-shaped WhatsApp payloads while sending remains disabled.

Next recommended block:

P6-F.9.46 — Production Meta Webhook Dry-Run Plan

Purpose:

Prepare a controlled production dry-run using real Meta webhook delivery while keeping `WHATSAPP_SENDING_ENABLED=false`.

Important boundary:

Do not enable real outbound WhatsApp sending yet.


---

## P6-F.9.46 Planning Note — Production Meta Webhook Dry-Run Plan

Status:

PLANNED / DOCUMENTED

Repository status at planning time:

* Branch: main
* Working tree before P6-F.9.46 doc creation: clean
* Latest full suite before this planning block: 260 passed
* Latest committed doc: `docs/P6-F.9.46_PRODUCTION_META_WEBHOOK_DRY_RUN_PLAN.md`
* Commit: `88c9eed Document production Meta webhook dry-run plan`

Objective:

Prepare the first controlled production dry-run where Meta delivers a real inbound WhatsApp webhook event to the production `/webhook` endpoint while outbound sending remains disabled.

Safety baseline:

* `WHATSAPP_SENDING_ENABLED=false`
* Real outbound WhatsApp sending remains disabled.
* Real patients must not be contacted.
* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No campaigns.
* No doctor confirmation automation.
* No runtime code changes unless a real blocker is found.

Scope:

P6-F.9.46 is documentation and operational planning for real inbound Meta webhook reception in production with sending disabled.

The first dry-run message should be a simple controlled greeting, for example:

`Hola, prueba controlada`

The first dry-run must not start an appointment flow.

Expected validation evidence:

* Production `/webhook` receives a real Meta event.
* Payload extraction succeeds.
* Real Meta `wamid` is preserved.
* Patient row is created or reused.
* Interaction is saved.
* `processed_messages` records the real Meta `wamid`.
* `delivery_status=sending_skipped`.
* `whatsapp_sending_enabled=false`.
* No outbound WhatsApp message is sent.
* No AppointmentRequest is created from the simple greeting.

Next active block:

P6-F.9.46 — Production Meta Webhook Dry-Run Execution

Important boundary:

Do not enable `WHATSAPP_SENDING_ENABLED=true`.

Do not move to real sending until P6-F.9.46 is executed, validated, documented, and closed.


---

## P6-F.9.46 Closure Note — Production Meta Webhook Run

Status:

CLOSED / PRODUCTION META WEBHOOK VALIDATED / OWNER-ACCEPTED SUCCESSFUL RUN

Validation date:

2026-06-13

Validated by:

Project owner / operator

Production evidence:

* Production app was running successfully on EasyPanel.
* `/ready` returned production-ready status before execution.
* Meta webhook configuration was confirmed in Meta Developer Console:
  * Callback URL: `https://elvira.genflowautomation.com/webhook`
  * App mode: Live
  * WhatsApp webhook field `messages` subscribed
* Real Meta inbound webhook reached production `/webhook`.
* Production logs showed multiple successful `POST /webhook HTTP/1.1 200 OK`.
* Real Meta WhatsApp message IDs (`wamid...`) were received and preserved.
* Status notifications without messages were ignored correctly with `reason=no_message`.
* Patient was loaded/created correctly.
* Interaction logs were written.
* State transitions executed correctly through the real production webhook path.

Validated real conversation flow:

1. `Hola, quisiera agendar una cita con la doctora`
   * intent: `cita`
   * transition: `ST_CITA_PENDIENTE -> ST_CITA_FECHA`
   * response asked for preferred day.

2. `Para el día lunes`
   * intent: `fecha_cita`
   * Monday 2026-06-15 was correctly identified as Colombia holiday:
     `Sagrado Corazón de Jesús`
   * state remained `ST_CITA_FECHA`
   * response correctly asked for another weekday.

3. `Entiendo, entonces el martes`
   * intent: `fecha_cita`
   * transition: `ST_CITA_FECHA -> ST_CITA_FRANJA`
   * Tuesday 2026-06-16 was correctly accepted.
   * Available slots were presented:
     * `3:00 p. m. - 5:00 p. m.`
     * `5:00 p. m. - 7:00 p. m.`

4. `La de las 5`
   * intent: `hora_cita`
   * transition: `ST_CITA_FRANJA -> ST_CITA_PENDIENTE`
   * response confirmed request registration for the selected franja.
   * Elvira did not confirm the appointment as final; she indicated that Dra. D'Aleman will confirm.

Observed delivery behavior:

* Logs showed real outbound WhatsApp API requests to Graph API.
* Delivery status observed: `sent`.
* `whatsapp_sending_enabled=True` was observed during the run.
* This run is therefore accepted by the owner as a successful controlled production webhook + real sending validation, not merely a disabled-sending dry-run.

Important owner decision:

The owner/operator explicitly validated this production run as successful.

Conclusion:

P6-F.9.46 is CLOSED as an owner-accepted successful production Meta webhook validation.

The production webhook path is proven end-to-end:

Meta inbound message
-> production `/webhook`
-> parsing
-> state machine
-> KB/date logic
-> appointment slot flow
-> interaction persistence
-> processed message handling
-> outbound WhatsApp response

Next recommended block:

P6-F.9.47 — Post-Run Safety Reconciliation And Controlled Next-Step Decision

Purpose:

Reconcile documentation after the successful owner-accepted production run, confirm the intended value of `WHATSAPP_SENDING_ENABLED` for the next phase, and decide whether the next controlled production block should continue with sending enabled or return to disabled mode.

Standing boundaries until explicitly changed:

* Do not open to uncontrolled real patients.
* Do not run campaigns.
* Do not add Google Sheets.
* Do not add Telegram.
* Do not add n8n.
* Do not add Calendar.
* Do not add doctor confirmation automation.
* Keep production testing controlled and operator-supervised.


---

## P6-F.9.47 Safety Reconciliation Note — Sending Disabled After Production Run

Status:

CLOSED / SAFETY BASELINE RESTORED

Context:

After the successful owner-accepted P6-F.9.46 production Meta webhook validation run, the operator restored the production safety baseline.

Current production safety state:

* `WHATSAPP_SENDING_ENABLED=false`
* Real outbound WhatsApp sending is disabled again.
* Production webhook remains validated.
* Meta inbound path remains confirmed.
* No uncontrolled patient activation is open.
* No campaigns are active.
* No Google Sheets, Telegram, n8n, Calendar, or doctor confirmation automation has been added.

Operational decision:

The successful production run validated end-to-end WhatsApp behavior, but the system is now intentionally returned to safe mode before any next production step.

Next recommended block:

P6-F.9.48 — Controlled Production Readiness Review Before Wider Testing

Purpose:

Review whether the next controlled test should stay internal-only, whether sending should remain disabled, and what exact evidence is required before allowing any broader patient-facing usage.

Standing boundaries:

* Do not open to uncontrolled real patients.
* Do not run campaigns.
* Do not enable real sending again without a named controlled phase.
* Keep all future production tests operator-supervised.


---

## P6-F.9.48.1 Closure Note — Production Evidence Review

Status:

CLOSED / PRODUCTION DB EVIDENCE VALIDATED

Context:

After the owner-accepted P6-F.9.46 production Meta webhook run, production database evidence was reviewed to confirm that the real WhatsApp conversation was persisted correctly.

Validated patient evidence:

* Controlled production phone: `4917655660163`
* Final patient state: `ST_CITA_PENDIENTE`
* Patient `updated_at` aligned with the production run timestamp.

Validated interaction evidence:

The real production WhatsApp flow was persisted in `interactions` with real Meta `wamid` values and `delivery_status=sent`.

Validated flow:

1. `Hola, quisiera agendar una cita con la doctora`
   * intent: `cita`
   * transition: `ST_CITA_PENDIENTE -> ST_CITA_FECHA`
   * next_action: `ask_preferred_date`

2. `Para el día lunes`
   * intent: `fecha_cita`
   * state_reason: `unavailable_date_guard`
   * Monday 2026-06-15 was correctly treated as Colombia holiday:
     `Sagrado Corazón de Jesús`
   * transition: `ST_CITA_FECHA -> ST_CITA_FECHA`

3. `Entiendo, entonces el martes`
   * intent: `fecha_cita`
   * transition: `ST_CITA_FECHA -> ST_CITA_FRANJA`
   * next_action: `ask_preferred_time`
   * Tuesday slots were presented:
     * `3:00 p. m. - 5:00 p. m.`
     * `5:00 p. m. - 7:00 p. m.`

4. `La de las 5`
   * intent: `hora_cita`
   * transition: `ST_CITA_FRANJA -> ST_CITA_PENDIENTE`
   * next_action: `confirm_appointment_request`
   * response registered the request and left final confirmation to Dra. D'Aleman.

Validated processed message evidence:

* All four real Meta inbound messages were stored in `processed_messages`.
* Real `wamid...` values were preserved.
* Processing timestamps aligned with the run:
  * `2026-06-13T14:02:35Z`
  * `2026-06-13T14:02:55Z`
  * `2026-06-13T14:03:12Z`
  * `2026-06-13T14:03:30Z`

Validated AppointmentRequest evidence:

* AppointmentRequest was created:
  * `SOL-20260613-090329-503926-0163`
* This confirms that the production `/webhook` path reached the AppointmentRequest persistence layer during the real run.

Important schema note:

The production `interactions` table uses:

* `mensaje`
* `respuesta`
* `nuevo_estado`

It does not use:

* `mensaje_usuario`
* `estado_nuevo`

Operational conclusion:

P6-F.9.48.1 confirms that production persistence worked end-to-end:

Meta inbound message
-> production `/webhook`
-> interaction persistence
-> processed message deduplication record
-> patient state update
-> AppointmentRequest creation

Current safety state:

* Operator restored `WHATSAPP_SENDING_ENABLED=false` after the production run.
* No uncontrolled patient activation is open.
* Future production tests must remain controlled and explicitly named.

Next recommended block:

P6-F.9.48.2 — AppointmentRequest Detail Verification And Cleanup Decision

Purpose:

Verify the final AppointmentRequest fields for `SOL-20260613-090329-503926-0163`, especially:

* `estado_solicitud`
* `fecha_solicitada`
* `franja_solicitada`
* duplicate active request behavior
* whether any cleanup/reset is needed for the controlled test patient before future tests.


---

## P6-F.9.48.2 Closure Note — AppointmentRequest Detail Verification And Cleanup Decision

Status:

CLOSED / APPOINTMENT REQUEST EXISTENCE AND ACTIVE COUNT VERIFIED

Context:

After P6-F.9.48.1 validated production evidence from the owner-accepted production Meta webhook run, the AppointmentRequest created during the run was checked directly in production PostgreSQL.

Verified controlled patient:

* `telefono`: `4917655660163`
* `nombre`: `Nabit Mikan`
* Final patient state: `ST_CITA_PENDIENTE`

Verified AppointmentRequest:

* `id_solicitud`: `SOL-20260613-090329-503926-0163`
* Active AppointmentRequest count for the controlled phone: `1`

Validation result:

* The production run created an AppointmentRequest.
* The controlled patient ended in `ST_CITA_PENDIENTE`.
* Duplicate active AppointmentRequests were not observed.
* `active_requests = 1` confirms no duplicate active request was created for the controlled phone.

Field detail note:

The exact values for `estado_solicitud`, `fecha_solicitada`, and `franja_solicitada` were not copied into this closure note. The validated operational evidence is limited to request existence, controlled phone ownership, final patient state, and active request count.

Cleanup decision:

Do not delete the production test evidence automatically.

The controlled production test data may remain as audit evidence unless the operator explicitly decides to reset the test patient before future controlled tests.

Current safety state:

* `WHATSAPP_SENDING_ENABLED=false` has been restored.
* No uncontrolled patient activation is open.
* No campaigns are active.
* Future production tests must remain explicitly named and operator-supervised.

Next recommended block:

P6-F.9.49 — Controlled Next Production Test Definition

Purpose:

Define the next controlled production test before enabling real sending again, if sending is needed at all.

Recommended options:

1. Keep sending disabled and continue DB/log verification only.
2. Run one short controlled real-sending test with the same internal phone.
3. Reset or archive controlled patient state before future appointment-flow tests.
4. Start designing the future human review handoff, without implementing Google Sheets, Telegram, n8n, Calendar, or doctor confirmation automation yet.

Standing boundaries:

* Do not open to uncontrolled real patients.
* Do not run campaigns.
* Do not enable real sending again without a named controlled phase.
* Do not add Google Sheets, Telegram, n8n, Calendar, or doctor confirmation automation until explicitly scoped.



---

## P6-F.9.49 Closure Note — Controlled Next Production Test Definition

Status:

CLOSED / DECISION RECORDED / NO NEW PRODUCTION TEST REQUIRED NOW

Context:

P6-F.9.49 was opened after the owner-accepted production Meta webhook run, post-run safety restoration, production DB evidence review, and AppointmentRequest existence verification.

Controlled production evidence already validated:

* Real Meta inbound webhook delivery.
* Production `/webhook` execution.
* Payload parsing.
* Real `wamid` preservation.
* State transition flow.
* Colombia holiday blocking.
* KB-driven slot presentation.
* Slot selection.
* AppointmentRequest creation.
* Interaction persistence.
* Processed message persistence.
* Patient state persistence.
* Real outbound WhatsApp sending during the controlled run.

Controlled production phone:

* `4917655660163`

Controlled patient name:

* `Nabit Mikan`

Validated AppointmentRequest:

* `SOL-20260613-090329-503926-0163`

Final validated patient state:

* `ST_CITA_PENDIENTE`

Decision:

No additional real production sending test is required at this moment.

Reason:

The previous controlled production run already validated the end-to-end production path. Repeating another real-sending test now would add limited value and increase operational risk unnecessarily.

Current safety baseline:

* `WHATSAPP_SENDING_ENABLED=false`
* No uncontrolled real patients.
* No campaigns.
* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No doctor confirmation automation.
* No real sending without a newly named controlled phase.

Controlled test data decision:

Do not delete the existing controlled production evidence automatically.

The controlled patient and AppointmentRequest may remain as audit evidence unless a future clean-state test explicitly requires reset or archival.

Accepted next direction:

Move to human review handoff design only.

Next phase:

P6-F.9.50 — Human Review Handoff Spec

Purpose:

Define how a persisted `AppointmentRequest` in `pendiente_confirmacion` moves into human review by Dra. D'Aleman before implementing any external adapter.

Important boundary:

P6-F.9.50 must be spec/design only at first.

Do not implement yet:

* Google Sheets adapter
* Telegram notification
* n8n workflow
* Calendar integration
* doctor confirmation automation
* campaigns
* therapy package/session tracking
* real patient activation
* real WhatsApp sending

Conclusion:

P6-F.9.49 is CLOSED.

Next starting point:

Create the spec for P6-F.9.50 — Human Review Handoff Spec.

P6-F.9.50 Spec Note — Human Review Handoff Spec

Status:

SPEC / DESIGN ONLY

Objective:

Define how a persisted AppointmentRequest in pendiente_confirmacion moves into human review by Dra. D'Aleman before implementing any external adapter.

Spec created:

docs/P6-F.9.50_HUMAN_REVIEW_HANDOFF_SPEC.md

Core decision:

Elvira registers requests.

Dra. D'Aleman confirms appointments.

PostgreSQL remains the source of truth.

External tools such as Google Sheets, Telegram, n8n, or Calendar may later become adapters or notification surfaces, but they must not own appointment lifecycle logic.

Human review object minimum required fields:

id_solicitud
telefono
nombre_paciente
fecha_solicitada
franja_solicitada
servicio_solicitado
direccion_paciente
estado_solicitud
fecha_creacion
ultima_actualizacion
notas_paciente
source_channel
source_interaction_id

Doctor actions defined:

confirm request
request missing data
propose alternative
reschedule
cancel request
close request

Status contract remains:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada

Invalid statuses remain forbidden:

pendiente
contraoferta
completada

Important design decision:

A contraoffer remains represented as pendiente_confirmacion, not as a separate status.

Adapter boundaries:

Google Sheets may later act as a visual inbox only.
Telegram may later notify the doctor or provide action buttons only through backend validation.
n8n may later orchestrate auxiliary notifications only.
Calendar may later mirror confirmed appointments only.
None of these tools may become the source of truth.

Current safety baseline:

WHATSAPP_SENDING_ENABLED=false
No uncontrolled real patients.
No campaigns.
No Google Sheets implementation.
No Telegram implementation.
No n8n workflow.
No Calendar integration.
No doctor confirmation automation.
No real WhatsApp sending.

Recommended next phase:

P6-F.9.51 — Human Review Internal Model And Service Contract

Purpose:

Create the internal backend contract for human review actions without connecting Google Sheets, Telegram, n8n, or Calendar.

P6-F.9.51 Spec Note — Human Review Internal Model And Service Contract

Status:

SPEC / CONTRACT / PRE-IMPLEMENTATION

Objective:

Define the internal backend contract for human review actions before connecting any external adapter.

Spec created:

docs/P6-F.9.51_HUMAN_REVIEW_INTERNAL_MODEL_AND_SERVICE_CONTRACT.md

Core decision:

The human review lifecycle must be controlled by backend service logic.

PostgreSQL remains the source of truth.

External tools remain out of scope and may later act only as adapters.

Recommended internal model:

HumanReviewAction

Recommended service:

HumanReviewService

Recommended service method:

apply_action(action: HumanReviewAction) -> HumanReviewResult

Supported actions:

confirm
request_missing_data
propose_alternative
reschedule
cancel
close

Supported status contract remains:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada

Important design decisions:

A contraoffer remains represented as pendiente_confirmacion.
P6-F.9.51 must not send patient messages.
The service result may prepare should_notify_patient and patient_message, but actual sending belongs to a later named phase.
Doctor-side lifecycle events should eventually use a dedicated appointment_request_events table rather than overloading patient-facing interactions.

Current safety baseline:

WHATSAPP_SENDING_ENABLED=false
No uncontrolled real patients.
No campaigns.
No Google Sheets implementation.
No Telegram implementation.
No n8n workflow.
No Calendar integration.
No doctor confirmation automation.
No real WhatsApp sending.

Recommended next phase:

P6-F.9.52 — Human Review Service Tests

Purpose:

Create tests for the internal human review service contract before implementation.

Boundary:

No external adapters.

No API endpoints.

No Google Sheets.

No Telegram.

No n8n.

No Calendar.

No real WhatsApp sending.


---

## P6-F.9.52 / P6-F.9.53 Closure Note — Human Review Service Tests And Minimal Implementation

Status:

GREEN / INTERNAL SERVICE CONTRACT IMPLEMENTED

Context:

After P6-F.9.51 documented the Human Review Internal Model And Service Contract, the project moved into tests-first implementation.

P6-F.9.52 created the internal service tests first.

Initial expected RED result:

* `ModuleNotFoundError: No module named 'app.models.human_review'`

P6-F.9.53 then added the minimal internal model and service implementation required to satisfy the tests.

Implemented files:

* `app/models/human_review.py`
* `app/services/human_review_service.py`
* `tests/test_human_review_service.py`

Implemented models:

* `HumanReviewAction`
* `HumanReviewResult`

Implemented service:

* `HumanReviewService`
* `apply_action(action: HumanReviewAction) -> HumanReviewResult`

Supported actions:

* `confirm`
* `request_missing_data`
* `propose_alternative`
* `reschedule`
* `cancel`
* `close`

Validated behavior:

* `confirm` moves `pendiente_confirmacion` to `confirmada`.
* `request_missing_data` moves `pendiente_confirmacion` to `pendiente_datos`.
* `propose_alternative` keeps status as `pendiente_confirmacion`.
* `reschedule` moves `confirmada` to `reagendada`.
* `cancel` moves active status to `cancelada`.
* `close` moves `confirmada` to `cerrada`.
* Invalid actions are rejected.
* Missing requests are rejected.
* Forbidden transition from `cancelada` to `confirmada` is rejected.
* Forbidden transition from `cerrada` to active status is rejected.
* Missing required fields are rejected.
* The service does not send WhatsApp messages.
* The service only prepares `should_notify_patient` and `patient_message`.

Targeted validation:

* `tests/test_human_review_service.py`
* Result: `12 passed`

Important boundary respected:

* No Google Sheets adapter.
* No Telegram implementation.
* No n8n workflow.
* No Calendar integration.
* No API endpoint.
* No doctor confirmation automation.
* No real WhatsApp sending.
* `WHATSAPP_SENDING_ENABLED=false` remains the safety baseline.

Architecture note:

This implementation is intentionally internal-only.

The service prepares human review lifecycle decisions but does not yet persist through the real PostgreSQL repository beyond the repository contract expected by the tests.

Next recommended phase:

P6-F.9.54 — Human Review Repository Contract Review

Purpose:

Review the existing AppointmentRequest repository capabilities and decide whether new repository methods are needed before wiring HumanReviewService to real PostgreSQL.

Boundary:

Do not add external adapters yet.


---

## P6-F.9.54 Closure Note — Human Review Repository Contract Alignment

Status:

GREEN / CONTRACT ALIGNED WITH REAL REPOSITORY

Context:

After P6-F.9.52/P6-F.9.53 introduced the first internal HumanReviewService tests and implementation, P6-F.9.54 reviewed the real AppointmentRequest repository contract before deeper wiring.

Repository inspection confirmed:

* `AppointmentRequestRepository` already defines:
  * `save(request)`
  * `update(request)`
  * `get_by_id(id_solicitud)`
  * `find_active_by_telefono(telefono)`
* `PostgresAppointmentRequestRepository` already implements:
  * `get_by_id(id_solicitud)`
  * `update(request)`
* `AppointmentRequest` is a Pydantic model, not a dict.

Decision:

Do not introduce duplicate methods such as:

* `find_by_id_solicitud`
* `update_status`

Instead, align `HumanReviewService` with the existing repository contract:

* read with `repository.get_by_id(id_solicitud)`
* update via `repository.update(updated_request)`

Implemented alignment:

* `HumanReviewService` now consumes real `AppointmentRequest` model instances.
* `HumanReviewService` uses `request.model_copy(update=...)` before repository update.
* Tests now use an `AppointmentRequest` model fake instead of dict-shaped request data.
* Fake test repository now exposes `get_by_id(...)` and `update(...)`, matching the real protocol.

Validated behavior remains:

* confirm
* request_missing_data
* propose_alternative
* reschedule
* cancel
* close
* invalid action rejection
* missing request rejection
* forbidden transition rejection
* missing required field rejection
* no WhatsApp sending

Important field mapping decisions:

* confirm may write `fecha_confirmada` / `franja_confirmada`.
* request_missing_data writes missing field information into `observaciones` for now.
* propose_alternative keeps status as `pendiente_confirmacion` and uses `fecha_aceptada` / `franja_aceptada` as temporary internal fields for the proposed alternative.
* reschedule writes `fecha_confirmada` / `franja_confirmada` and `motivo_reagendamiento`.
* cancel writes `motivo_cancelacion`.
* all successful actions write `updated_by`.

Boundary respected:

* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No API endpoint.
* No doctor confirmation automation.
* No real WhatsApp sending.

Next recommended phase:

P6-F.9.55 — Human Review PostgreSQL Repository Integration Test

Purpose:

Validate HumanReviewService against the real PostgresAppointmentRequestRepository contract using the existing SQLite-style repository test infrastructure, without adding external adapters or endpoints.


---

## P6-F.9.55 Closure Note — Human Review PostgreSQL Repository Integration Test

Status:

GREEN / REPOSITORY INTEGRATION VALIDATED

Objective:

Validate `HumanReviewService` against the real `PostgresAppointmentRequestRepository` contract using the existing SQLite-style repository test infrastructure.

Context:

P6-F.9.54 aligned `HumanReviewService` with the real repository contract:

* `repository.get_by_id(id_solicitud)`
* `repository.update(request)`

P6-F.9.55 validates that this alignment works with the concrete repository implementation.

Implemented tests:

* `test_human_review_service_confirms_request_with_postgres_repository`
* `test_human_review_service_cancels_request_with_postgres_repository`
* `test_human_review_service_rejects_forbidden_transition_with_postgres_repository`

Validated behavior:

* HumanReviewService can confirm an AppointmentRequest through PostgresAppointmentRequestRepository.
* Confirm action persists:
  * `estado_solicitud = confirmada`
  * `fecha_confirmada`
  * `franja_confirmada`
  * `updated_by`
* HumanReviewService can cancel an AppointmentRequest through PostgresAppointmentRequestRepository.
* Cancel action persists:
  * `estado_solicitud = cancelada`
  * `motivo_cancelacion`
  * `updated_by`
* Forbidden transition from `cancelada` to `confirmada` is rejected.
* Forbidden transition does not mutate the stored AppointmentRequest.

Boundary respected:

* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No API endpoint.
* No doctor confirmation automation.
* No real WhatsApp sending.
* No production DB touched.

Conclusion:

HumanReviewService is now validated against the real repository contract using local test infrastructure.

Next recommended phase:

P6-F.9.56 — Human Review API Boundary Spec

Purpose:

Define, before implementation, whether a future internal backend endpoint is needed for doctor review actions, and what its request/response contract should be.

Boundary:

Spec only first.

No external adapters.

No real sending.

P6-F.9.56 Spec Note — Human Review API Boundary Spec

Status:

SPEC / API BOUNDARY ONLY

Objective:

Define the backend API boundary for future doctor/human review actions before implementing any endpoint.

Spec created:

docs/P6-F.9.56_HUMAN_REVIEW_API_BOUNDARY_SPEC.md

Current validated internal contract:

HumanReviewAction
HumanReviewResult
HumanReviewService
HumanReviewService.apply_action(action)
Repository contract:
repository.get_by_id(id_solicitud)
repository.update(request)

Core decision:

A backend API boundary should be introduced in a later implementation phase so future doctor-facing surfaces cannot mutate appointment state directly.

Recommended future endpoint:

POST /internal/human-review/actions

The endpoint should map request body to HumanReviewAction and response body to HumanReviewResult.

Supported actions remain:

confirm
request_missing_data
propose_alternative
reschedule
cancel
close

Notification boundary:

The first API implementation must not send WhatsApp messages.

Allowed:

return should_notify_patient
return patient_message

Not allowed yet:

call WhatsApp Cloud API
update interactions as if a message was sent
trigger Telegram
trigger n8n
trigger Google Sheets
trigger Calendar

Security boundary:

The endpoint must be internal/admin only.

Recommended first implementation:

Require an internal header such as X-Internal-Admin-Token.
Load the secret from environment variables.
Do not hardcode secrets.
Do not expose this endpoint publicly without protection.

HTTP strategy:

200 OK for successful business actions.
200 OK for known business rejections returned by HumanReviewService.
422 only for Pydantic/request validation errors.
500 only for unexpected infrastructure errors.

Audit note:

P6-F.9.56 does not implement audit events.

Future recommended audit direction:

Create appointment_request_events table in a later phase.
Do not overload patient-facing interactions with doctor-side lifecycle events.

Boundary respected:

No API endpoint implemented.
No Google Sheets.
No Telegram.
No n8n.
No Calendar.
No doctor confirmation automation.
No real WhatsApp sending.
No production activation.

Recommended next phase:

P6-F.9.57 — Human Review API Endpoint Tests

Purpose:

Create tests for the internal endpoint boundary before implementing it.


---

## P6-F.9.57 / P6-F.9.58 Closure Note — Human Review API Endpoint Tests And Minimal Implementation

Status:

GREEN / INTERNAL API ENDPOINT IMPLEMENTED

Context:

P6-F.9.57 created RED tests for the internal human review endpoint.

Initial expected RED result:

* `404 Not Found`

Reason:

The endpoint `/internal/human-review/actions` did not exist yet.

P6-F.9.58 then implemented the minimal endpoint directly in `app/main.py`, consistent with the current FastAPI structure where routes are mounted directly in `main.py`.

Implemented endpoint:

* `POST /internal/human-review/actions`

Implemented helpers:

* `get_internal_admin_token()`
* `create_human_review_repository()`
* `_validate_internal_admin_token(...)`

Implemented security boundary:

* Endpoint requires `X-Internal-Admin-Token`.
* Missing or invalid token returns `401`.
* Token is read through `get_internal_admin_token()`.

Implemented service wiring:

* Request body maps to `HumanReviewAction`.
* Endpoint creates `HumanReviewService`.
* Endpoint uses `PostgresAppointmentRequestRepository(engine)`.
* Response returns `HumanReviewResult.model_dump()`.

Validated API behavior:

* Missing internal admin token is rejected.
* Invalid internal admin token is rejected.
* Valid confirm action returns structured success.
* Invalid business action returns structured business error.
* Endpoint does not send WhatsApp messages.
* Endpoint only returns `should_notify_patient` and `patient_message`.

Boundary respected:

* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No doctor confirmation automation.
* No patient notification sending.
* No WhatsApp sending.
* No production activation.

Important note:

The endpoint is internal/admin-facing only.

It must not be exposed for uncontrolled public usage without a real internal admin token configured.

Next recommended phase:

P6-F.9.59 — Human Review API Config Hardening

Purpose:

Add a real `internal_admin_token` field to settings/config instead of relying only on `getattr(settings, "internal_admin_token", None)`, and document required environment variable for production readiness.

Boundary:

No external adapters.

No patient notification sending.


---

## P6-F.9.59 Closure Note — Human Review API Config Hardening

Status:

GREEN / CONFIG CONTRACT HARDENED

Context:

P6-F.9.58 implemented the internal human review endpoint with token validation through:

* `get_internal_admin_token()`

Initially, the token was read with:

* `getattr(settings, "internal_admin_token", None)`

This worked defensively but did not define a real configuration contract.

P6-F.9.59 hardened the config boundary.

Implemented:

* Added `internal_admin_token: str | None = None` to `app/config.py`.
* Updated `get_internal_admin_token()` to read `settings.internal_admin_token` directly.
* Added test coverage proving `get_internal_admin_token()` reads the configured settings field.

Validated behavior:

* Internal human review endpoint still requires `X-Internal-Admin-Token`.
* Missing token returns `401`.
* Invalid token returns `401`.
* Valid token allows business action handling.
* Endpoint still does not send WhatsApp messages.
* Endpoint still only returns `should_notify_patient` and `patient_message`.

Operational note:

For production readiness, `INTERNAL_ADMIN_TOKEN` must be configured as an environment variable before using the internal human review endpoint.

Security note:

Do not hardcode this token.

Do not expose the endpoint for uncontrolled public usage.

Boundary respected:

* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No doctor confirmation automation.
* No patient notification sending.
* No WhatsApp sending.
* No production activation.

Next recommended phase:

P6-F.9.60 — Human Review API Swagger Dry-Run Plan

Purpose:

Define and then validate the internal human review endpoint through Swagger using a controlled local/preproduction AppointmentRequest.

Boundary:

No real patient notification sending.


---

## P6-F.9.59 Fix Note — Config Syntax Correction

Status:

GREEN / SYNTAX FIXED

Context:

During P6-F.9.59, `internal_admin_token` was added to `app/config.py`.

A shell insertion introduced a stray leading `n` before the field:

`n    internal_admin_token: str | None = None`

This caused a syntax error during pytest collection.

Fix applied:

* Corrected the line to:
  * `internal_admin_token: str | None = None`

Validation required:

* `tests/test_human_review_api.py`
* full suite

Boundary respected:

* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No WhatsApp sending.
* No production activation.


---

## P6-F.9.59 Closure Note — Human Review API Config Hardening

Status:

GREEN / CONFIG CONTRACT HARDENED

Context:

P6-F.9.58 implemented the internal human review endpoint with token validation through:

* `get_internal_admin_token()`

Initially, the token was read with:

* `getattr(settings, "internal_admin_token", None)`

This worked defensively but did not define a real configuration contract.

P6-F.9.59 hardened the config boundary.

Implemented:

* Added `internal_admin_token: str | None = None` to `app/config.py`.
* Updated `get_internal_admin_token()` to read `settings.internal_admin_token` directly.
* Added test coverage proving `get_internal_admin_token()` reads the configured settings field.

Validated behavior:

* Internal human review endpoint still requires `X-Internal-Admin-Token`.
* Missing token returns `401`.
* Invalid token returns `401`.
* Valid token allows business action handling.
* Endpoint still does not send WhatsApp messages.
* Endpoint still only returns `should_notify_patient` and `patient_message`.

Operational note:

For production readiness, `INTERNAL_ADMIN_TOKEN` must be configured as an environment variable before using the internal human review endpoint.

Security note:

Do not hardcode this token.

Do not expose the endpoint for uncontrolled public usage.

Boundary respected:

* No Google Sheets.
* No Telegram.
* No n8n.
* No Calendar.
* No doctor confirmation automation.
* No patient notification sending.
* No WhatsApp sending.
* No production activation.

Next recommended phase:

P6-F.9.60 — Human Review API Swagger Dry-Run Plan

Purpose:

Define and then validate the internal human review endpoint through Swagger using a controlled local/preproduction AppointmentRequest.

Boundary:

No real patient notification sending.

P6-F.9.60 Plan Note — Human Review API Swagger Dry-Run Plan

Status:

PLAN / NO RUNTIME CHANGES

Objective:

Define the controlled Swagger dry-run for the internal human review endpoint before using it in any real operational workflow.

Plan created:

docs/P6-F.9.60_HUMAN_REVIEW_API_SWAGGER_DRY_RUN_PLAN.md

Current implemented endpoint:

POST /internal/human-review/actions

Required header:

X-Internal-Admin-Token

Required environment variable:

INTERNAL_ADMIN_TOKEN

Safety baseline:

WHATSAPP_SENDING_ENABLED=false
no uncontrolled real patients
no campaigns
no Google Sheets
no Telegram
no n8n
no Calendar
no doctor confirmation automation
no patient notification sending

Planned Swagger cases:

missing token returns 401
invalid token returns 401
confirm request mutates controlled AppointmentRequest to confirmada
invalid action returns structured business error
forbidden transition returns structured business error
no WhatsApp message is sent
no external adapter is triggered

Important boundary:

The endpoint may return should_notify_patient and patient_message, but it must not send WhatsApp messages in this phase.

Next recommended phase:

P6-F.9.61 — Human Review API Swagger Dry-Run Execution

Purpose:

Execute the Swagger dry-run using controlled data and document evidence.

Boundary:

No real patient notification sending.

---

## P6-F.9.62 / P6-F.9.63 / P6-F.9.64 / P6-F.9.65 Closure Note — Google Sheets Human Review Inbox Foundation

Status:

GREEN / COMMITTED / READY FOR NEXT BLOCK

Context:

The project moved from pure HumanReviewService/API design into the Google Sheets human review inbox foundation for Dra. D'Aleman.

Operational product decision:

Elvira registers appointment requests.

Dra. D'Aleman reviews them in Google Sheets.

PostgreSQL remains the source of truth.

Google Sheets is only the human-facing review inbox, not the owner of appointment lifecycle logic.

The doctor should not manually edit `estado_solicitud`.

The doctor should use `accion_doctora`.

A later backend reader will translate doctor actions into HumanReviewAction and apply them through HumanReviewService.

## P6-F.9.62 — Google Sheets Human Review Inbox Alignment

Status:

CLOSED / COMMITTED

Commit:

26c011b Document Google Sheets human review inbox alignment

Document created:

docs/P6-F.9.62_GOOGLE_SHEETS_HUMAN_REVIEW_INBOX_ALIGNMENT.md

Existing Google Sheet:

Respirarte CRM

Tab:

Solicitudes_Cita

Final agreed columns:

- id_solicitud
- fecha_registro
- telefono
- nombre_paciente
- fecha_solicitada_texto
- franja_solicitada
- modalidad
- estado_solicitud
- observaciones_elvira
- interaction_id_origen
- direccion_domicilio
- servicio_solicitado
- fecha_confirmada
- franja_confirmada
- accion_doctora
- motivo_decision
- revisado_por
- fecha_revision
- sync_status
- last_sync_at
- sync_error

Doctor-owned columns:

- accion_doctora
- fecha_confirmada
- franja_confirmada
- motivo_decision
- revisado_por
- fecha_revision

Backend-owned columns:

- id_solicitud
- fecha_registro
- telefono
- nombre_paciente
- fecha_solicitada_texto
- franja_solicitada
- modalidad
- estado_solicitud
- observaciones_elvira
- interaction_id_origen
- direccion_domicilio
- servicio_solicitado
- sync_status
- last_sync_at
- sync_error

Allowed doctor actions:

- aprobar
- rechazar
- pedir_datos
- proponer_alternativa
- reagendar
- cerrar

Backend action mapping:

- aprobar -> confirm
- rechazar -> cancel
- pedir_datos -> request_missing_data
- proponer_alternativa -> propose_alternative
- reagendar -> reschedule
- cerrar -> close

## P6-F.9.63 — Google Sheets Human Review Inbox Writer

Status:

CLOSED / GREEN / COMMITTED

Commit:

55b8024 Add Google Sheets human review inbox writer

Files created:

- app/adapters/__init__.py
- app/adapters/google_sheets_human_review_writer.py
- tests/test_google_sheets_human_review_writer.py
- docs/P6-F.9.63_GOOGLE_SHEETS_HUMAN_REVIEW_INBOX_WRITER_SPEC.md

Implemented:

- GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
- DOCTOR_OWNED_COLUMNS
- SheetsClient protocol
- map_appointment_request_to_sheet_row(...)
- GoogleSheetsHumanReviewWriter
- upsert_request(...)

Validated behavior:

- AppointmentRequest maps to Solicitudes_Cita row contract.
- Missing optional fields become empty strings.
- Existing row is updated by id_solicitud.
- Missing row is appended.
- Doctor-owned values are preserved on update.
- Writer is skipped when disabled.

Validated targeted tests:

- tests/test_google_sheets_human_review_writer.py
- tests/test_appointment_request_model.py
- tests/test_appointment_request_service.py

Result:

27 passed

Important implementation note:

The writer is isolated.

It is not connected to /webhook or appointment runtime yet.

No real Google Sheets write happens automatically.

## P6-F.9.64 — Google Sheets Config Boundary

Status:

CLOSED / GREEN / COMMITTED

Commit:

d80eb27 Add Google Sheets config boundary

Files changed/created:

- app/config.py
- tests/test_google_sheets_config.py
- docs/P6-F.9.64_GOOGLE_SHEETS_CLIENT_CONFIG_BOUNDARY.md

Config fields added:

- google_sheets_enabled: bool = False
- google_sheets_spreadsheet_id: str | None = None
- google_sheets_solicitudes_cita_tab: str = "Solicitudes_Cita"
- google_service_account_json: str | None = None

Safety decision:

GOOGLE_SHEETS_ENABLED defaults to false.

No Google Sheets write may happen unless explicitly enabled.

## P6-F.9.65 — Google Sheets API Client Adapter

Status:

CLOSED / GREEN / COMMITTED

Commit:

d72d20f Add Google Sheets API client adapter

Files changed/created:

- requirements.txt
- app/adapters/google_sheets_client.py
- tests/test_google_sheets_api_client.py
- docs/P6-F.9.65_GOOGLE_SHEETS_API_CLIENT_ADAPTER.md

Dependencies added:

- google-api-python-client==2.187.0
- google-auth==2.43.0

Implemented:

- GoogleSheetsConfigError
- GOOGLE_SHEETS_SCOPES
- build_google_sheets_service(...)
- GoogleSheetsApiClient
- get_values(...)
- append_row(...)
- update_row(...)

Validated behavior with mocks/fakes only:

- Missing service account JSON is rejected.
- Invalid service account JSON is rejected.
- Valid service account JSON builds a mocked Sheets service.
- get_values calls the expected Sheets API chain.
- append_row uses USER_ENTERED.
- update_row uses USER_ENTERED and row-specific range.

Important safety note:

No real Google Sheets write was performed during P6-F.9.65.

The client exists but is not wired into runtime.

## Google Cloud / Service Account Operational Note

A Google Cloud service account was created:

elvira-sheets-writer@charged-atlas-492207-n9.iam.gserviceaccount.com

Intended purpose:

Write appointment requests from Elvira backend to the Respirarte CRM Google Sheet.

Required external setup before real dry-run:

- Google Sheets API enabled.
- Share the Respirarte CRM Google Sheet with the service account email as Editor.
- Create/download JSON key.
- Store JSON only as environment variable, never in Git or chat.

Expected future env vars:

GOOGLE_SHEETS_ENABLED=false
GOOGLE_SHEETS_SPREADSHEET_ID=1KybtxT0genUOzYLfiPridsAXRtx8jS-rm79829LKjgY
GOOGLE_SHEETS_SOLICITUDES_CITA_TAB=Solicitudes_Cita
GOOGLE_SERVICE_ACCOUNT_JSON=<service-account-json-one-line>

Never commit the service account JSON.

## Current Safety Baseline

WHATSAPP_SENDING_ENABLED=false

GOOGLE_SHEETS_ENABLED=false by default.

No real patient notification sending.

No runtime Google Sheets writes yet.

No doctor action reader.

No Telegram.

No n8n.

No Calendar.

No campaigns.

No doctor confirmation automation.

No therapy session package tracking.

## Current Next Recommended Block

P6-F.9.66 — Google Sheets Writer Factory And Runtime Boundary

Purpose:

Create a safe factory that builds the Google Sheets writer only when configuration is complete and GOOGLE_SHEETS_ENABLED=true.

Recommended scope:

- create factory/helper for GoogleSheetsHumanReviewWriter
- require google_sheets_enabled=true
- require google_service_account_json
- require google_sheets_spreadsheet_id
- use google_sheets_solicitudes_cita_tab
- return disabled/null writer safely when not enabled
- tests with mocks only
- no /webhook wiring yet
- no automatic Sheets write yet

Recommended order after P6-F.9.66:

P6-F.9.67 — Internal/manual controlled Google Sheets write dry-run
P6-F.9.68 — Runtime wiring after AppointmentRequest persistence
P6-F.9.69 — Doctor action reader design
P6-F.9.70 — Patient notification after human review

Do not jump directly into automatic runtime writing before a controlled manual dry-run.


---

## P6-F.9.66 Closure Note — Google Sheets Writer Factory And Runtime Boundary

Status:

GREEN / FACTORY IMPLEMENTED / NOT WIRED TO RUNTIME

Objective:

Create a safe factory that builds `GoogleSheetsHumanReviewWriter` only when Google Sheets human review inbox configuration is explicitly complete.

Implemented:

* `app/adapters/google_sheets_human_review_writer_factory.py`
* `tests/test_google_sheets_human_review_writer_factory.py`

Factory behavior:

`build_google_sheets_human_review_writer(...)` returns `None` unless all required conditions are met:

* `GOOGLE_SHEETS_ENABLED=true`
* `GOOGLE_SERVICE_ACCOUNT_JSON` exists
* `GOOGLE_SHEETS_SPREADSHEET_ID` exists

When all required config exists, the factory:

* builds a Google Sheets API service through the injected `service_builder`
* wraps it in `GoogleSheetsApiClient`
* returns `GoogleSheetsHumanReviewWriter`
* sets `spreadsheet_id` from settings
* sets `tab_name` from `GOOGLE_SHEETS_SOLICITUDES_CITA_TAB`
* keeps writer `enabled=True`

Validated behavior:

* Factory returns `None` when Google Sheets is disabled.
* Factory returns `None` when spreadsheet ID is missing.
* Factory returns `None` when service account JSON is missing.
* Factory returns `GoogleSheetsHumanReviewWriter` when all required config is present.

Validation:

* Google Sheets targeted suite GREEN.
* Full suite GREEN:
  * `301 passed in 11.59s`

Commit:

* `e2c4075 Add Google Sheets human review writer factory`

Important boundary respected:

* No `/webhook` wiring.
* No automatic Google Sheets write.
* No doctor action reader.
* No WhatsApp sending changes.
* No Telegram.
* No n8n.
* No Calendar.
* No doctor confirmation automation.
* PostgreSQL remains the source of truth.
* Google Sheets remains an optional human-visible inbox adapter only.

Conclusion:

P6-F.9.66 is CLOSED.

Next recommended block:

P6-F.9.67 — Manual Controlled Sheets Write Dry-Run

Purpose:

Run a controlled manual Google Sheets write through the adapter/factory path, without connecting it to `/webhook` or automatic AppointmentRequest persistence.

Standing safety baseline:

* Keep `WHATSAPP_SENDING_ENABLED=false`.
* Do not connect Google Sheets to runtime yet.
* Do not write automatically from patient conversations.
* Do not add doctor action reader yet.
* Do not touch Telegram, n8n, Calendar, campaigns, or real patient activation.
