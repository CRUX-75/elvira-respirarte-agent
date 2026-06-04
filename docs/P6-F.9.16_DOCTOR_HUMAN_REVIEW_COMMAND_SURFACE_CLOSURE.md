# P6-F.9.16 — Doctor Human Review Command Surface Closure

## Status

CLOSED / ARCHITECTURE SPEC SEALED

## Closed Scope

This block closed the architecture/spec phase for the Doctor Human Review Command Surface.

Closed microblocks:

- P6-F.9.16.1 — DoctorDecision Contract Design
- P6-F.9.16.2 — Telegram Command Surface Contract
- P6-F.9.16.3 — Backend Action Validation Contract
- P6-F.9.16.4 — Endpoint Strategy Decision

## Final Architecture Decision

The doctor review flow follows this architecture:

- Telegram = command surface / notification surface
- n8n = optional auxiliary plumbing
- FastAPI = validation, decisions, transitions, audit boundary
- PostgreSQL = source of truth
- WhatsApp = patient communication channel

## Critical Boundary

n8n must not own critical business logic.

n8n must not decide:

- appointment request state
- doctor decision validity
- appointment lifecycle transitions
- patient communication logic
- persistence rules
- confirmation/rejection/reagendamiento logic

Those responsibilities belong to FastAPI/Python and PostgreSQL.

## Telegram Workflow Recovery Decision

The previous n8n Telegram workflow was lost.

This is not considered critical because n8n is not the source of truth and must not contain business-critical scheduling logic.

The workflow can be rebuilt later as a minimal notification plumbing workflow:

Webhook n8n
→ Format payload
→ Send Telegram message

No appointment decision logic should be rebuilt inside n8n.

## Sealed Doctor Review Direction

Doctor review must remain human-in-the-loop.

Elvira collects the request.

The backend persists and validates.

The doctor reviews and decides.

The system records the decision.

## Out of Scope For This Closure

This closure does not implement:

- Telegram notification workflow
- n8n workflow reconstruction
- DoctorDecision runtime implementation
- Google Sheets adapter
- WhatsApp real sending changes
- real /webhook changes
- automatic appointment confirmation
- calendar integration

## Next Recommended Block

P6-F.9.17 — Telegram Notification Plumbing / DoctorDecision Implementation Plan

Recommended order:

1. Define minimal Telegram notification payload.
2. Decide whether FastAPI sends directly to Telegram or triggers n8n as plumbing.
3. If n8n is used, keep it stateless and minimal.
4. Prepare DoctorDecision implementation plan.
5. Do not implement doctor approval logic inside n8n.

## Conclusion

P6-F.9.16 is closed as an architecture/spec milestone.

The doctor review command surface is now architecturally bounded:

FastAPI validates.
PostgreSQL persists.
Telegram displays/receives commands.
n8n only transports when useful.
