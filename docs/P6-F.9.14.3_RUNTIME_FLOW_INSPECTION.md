# P6-F.9.14.3 — Runtime Flow Inspection

## Status

DRAFT

## Purpose

This document records the inspection of the current Elvira runtime flow before connecting `AppointmentRequestService`.

This block is inspection-only.

No runtime implementation is done here.

---

## Files Inspected

Main runtime file:

- `app/main.py`

Interaction persistence:

- `app/repositories/interactions.py`

Database engine wiring:

- `app/db/session.py`

LangGraph runtime:

- `app/graph/graph.py`
- `app/graph/nodes.py`
- `app/graph/transitions.py`

---

## Runtime Entry Points

The current application exposes three relevant message-processing entry points.

### Real WhatsApp webhook

`POST /webhook`

Function:

`receive_webhook(payload: WhatsAppPayload)`

Purpose:

Processes real WhatsApp Cloud API webhook payloads.

### Stateless test endpoint

`POST /test/message`

Function:

`test_message(message: IncomingMessage)`

Purpose:

Processes one message directly through the graph and returns the result.

This endpoint does not persist patient state.

### Stateful dry-run endpoint

`POST /test/message-stateful`

Function:

`test_message_stateful(message: IncomingMessage)`

Purpose:

Production dry-run endpoint for multi-turn validation.

It:

- reads or creates patient from PostgreSQL
- loads current patient state
- processes the message through LangGraph
- stores the interaction
- updates patient state
- never sends WhatsApp messages

This endpoint is the best candidate for safe validation before connecting appointment request persistence to the real webhook.

---

## Real Webhook Flow

The real WhatsApp webhook currently follows this order:

1. Extract message from WhatsApp payload.
2. Validate required fields.
3. Deduplicate by `whatsapp_message_id`.
4. Ignore already processed messages.
5. Get or create patient by phone.
6. Build `IncomingMessage`.
7. Run `traced_process_message(process_message, message)`.
8. Send WhatsApp reply only if `WHATSAPP_SENDING_ENABLED=true`.
9. Save interaction.
10. Update patient state.
11. Update patient last message.
12. Mark message as processed.
13. Write legacy log.
14. Return response payload.

Important safety detail:

If WhatsApp sending fails while real sending is enabled, the interaction is saved with failed delivery information, but patient state is not advanced.

This behavior must not be broken by appointment request integration.

---

## Stateful Test Flow

The `/test/message-stateful` flow currently follows this order:

1. Receive `IncomingMessage`.
2. Get or create patient by phone.
3. Read current patient state.
4. Build stateful message.
5. Run `traced_process_message(process_message, stateful_message)`.
6. Generate synthetic `whatsapp_message_id`.
7. Set `delivery_status = sending_skipped`.
8. Save interaction.
9. Update patient state.
10. Update patient last message.
11. Return graph result plus test metadata.

This endpoint never sends real WhatsApp messages.

It is a strong candidate for first safe AppointmentRequest runtime validation.

---

## LangGraph Flow

The current graph is built in `app/graph/graph.py`.

Node order:

1. `sanitize_input`
2. `classify_intent`
3. `transition_state`
4. `resolve_date_context`
5. `load_kb_context`
6. `generate_response`

This confirms that `AppointmentRequestService` must not run before:

- intent classification
- state transition
- deterministic date context resolution

The earliest safe point is after `traced_process_message(...)` returns its `ElviraState`.

---

## Intent and State Transition Findings

The deterministic state machine currently handles appointment-related intents as follows:

### `cita`

Transition:

- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`

Meaning:

The patient wants to book an appointment, but no operational date/time is available yet.

Appointment request should usually not be created here.

### `fecha_cita`

Transition:

- `nuevo_estado = ST_CITA_FRANJA`
- `next_action = ask_preferred_time`

Meaning:

The patient gave date or date-like information.

Appointment request should usually not be created yet unless enough time/preference data is also available.

### `hora_cita`

Transition:

- `nuevo_estado = ST_CITA_PENDIENTE`
- `next_action = confirm_appointment_request`

Meaning:

The patient gave a time preference.

This is the strongest first candidate for AppointmentRequest creation or reuse.

---

## Date Context Findings

`node_resolve_date_context()` enriches the runtime state with deterministic appointment date fields.

Relevant fields include:

- `fecha_actual_colombia`
- `fecha_solicitada`
- `fecha_solicitada_texto`
- `dia_semana_solicitado`
- `es_dia_disponible`
- `slots_candidatos`
- `is_weekend`
- `is_colombia_holiday`
- `colombia_holiday_name`
- `date_resolution_source`

This node does not decide appointment lifecycle.

It only enriches the state for safe response wording and deterministic context.

Appointment request persistence should use these fields only after state transition.

---

## KB Context Findings

`node_load_kb_context()` runs after date resolution.

The KB remains informational only.

It does not decide:

- intent
- patient state
- next_action
- appointment request persistence

This boundary must remain intact.

---

## Interaction Persistence Finding

`save_interaction()` currently inserts into the `interactions` table but returns `None`.

Current signature:

`save_interaction(...) -> None`

Therefore, the current runtime cannot directly obtain a database interaction ID after insertion.

Important implication:

The preferred design from earlier SPEC — persist interaction first and pass the created interaction ID as `source_interaction_id` — is not currently available without changing the interaction repository.

---

## Source Interaction ID Decision

Because `save_interaction()` does not currently return an interaction ID, there are two options.

### Option A — Use `whatsapp_message_id` as `source_interaction_id`

Pros:

- No interaction schema/repository change.
- Works in real webhook.
- Works in `/test/message-stateful` because it generates a synthetic message ID.
- Deterministic and traceable.
- Safe for first runtime integration.

Cons:

- It references the message, not the internal interaction row ID.

### Option B — Modify `save_interaction()` to return an interaction ID

Pros:

- Stronger relational traceability.

Cons:

- Requires inspecting the interactions schema.
- May require SQL RETURNING support.
- Requires updating tests.
- Adds extra scope before first runtime integration.

Decision for first integration:

Use Option A.

`source_interaction_id` should initially receive `whatsapp_message_id`.

A later improvement may add real interaction row IDs if needed.

---

## Recommended First Integration Point

The first safe integration point should be after:

`result = traced_process_message(process_message, message)`

or, in test flow:

`result = traced_process_message(process_message, stateful_message)`

At that point, the runtime has:

- telefono
- nombre
- patient_id
- estado_actual
- result.intent
- result.nuevo_estado
- result.next_action
- result.fecha_solicitada
- result.slots_candidatos
- result.es_dia_disponible
- result.is_weekend
- result.is_colombia_holiday
- result.respuesta

This is the first point where deterministic appointment persistence can be evaluated safely.

---

## Recommended First Validation Surface

The first integration should be validated through:

`POST /test/message-stateful`

Reason:

- It already persists patient state.
- It already creates a synthetic `whatsapp_message_id`.
- It never sends real WhatsApp messages.
- It can be tested through Swagger.
- It mirrors the real runtime closely enough for safe dry-runs.

No new `/test/appointment-request` endpoint is required yet.

---

## Creation Trigger Recommendation

For the first runtime integration, AppointmentRequest creation/reuse should be limited to:

- `intent == "hora_cita"`
- `nuevo_estado == "ST_CITA_PENDIENTE"`
- `next_action == "confirm_appointment_request"`
- `fecha_solicitada` is present
- at least one time preference exists through either:
  - `slots_candidatos`
  - `mensaje_original` as `hora_solicitada_texto`

Do not create requests for:

- `intent == "cita"`
- `intent == "fecha_cita"` as default
- service questions
- schedule questions
- payment questions
- urgency messages
- opt-out messages
- blocked weekend/holiday cases

---

## Weekend / Holiday Safety

If deterministic date resolution marks a requested date as unavailable, appointment request creation should be skipped.

Skip when:

- `is_weekend == true`
- `is_colombia_holiday == true`
- `es_dia_disponible == false`

Reason:

The doctor should not receive operational appointment requests for dates the system already knows are invalid.

The conversation may still continue by offering alternatives.

---

## First Runtime Integration Strategy

Recommended next architecture:

1. Create a pure decision function that receives the final `ElviraState`.
2. The function decides whether appointment request persistence should be skipped or attempted.
3. The function returns a small decision object.
4. Runtime wiring later uses the decision object to call `AppointmentRequestService`.

This keeps the integration testable and avoids putting business rules directly inside `app/main.py`.

---

## Proposed New Module

Candidate file:

`app/services/appointment_request_runtime.py`

Purpose:

Contain runtime-specific decision logic for appointment request persistence.

It should not directly send WhatsApp messages.

It should not touch Google Sheets.

It should not touch Telegram.

It should not use n8n.

Possible responsibilities:

- decide whether to skip appointment request persistence
- explain skip reason
- build service input payload
- keep runtime-specific mapping out of `app/main.py`

---

## Proposed Next Tests

Candidate test file:

`tests/test_appointment_request_runtime_decision.py`

Test cases:

1. Skips general messages.
2. Skips initial appointment intent `cita`.
3. Skips `fecha_cita` when time preference is missing.
4. Skips weekend/holiday/unavailable dates.
5. Allows `hora_cita` with `ST_CITA_PENDIENTE`.
6. Preserves `whatsapp_message_id` as `source_interaction_id`.
7. Uses `pendiente_confirmacion` for a complete patient appointment request.
8. Does not call repository/service directly from the decision function.

---

## Open Questions For Next Block

The next block must decide:

1. Exact decision object shape.
2. Exact function name.
3. Whether the function receives `ElviraState` only or also runtime metadata.
4. How to derive `franja_solicitada` from `slots_candidatos`.
5. Whether `hora_solicitada_texto` should store the raw patient message.
6. Whether missing service/address should keep status as `pendiente_datos` or still allow `pendiente_confirmacion`.

---

## Next Block

P6-F.9.14.4 — Appointment Persistence Decision Function SPEC

Goal:

Specify the pure decision function before writing tests or implementation.

