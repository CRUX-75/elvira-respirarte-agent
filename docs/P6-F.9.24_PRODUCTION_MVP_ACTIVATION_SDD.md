# P6-F.9.24 — Production MVP Activation SDD

## Status

DRAFT / READY FOR REVIEW

## Objective

Prepare the controlled production activation roadmap for the Elvira / Respirarte MVP after the exact-hour franja confirmation persistence bug was fixed and verified through:

- local automated tests
- deployed `/webhook` Meta-shaped dry-run
- PostgreSQL `appointment_requests` DB evidence

This sprint does not activate real WhatsApp sending yet.

## Current Baseline

P6-F.9.23 is closed:

- exact-hour franja confirmation persists AppointmentRequest correctly
- `/webhook` Meta-shaped flow passed
- `WHATSAPP_SENDING_ENABLED=false`
- PostgreSQL row verified in `appointment_requests`
- Elvira only says the request was received when `appointment_request != null`

Current validation baseline:

- `pytest -q` → `216 passed`

## Scope

This sprint prepares MVP production activation.

In scope:

- review current production readiness
- define controlled activation checklist
- define first real pilot boundaries
- define rollback rules
- define monitoring rules
- confirm required E2E validation gates before enabling real sending

Out of scope:

- Google Sheets sync
- Telegram notification
- n8n workflows
- Calendar integration
- doctor confirmation automation
- therapy session tracking
- uncontrolled WhatsApp sending
- broad refactors

## Safety Rule

`WHATSAPP_SENDING_ENABLED=false` remains active during this sprint.

No real WhatsApp sending is allowed until a later explicitly approved controlled sending activation sprint.

## Production Readiness Checklist

Before real sending can be considered, the following must be confirmed:

1. `/ready` returns:
   - `status = ready`
   - `whatsapp_sending_enabled = false`
   - `real_whatsapp_sending_allowed = false`

2. `/webhook` accepts Meta-shaped payloads.

3. `processed_messages` deduplication protects repeated `wamid` values.

4. `interactions` stores enough audit information:
   - user message
   - Elvira response
   - intent
   - previous state
   - new state
   - next_action
   - state_reason
   - delivery_status

5. `appointment_requests` remains the source of truth for appointment requests.

6. The appointment request flow has at least one full passing E2E validation:
   - fresh phone
   - fresh `wamid` per turn
   - final `appointment_request != null`
   - correct PostgreSQL row

## Conversational E2E Acceptance Rule

For any production conversation flow:

A response is not trusted unless the expected DB effect exists.

For appointment requests:

~~~txt
appointment_request != null
and appointment_requests contains the correct row in PostgreSQL
~~~

A response such as:

~~~txt
Hemos recibido su solicitud...
~~~

is valid only when:

~~~txt
appointment_request != null
and appointment_requests.estado_solicitud = pendiente_confirmacion
~~~

## Required E2E Evidence

Every accepted production-readiness conversation must capture:

- endpoint used
- test phone
- fresh `wamid` values
- request payloads
- response payloads
- `WHATSAPP_SENDING_ENABLED` value
- `delivery_status`
- `estado_anterior`
- `nuevo_estado`
- `intent`
- `next_action`
- `appointment_request_decision.reason`
- `appointment_request`
- PostgreSQL `appointment_requests` row
- `source_interaction_id` matching the final `wamid`

## Blocking Conditions

Real sending must not be enabled if any of the following happens:

- Elvira says the request was received but `appointment_request = null`
- the PostgreSQL `appointment_requests` row is missing
- the appointment request row has the wrong date
- the appointment request row has the wrong franja
- duplicate `wamid` values create duplicate operational effects
- `/webhook` sends a real WhatsApp message while `WHATSAPP_SENDING_ENABLED=false`
- Elvira confirms final appointment availability automatically
- Elvira promises an exact hour inside a franja
- the patient reaches `ST_CITA_PENDIENTE` without a valid persisted AppointmentRequest

## Pilot Boundaries

The first real production pilot must be limited.

Allowed:

- one dedicated Respirarte WhatsApp Cloud API number
- one or a very small number of controlled test phones
- controlled patient-style test conversations
- manual DB verification after each test flow
- immediate rollback by disabling sending

Not allowed:

- public patient traffic
- mass messaging
- marketing campaigns
- doctor confirmation automation
- Google Sheets operational dependency
- Telegram dependency
- n8n dependency
- Calendar dependency

## Rollback Rules

If a critical issue appears:

1. keep or restore `WHATSAPP_SENDING_ENABLED=false`
2. stop real testing immediately
3. preserve request/response payloads
4. preserve DB evidence
5. document the failing flow
6. fix with automated tests first
7. rerun `pytest -q`
8. rerun `/test/message-stateful`
9. rerun `/webhook` Meta-shaped dry-run
10. verify PostgreSQL effect again

## Acceptance Criteria

This sprint is accepted only if it produces a clear controlled production activation plan.

The plan must define:

- what can be activated
- what must remain disabled
- which test phone(s) are allowed
- how to verify successful real message sending later
- how to stop sending immediately
- how to validate DB effects after real conversations
- how to monitor failed delivery or failed persistence

## Proposed Next Sprint After This

P6-F.9.25 — Controlled WhatsApp Sending Activation Plan

Goal:

Prepare the exact technical and operational steps to enable real WhatsApp sending for a very small controlled pilot.

This future sprint may decide when and how to change:

~~~txt
WHATSAPP_SENDING_ENABLED=true
~~~

But P6-F.9.24 must not enable it.

## Definition of Done

P6-F.9.24 is closed only when:

- this SDD is committed
- the production MVP activation roadmap is explicit
- `WHATSAPP_SENDING_ENABLED=false` remains unchanged
- E2E acceptance requires DB evidence
- rollback rules are documented
- the next sprint is clearly defined

---

## Post-Activation Addendum — Phase 2 Conversational Voice

This addendum records the current post-MVP direction. It does not alter the historical P6-F.9.24 activation decision or its original acceptance criteria.

### Production State

Elvira remains online in production and continues serving text conversations.

Voice development is isolated in:

```txt
feature/p6-f-9-92-voice-interaction
```
No voice implementation has been merged into or activated on production.

Closed Voice Milestones
P6-F.9.92 — Voice Interaction Architecture
P6-F.9.93 — Inbound Voice Notes

P6-F.9.93 implemented:

parsing of valid WhatsApp audio.voice=true payloads;
deduplication before media download or STT;
authenticated WhatsApp media download;
MIME, size, and SHA-256 validation;
secure temporary files with guaranteed cleanup;
OGG/Opus normalization through ffmpeg;
Spanish transcription through OpenAI;
reuse of the existing deterministic conversational core;
deterministic text fallback when media processing or STT fails;
preservation of the existing text webhook behavior.

Meta remains strictly a WhatsApp transport boundary. It does not provide transcription, synthesis, conversational logic, state, persistence, or safety decisions.

Safety State

The branch defaults remain:

VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true

WHATSAPP_SENDING_ENABLED remains the master external-delivery switch.

Voice processing must not be activated in production during P6-F.9.94.

Verification Evidence

The complete repository suite passed after inbound voice integration:

347 passed in 528.22s

Final inbound webhook integration commit:

f3120fd — Integrate inbound voice notes into webhook
Next Voice Milestone
P6-F.9.94 — Outbound Voice Replies

This phase is limited to:

existing deterministic response
→ TTS
→ validated audio
→ WhatsApp voice-note transport

TTS must not generate or alter conversational content. If synthesis, validation, upload, or voice delivery fails, Elvira must send the already-produced deterministic response as text without rerunning the core.

Production Activation Gate

Voice production activation remains blocked until:

P6-F.9.95 — Safety, Observability and Production Activation

That phase must validate rollback flags, latency, cleanup, correlation, duplicate-work protection, real-device voice-note rendering, AI-voice disclosure, and controlled activation.
Post-Activation Addendum — P6-F.9.94 Outbound Voice Closure

P6-F.9.94 is complete on the isolated voice branch.

The implemented outbound path is:

existing deterministic response
→ OpenAI TTS
→ OGG/Opus validation
→ WhatsApp media upload
→ WhatsApp voice-note delivery

The implementation does not permit TTS to decide or rewrite conversational content. It receives the already-produced deterministic response plus the approved AI-voice disclosure.

The marin voice was validated through a real local OpenAI TTS request, listened to, and approved. This validation did not call Meta and did not affect production.

If synthesis, validation, upload, or voice delivery fails, Elvira sends the existing deterministic response as text without rerunning the core. If both voice and text delivery fail, patient state and processed-message behavior remain unchanged.

Code integration commit:

df203d8

Repository verification:

361 passed in 527.69s (0:08:47)

Production remains text-only. Voice flags remain disabled by default.

The next authorized phase is P6-F.9.95. No production voice activation is authorized without its safety, observability, rollback, duplicate-work, allowlist, and controlled-device gates.

---

## Post-Activation Addendum — P6-F.9.95 Controlled Voice Activation

Elvira remained available for production text conversations throughout deployment and validation.

P6-F.9.95 introduced an additive voice layer without changing the deterministic conversational core, appointment logic, or existing patient-state semantics.

Verified controls:

- PostgreSQL backup before deployment;
- Git rollback tag before deployment;
- voice flags disabled during initial deployment;
- additive processing-claim migration;
- health, readiness, and text regression validation;
- controlled single-number allowlist;
- successful inbound and outbound voice validation;
- privacy stop condition detected during controlled activation;
- immediate configuration rollback completed successfully;
- privacy correction deployed and revalidated;
- transcript and response content removed from production voice logs.

Current activation is controlled and limited to one allowlisted number. Global production voice remains unauthorized.

The operational rollback remains:

```env
VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true
VOICE_ALLOWED_PHONE_NUMBERS=
```

Ordinary voice rollback does not require database restoration.

Naturalness and expressive intonation remain quality improvements outside the functional activation gate.
