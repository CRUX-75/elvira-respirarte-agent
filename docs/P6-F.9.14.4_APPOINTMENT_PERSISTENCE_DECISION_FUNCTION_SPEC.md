# P6-F.9.14.4 — Appointment Persistence Decision Function SPEC

## Status

DRAFT

## Purpose

This document specifies the pure decision function that will decide whether the runtime should attempt AppointmentRequest persistence.

This block is specification-only.

No implementation is done here.

---

## Background

Runtime inspection confirmed that the safest first integration point is after:

`result = traced_process_message(process_message, message)`

At that point, the runtime already has deterministic output from:

- intent classification
- state transition
- date context resolution
- KB context loading
- response generation

The decision to create or reuse an appointment request must not live directly inside `app/main.py`.

A pure decision function should be created first.

---

## Proposed Module

Candidate module:

`app/services/appointment_request_runtime.py`

This module will contain runtime-specific appointment request persistence decision logic.

It must not:

- send WhatsApp messages
- write to Google Sheets
- send Telegram notifications
- call n8n
- mutate patient state
- call the LLM
- decide patient state transitions
- directly persist database rows in the decision function

---

## Function Responsibility

The decision function decides whether appointment request persistence should be attempted.

It answers:

Should the runtime call `AppointmentRequestService` for this processed message?

It should also explain why the operation is allowed or skipped.

---

## Proposed Function Name

`decide_appointment_request_persistence`

---

## Proposed Input

The function should receive:

- final `ElviraState`
- `telefono`
- `nombre`
- `source_interaction_id`

Where:

- `ElviraState` contains deterministic graph result.
- `telefono` comes from runtime/patient input.
- `nombre` comes from runtime/patient input when available.
- `source_interaction_id` should initially be the `whatsapp_message_id`.

Reason:

`save_interaction()` currently returns `None`, so using the internal interaction row ID is not available without expanding scope.

---

## Proposed Output

The function should return a small decision object.

Candidate object:

`AppointmentPersistenceDecision`

Fields:

- `should_persist: bool`
- `reason: str`
- `telefono: str | None`
- `nombre_paciente: str | None`
- `intent_origen: str | None`
- `canal_origen: str`
- `estado_solicitud: str | None`
- `fecha_solicitada: str | None`
- `franja_solicitada: str | None`
- `hora_solicitada_texto: str | None`
- `servicio_solicitado: str | None`
- `direccion_domicilio: str | None`
- `source_interaction_id: str | None`

This object should be easy to test without database access.

---

## Default Channel

For this first runtime integration:

`canal_origen = "whatsapp"`

This applies to both:

- real webhook messages
- `/test/message-stateful` dry-run messages

The dry-run endpoint simulates WhatsApp-originated patient messages.

---

## Main Allow Rule

The first allowed persistence case should be narrow.

Allow persistence only when:

- `state.intent == "hora_cita"`
- `state.nuevo_estado == "ST_CITA_PENDIENTE"`
- `state.next_action == "confirm_appointment_request"`
- `state.fecha_solicitada` is present
- requested date is not blocked
- patient supplied some time preference

This prevents early appointment request noise.

---

## Required Patient Data

Persistence should be skipped if:

- `telefono` is missing or blank

`nombre` is optional.

---

## Required Appointment Data

Persistence should be skipped if:

- `fecha_solicitada` is missing
- no time preference can be derived

A time preference may come from:

- `state.slots_candidatos`
- the raw patient message as `hora_solicitada_texto`

For first implementation, if `slots_candidatos` exists, use the first candidate as `franja_solicitada`.

If no candidate slot exists but the patient message exists, store the raw message as `hora_solicitada_texto`.

---

## Blocked Date Rules

Persistence should be skipped when any of these are true:

- `state.is_weekend is True`
- `state.is_colombia_holiday is True`
- `state.es_dia_disponible is False`

Reason:

The doctor should not receive operational appointment requests for dates the deterministic system already knows are invalid.

---

## Skip Rules

The decision function must skip persistence for:

- `intent == "general"`
- `intent == "servicios"`
- `intent == "horarios"`
- `intent == "pago"`
- `intent == "reglas"`
- `intent == "urgencia"`
- `intent == "optout"`
- `intent == "cita"` in the first implementation
- `intent == "fecha_cita"` in the first implementation

Important:

`cita` and `fecha_cita` may continue the conversation, but they should not create an operational request yet.

---

## Status Mapping

For the first integration, when persistence is allowed:

`estado_solicitud = "pendiente_confirmacion"`

Meaning:

The patient has provided enough appointment preference data for human review.

The appointment is not confirmed.

The doctor still decides.

---

## No Automatic Confirmation

The decision function must never return:

`estado_solicitud = "confirmada"`

Confirmation belongs to a future human doctor decision flow.

---

## Source Interaction ID Strategy

For the first integration:

`source_interaction_id = whatsapp_message_id`

In `/test/message-stateful`, this is the generated synthetic test message ID.

In real webhook flow, this is the real WhatsApp message ID.

This gives traceability without modifying `save_interaction()`.

---

## Data Extraction Rules

### `fecha_solicitada`

Use:

`state.fecha_solicitada`

Expected format:

ISO date string.

### `franja_solicitada`

Use first available item from:

`state.slots_candidatos`

Only if present.

### `hora_solicitada_texto`

Use:

`state.mensaje_original`

When a time preference exists or when no structured franja can be extracted.

### `servicio_solicitado`

Do not infer from LLM response.

Use `None` for first implementation unless a deterministic field already exists.

### `direccion_domicilio`

Do not infer from LLM response.

Use `None` for first implementation unless a deterministic field already exists.

---

## Reason Codes

The decision object should provide clear reason strings.

Candidate reasons:

- `allowed_hora_cita_ready_for_human_review`
- `skipped_missing_telefono`
- `skipped_non_appointment_intent`
- `skipped_initial_cita_intent`
- `skipped_fecha_cita_waiting_for_time`
- `skipped_missing_fecha_solicitada`
- `skipped_missing_time_preference`
- `skipped_weekend`
- `skipped_colombia_holiday`
- `skipped_unavailable_date`
- `skipped_wrong_state_or_action`

These reasons should be tested.

---

## Test Strategy

Create tests before implementation.

Candidate test file:

`tests/test_appointment_request_runtime_decision.py`

Required tests:

1. Skips general message.
2. Skips servicios.
3. Skips horarios.
4. Skips pago.
5. Skips urgencia.
6. Skips optout.
7. Skips initial `cita`.
8. Skips `fecha_cita` because it is still waiting for time.
9. Skips `hora_cita` without `fecha_solicitada`.
10. Skips weekend.
11. Skips Colombia holiday.
12. Skips unavailable date.
13. Allows `hora_cita` with `ST_CITA_PENDIENTE`, `confirm_appointment_request`, valid date, and candidate slots.
14. Uses first candidate slot as `franja_solicitada`.
15. Preserves `source_interaction_id`.
16. Sets `estado_solicitud = pendiente_confirmacion`.
17. Does not require `nombre`.
18. Skips blank `telefono`.

---

## Expected Implementation Style

The implementation should be:

- pure
- deterministic
- unit-testable
- free of database access
- free of network access
- free of LLM calls
- typed
- DRY

No code in this function should depend on FastAPI.

---

## Future Runtime Wiring

After the decision function is implemented and tested, a later block may wire it into:

- `/test/message-stateful` first
- real `/webhook` later

Runtime wiring should call `AppointmentRequestService` only when:

`decision.should_persist is True`

---

## Out of Scope

This SPEC does not implement:

- decision function code
- decision tests
- AppointmentRequestService runtime call
- repository wiring
- database writes from runtime
- Google Sheets sync
- Telegram notification
- n8n workflow
- WhatsApp sending changes
- doctor confirmation
- calendar integration

---

## Next Block

P6-F.9.14.5 — Decision Function Tests

Goal:

Write failing tests for the pure decision function before implementation.

