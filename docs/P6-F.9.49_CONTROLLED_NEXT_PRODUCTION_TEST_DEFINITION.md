# P6-F.9.49 — Controlled Next Production Test Definition

## Status

CLOSED / DECISION RECORDED / NO NEW PRODUCTION TEST REQUIRED NOW

## Context

P6-F.9.49 starts after:

- P6-F.9.46 validated the real production Meta webhook path with owner-accepted successful real WhatsApp sending.
- P6-F.9.47 restored the safety baseline with `WHATSAPP_SENDING_ENABLED=false`.
- P6-F.9.48.1 validated production DB evidence from the real run.
- P6-F.9.48.2 verified the created AppointmentRequest existence and active request count.

Controlled production phone:

- `4917655660163`

Controlled patient name:

- `Nabit Mikan`

Validated AppointmentRequest:

- `SOL-20260613-090329-503926-0163`

Final validated patient state:

- `ST_CITA_PENDIENTE`

## Objective

Define whether another controlled production test is required before moving toward the future human review handoff design.

## Decision

No additional real production sending test is required at this moment.

The previous controlled production run already validated:

- Real Meta inbound webhook delivery.
- Production `/webhook` execution.
- Payload parsing.
- Real `wamid` preservation.
- State transition flow.
- Colombia holiday blocking.
- KB-driven slot presentation.
- Slot selection.
- AppointmentRequest creation.
- Interaction persistence.
- Processed message persistence.
- Patient state persistence.
- Real outbound WhatsApp sending.

Therefore, repeating another production sending test now would add limited value and increase operational risk unnecessarily.

## Current Safety Baseline

The production safety baseline remains:

- `WHATSAPP_SENDING_ENABLED=false`
- No uncontrolled real patients.
- No campaigns.
- No Google Sheets.
- No Telegram.
- No n8n.
- No Calendar.
- No doctor confirmation automation.
- No real sending without a newly named controlled phase.

## Controlled Test Data Decision

Do not delete the existing controlled production evidence automatically.

The controlled patient and AppointmentRequest may remain as audit evidence:

- `telefono = 4917655660163`
- `id_solicitud = SOL-20260613-090329-503926-0163`

If a future clean appointment-flow production test is needed, the reset or archival of this controlled patient must be done as a separate, explicit, named step.

## Decision Options Reviewed

### Option 1 — Keep sending disabled and continue DB/log verification only

Accepted.

This is the safest default because production sending has already been validated once.

### Option 2 — Run another short controlled real-sending test with the same internal phone

Rejected for now.

No current blocker requires another sending activation.

### Option 3 — Reset or archive the controlled patient before future tests

Deferred.

The existing data is useful as production audit evidence. Cleanup should happen only if a future test needs a clean state.

### Option 4 — Start designing the human review handoff

Accepted.

The next useful step is to define how a persisted `AppointmentRequest` in `pendiente_confirmacion` should move into human review by Dra. D'Aleman.

This must start as spec/design only.

## Next Phase

P6-F.9.50 — Human Review Handoff Spec

## Purpose of Next Phase

Define the human review handoff contract before implementing any external adapter.

The next phase should clarify:

- What Dra. D'Aleman needs to see.
- Which AppointmentRequest fields are required for review.
- Which human actions are supported.
- How request statuses transition after human action.
- What Elvira may say to the patient.
- What Elvira must not confirm automatically.
- Whether Google Sheets is only a visual inbox or also a decision surface.
- How Telegram/n8n may later act as auxiliary notification only.

## Out of Scope for P6-F.9.50

Do not implement yet:

- Google Sheets adapter.
- Telegram notification.
- n8n workflow.
- Calendar integration.
- Doctor confirmation automation.
- Campaigns.
- Therapy package/session tracking.
- Real patient activation.
- Real WhatsApp sending.

## Closure Criteria

P6-F.9.49 is closed when:

- The decision is documented.
- Safety baseline remains disabled.
- No runtime code is changed.
- No production sending is activated.
- The next phase is clearly named.

## Conclusion

P6-F.9.49 is CLOSED.

The project should now move to:

P6-F.9.50 — Human Review Handoff Spec

Starting point:

Design the human review lifecycle for persisted AppointmentRequests before introducing Google Sheets, Telegram, n8n, Calendar, or any doctor confirmation automation.
