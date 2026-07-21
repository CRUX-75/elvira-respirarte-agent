# P6-F.9.97 — Conversational Continuity and KB-Grounded Services SDD

## Status

- Date: 2026-07-21
- Status: In progress — specification and design
- Branch: `feature/p6-f-9-97-conversational-continuity-kb-services`
- Production service: Elvira remains online
- Database changes: None authorized
- Google Sheets changes: None authorized

## Objective

Improve Elvira's conversational continuity and guarantee that every
patient-facing statement about Respirarte services is grounded in approved
knowledge-base information.

This sprint responds to production evidence where Elvira:

1. repeated an initial greeting during an active conversation;
2. failed to interpret `3` while waiting for an appointment slot;
3. answered about oximetría without retrieving `kb_services`;
4. claimed that a procedure could be coordinated without KB support;
5. restarted an appointment flow after a request was already pending;
6. presented candidate appointment slots as real availability;
7. appeared to process an identical services question twice.

## Scope

### Included

- Greeting continuity outside `ST_INIT`
- Contextual appointment-slot selection
- Numeric shorthand in `ST_CITA_FRANJA`
- Priority of the current message over stale conversational context
- KB-grounded service answers
- Matching across approved `KB_Servicios` fields
- Safe fallback for unknown procedures
- Pending-appointment continuity
- Candidate-slot wording protection
- Duplicate-message regression verification
- Automated tests
- `AI_CONTEXT.md` maintenance
- Sprint closure evidence

### Excluded

- New clinical or medical content
- Inventing descriptions for procedures
- PostgreSQL schema or data changes
- Google Sheets changes
- Multitenancy
- P7 channel resilience
- Patient follow-up
- Campaigns
- Doctor-notification implementation
- Realtime voice
- Voice transport changes
- Appointment-capacity or schedule changes

## Production Evidence

### Repeated greeting

While the patient was already in `ST_CITA_FRANJA`, the message `3` was
classified as `general`.

Elvira answered with a fresh greeting instead of continuing the appointment
conversation.

Expected behavior:

- interpret the answer in the active slot-selection context;
- never greet again outside `ST_INIT`;
- preserve the appointment flow.

### Unsupported oximetría answer

Patient message:

    Toma de oximetría dinámica.

Observed result:

    intent=general
    kb_sources=["kb_schedules","kb_rules"]
    next_action=answer_general

Elvira stated that the procedure could be coordinated, although no active
`KB_Servicios` result supported that claim.

Expected behavior:

- detect a service or procedure question;
- query `KB_Servicios`;
- answer only with facts present in the matched active row;
- use a safe escalation response when the information is insufficient.

### Pending appointment restarted

A patient in `ST_CITA_PENDIENTE` mentioned an appointment again.

Elvira changed to `ST_CITA_FECHA` and started a new appointment flow.

Expected behavior:

- preserve the existing pending request;
- determine whether the patient wants to modify it or create another request;
- never overwrite or restart from ambiguous language.

### Candidate slots presented as availability

Elvira used wording equivalent to:

    Para ese día tengo disponibles...

Candidate slots are preferences that may be reviewed. They are not confirmed
availability.

Expected wording:

    Las franjas que podemos revisar son...
    Puedo registrar su preferencia entre...
    Podemos validar disponibilidad para...

### Apparent duplicate message

The supplied production log contains the same services question twice.

The repository already has idempotency based on `whatsapp_message_id`.
This sprint will verify that existing behavior rather than introduce another
deduplication architecture without evidence.

Possible explanations to investigate:

- two different inbound message IDs;
- a retry with a missing or changed ID;
- duplicate application logging;
- two patient sends;
- an actual idempotency regression.

## Functional Requirements

### FR-1 — Greeting continuity

Elvira may issue an initial greeting only when the state entering the turn is
`ST_INIT`.

Outside `ST_INIT`, Elvira must not introduce:

- Hola
- Buenos días
- Buenas tardes
- Buenas noches
- Qué gusto saludarle
- a repeated presentation of Elvira or Respirarte

The response must continue directly from the active conversation.

### FR-2 — Contextual slot selection

When the active state is `ST_CITA_FRANJA`, slot interpretation must occur before
generic fallback.

First-slot expressions include:

- `3`
- `a las 3`
- `a las tres`
- `primera`
- `la primera`
- `primera franja`
- `de 3 a 5`
- `entre 3 y 5`
- `15 a 17`
- `15:00 a 17:00`

Second-slot expressions include:

- `5`
- `a las 5`
- `a las cinco`
- `segunda`
- `la segunda`
- `segunda franja`
- `de 5 a 7`
- `entre 5 y 7`
- `17 a 19`
- `17:00 a 19:00`

The mapping must use the actual `slots_candidatos`.

The values `3` and `5` must not become global appointment intents outside
`ST_CITA_FRANJA`.

Unsupported numeric answers must trigger clarification rather than
`answer_general`.

### FR-3 — Exact-hour safety

A loose exact hour is not a confirmed appointment time.

A message such as `a las 3` may map to the candidate franja containing 15:00,
but Elvira must preserve the existing rule that appointments are handled by
visible franjas and remain pending human confirmation.

Elvira must never guarantee an exact hour.

### FR-4 — Current-message priority

The current message takes priority over the previous state for independent
informational or safety intents.

Examples:

- a service question in `ST_CITA_PENDIENTE` must query services;
- a service question in `ST_CITA_FRANJA` must query services;
- an opt-out message must retain absolute priority;
- a service question must not retrieve only schedules because the previous state
  was appointment-related.

The previous appointment context must remain available after answering an
independent informational question.

### FR-5 — KB-grounded service answers

Patient-facing service claims must derive from active `KB_Servicios` rows.

Searchable fields may include:

- `service_id`
- `service_name`
- `category`
- `objective`
- `techniques`
- `patient_scope`
- `modality`
- `public_answer_short`
- `public_answer_long`
- `aliases`
- `is_active`

Matching must:

- normalize case;
- normalize accents;
- ignore harmless punctuation;
- search individual terms inside `techniques`;
- exclude inactive services;
- identify the matched service;
- identify the matched term or field;
- avoid adding medical details absent from the row.

### FR-6 — Grounding metadata

A successful service match must expose testable metadata equivalent to:

    intent=servicios
    next_action=answer_services
    kb_used=true
    kb_sources=["kb_services"]
    matched_service_id=<service id>
    matched_service_term=<matched term>
    service_grounding_status=matched

Exact field names may follow current model conventions.

A response must not claim grounding when no active service matched.

### FR-7 — Unknown-service fallback

When a service or procedure cannot be matched confidently, Elvira must not:

- claim that Respirarte offers it;
- claim that it can be coordinated;
- claim that it can be scheduled;
- invent its clinical purpose;
- invent preparation requirements;
- redirect automatically into appointment scheduling;
- infer equivalence between medical terms.

Required internal behavior:

    intent=servicios
    next_action=escalate_unknown_service
    escalation_required=true
    kb_used=false
    service_grounding_status=not_found

Required patient-facing meaning:

    No tengo información confirmada suficiente sobre ese procedimiento.
    Voy a remitir su consulta a la Dra. D’Aleman para que pueda orientarle
    correctamente.

Until validated by the doctor, `oximetría dinámica` must not automatically be
treated as an approved alias for plain `oximetría`.

### FR-8 — Partial procedure matches

If a term exists inside a service row but the KB does not contain a specific
explanation, Elvira may state only the confirmed relationship.

Example:

    La oximetría aparece entre los procedimientos de terapia respiratoria de
    Respirarte. No tengo registrada una explicación específica de la oximetría
    dinámica. Voy a remitir la consulta a la Dra. D’Aleman.

Elvira may not infer clinical details or schedulability.

### FR-9 — Pending appointment continuity

When the state is `ST_CITA_PENDIENTE` and the patient mentions another
appointment, Elvira must distinguish between:

1. an informational question;
2. a request to modify the existing request;
3. an explicit request for a second appointment;
4. an ambiguous appointment mention.

For an ambiguous mention, Elvira must ask:

    Ya tiene una solicitud de cita pendiente de confirmación.
    ¿Desea modificar esa solicitud o registrar una nueva?

No appointment data may be overwritten until the patient's intention is clear.

### FR-10 — Candidate-slot wording

Candidate slots must never be represented as confirmed availability.

Forbidden unless an authorized human-review result explicitly confirms it:

- tengo disponible
- tenemos disponible
- hay disponibilidad
- franjas disponibles
- puedo confirmarle
- queda confirmada

Permitted:

- las franjas que podemos revisar son
- puedo registrar su preferencia entre
- podemos validar disponibilidad para

### FR-11 — Idempotency preservation

The existing webhook contract remains:

1. extract `whatsapp_message_id`;
2. check processed-message storage;
3. ignore known duplicates before LangGraph or LLM execution;
4. preserve the unique processed-message constraint.

Required regression coverage:

- duplicate ID does not invoke the core;
- duplicate ID does not advance state;
- duplicate ID does not invoke STT or TTS;
- duplicate ID does not send another response;
- duplicate ID returns `reason=duplicate_message`;
- missing message ID follows the existing explicit failure contract.

## Safety Invariants

1. No unsupported medical claim may be generated.
2. No unknown procedure may be presented as offered.
3. No medical aliases may be inferred without KB approval.
4. Candidate slots are not confirmed availability.
5. Exact appointment times are never guaranteed.
6. Ambiguous language cannot overwrite a pending appointment.
7. Opt-out retains priority over conversational state.
8. Inactive services remain excluded.
9. The retired tracheostomy-service behavior remains unchanged.
10. Voice and text continue using the same deterministic core.

## Proposed Design

### State-aware intent guard

Routing priority:

1. opt-out and safety intents;
2. state-aware slot selection;
3. explicit service or procedure detection;
4. date and appointment intents;
5. general fallback.

This must not rely exclusively on prompt behavior.

### Deterministic service matcher

A single service-matching boundary should perform:

- normalization;
- active-row filtering;
- approved-field search;
- technique-level matching;
- match metadata creation;
- safe no-match creation.

The response layer consumes the matcher result and must not independently invent
service facts.

### Deterministic response policies

Centralized responses are required for:

- unknown service;
- partial procedure match;
- pending-appointment clarification;
- unsupported slot selection;
- non-initial general fallback.

### State preservation

An independent information question may be answered without destroying a pending
appointment state.

Every state transition must be explicit and covered by tests.

## Test Plan

### Greeting continuity

- `ST_INIT` may greet.
- `ST_GENERAL` does not greet again.
- `ST_CITA_FRANJA` does not greet again.
- `ST_CITA_PENDIENTE` does not greet again.
- Voice follow-ups do not repeat the initial greeting or AI disclosure.

### Slot selection

- `3` selects the first candidate franja.
- `5` selects the second candidate franja.
- `primera` and `segunda` remain supported.
- `a las 3` preserves exact-hour clarification.
- `a las 5` preserves exact-hour clarification.
- `4` asks for clarification.
- Numeric input outside `ST_CITA_FRANJA` remains non-global.
- Mapping uses actual candidate slots.

### Service grounding

- exact service-name match;
- accent-insensitive match;
- match inside `techniques`;
- inactive service excluded;
- unknown service triggers safe escalation;
- unknown service does not retrieve only schedules;
- unknown service does not claim schedulability;
- partial match does not invent clinical details;
- appointment state does not block service lookup;
- successful output includes grounding metadata.

### Pending appointment

- service question preserves `ST_CITA_PENDIENTE`;
- ambiguous appointment mention asks modify-or-new;
- explicit modification follows the modification path;
- explicit new appointment follows the authorized path;
- ambiguity does not overwrite the existing request.

### Candidate wording

- no `tengo disponibles`;
- no confirmation from candidate slots;
- use preference or validation wording.

### Idempotency

- retain existing webhook-persistence tests;
- retain voice-processing claim tests;
- add a regression only if the production duplicate cause can be reproduced.

## Implementation Sequence

1. Commit this specification.
2. Inspect exact routing, state, response and KB boundaries.
3. Add failing tests reproducing production evidence.
4. Implement greeting continuity.
5. Implement contextual numeric slot selection.
6. Implement deterministic service matching.
7. Implement the grounding contract.
8. Implement safe unknown-service fallback.
9. Implement pending-request clarification.
10. enforce candidate-slot wording.
11. run directed tests;
12. run the complete suite;
13. update SDD evidence;
14. update `AI_CONTEXT.md`;
15. commit and merge;
16. push and redeploy;
17. validate controlled text and voice conversations.

## Directed Validation

Run:

    pytest -q \
      tests/test_intent.py \
      tests/test_state_machine.py \
      tests/test_kb_service.py \
      tests/test_kb_runtime_integration.py \
      tests/test_kb_services_repository.py \
      tests/test_appointment_request_runtime_decision.py \
      tests/test_stateful_appointment_context_carryover.py \
      tests/test_webhook_persistence.py \
      tests/test_voice_webhook.py

Before merge:

    pytest -q
    python -m py_compile app/main.py app/services/intent.py \
      app/services/response.py app/services/kb.py \
      app/services/appointment_request_runtime.py
    git diff --check

## Deployment Validation

After deployment:

1. Verify `/health` returns 200.
2. Verify `/ready` returns 200.
3. Send a normal initial greeting.
4. Continue the conversation and verify no repeated greeting.
5. Request an appointment and answer `3`.
6. Verify that the first franja is selected safely.
7. Ask about a service while an appointment is pending.
8. Verify that `kb_services` supports the answer.
9. Ask about `oximetría dinámica`.
10. Verify that Elvira does not invent an explanation or schedulability.
11. Replay one webhook ID and verify that it is ignored.
12. Repeat relevant cases by voice.
13. Verify persistence remains correct.

## Rollback

If patient-facing behavior becomes unsafe:

1. preserve correlation evidence;
2. redeploy the previous stable `main` commit;
3. do not modify PostgreSQL or Google Sheets;
4. disable voice independently only when needed;
5. investigate the exact failing contract before another patch.

## Closure Criteria

P6-F.9.97 closes only when:

- all directed tests pass;
- the complete suite passes;
- greetings occur only in `ST_INIT`;
- `3` and `5` work contextually in `ST_CITA_FRANJA`;
- service answers use active `KB_Servicios` data;
- unknown procedures trigger the safe fallback;
- pending appointments are not silently restarted;
- candidate slots are not presented as confirmed availability;
- existing idempotency coverage remains green;
- controlled text and voice validation pass;
- SDD closure evidence and `AI_CONTEXT.md` are updated.
