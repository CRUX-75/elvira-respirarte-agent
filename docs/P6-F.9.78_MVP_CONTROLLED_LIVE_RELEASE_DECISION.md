# P6-F.9.78 — MVP Controlled Live Release Decision

## Status

PLANNED

## Objective

Decide whether Elvira / Respirarte is ready to move from controlled testing into an MVP live release.

This phase exists to avoid endless beta loops.

The goal is not to keep validating artificially forever, but to define a controlled production release with clear safety boundaries, monitoring, and rollback.

## Context

Elvira has already been tested in a real production WhatsApp environment for 24 hours.

That real run revealed multiple bugs and behavioral gaps.

Those bugs were analyzed, fixed, validated, and documented across the latest P6-F.9.x blocks.

Recently validated and closed:

- Appointment flow
- KB-driven availability
- Colombia holiday handling
- Slot selection rules
- AppointmentRequest persistence
- Production Meta webhook path
- Google Sheets human review inbox
- Doctor-facing Google Sheets guide
- Google Sheets runtime policy

## Core Decision

The project should not remain blocked in artificial beta cycles.

Elvira is ready to move into a controlled MVP live release.

This means:

- Real WhatsApp interaction can be enabled.
- Real patient messages may be received.
- Elvira may respond to patients.
- Elvira may register AppointmentRequests.
- Google Sheets may be used as the doctor-facing human review inbox.
- Dra. D'Aleman continues to manually confirm, reject, reschedule, or request missing information.

## MVP Live Configuration

Recommended MVP live configuration:

- `WHATSAPP_SENDING_ENABLED=true`
- `GOOGLE_SHEETS_ENABLED=true`
- `KB_RUNTIME_ENABLED=true`

## What Elvira Is Allowed To Do In MVP

Elvira may:

- receive patient messages through WhatsApp
- answer basic service and scheduling questions
- ask for preferred appointment date
- present available time windows based on KB_Horarios
- register appointment requests
- persist AppointmentRequests in PostgreSQL
- write appointment request rows to Google Sheets
- tell the patient that Dra. D'Aleman will confirm the appointment

## What Elvira Must Not Do Yet

Elvira must not:

- confirm final appointments automatically
- process doctor actions automatically from Google Sheets
- send campaigns
- send mass messages
- create calendar events
- trigger Telegram notifications
- trigger n8n workflows
- manage therapy packages or session tracking
- replace Dra. D'Aleman's final decision

## Human Review Process

During MVP:

1. Patient writes to WhatsApp.
2. Elvira handles the conversation.
3. Elvira registers the appointment request.
4. Request is stored in PostgreSQL.
5. Request appears in Google Sheets.
6. Dra. D'Aleman reviews the row manually.
7. Dra. D'Aleman contacts or confirms with the patient manually.
8. No automated doctor-action processing happens yet.

## Launch Boundaries

The MVP live release is approved only under these boundaries:

- No campaigns.
- No public marketing push yet.
- No mass patient activation.
- No automated doctor confirmation.
- No Calendar integration.
- No Telegram integration.
- No n8n workflow.
- Logs and Google Sheets must be monitored during the first live window.
- Rollback must be available immediately.

## First Live Window

Recommended first MVP live window:

- Duration: 24 to 48 hours
- Scope: real inbound patients only if they naturally contact the WhatsApp number or are manually invited by the doctor/operator
- Monitoring: active operator supervision

Evidence to observe:

- WhatsApp responses
- LangSmith traces
- production logs
- PostgreSQL AppointmentRequests
- Google Sheets rows
- patient state transitions

## Rollback Plan

If unexpected behavior appears:

1. Set `WHATSAPP_SENDING_ENABLED=false`.
2. Optionally set `GOOGLE_SHEETS_ENABLED=false`.
3. Keep `KB_RUNTIME_ENABLED=true`.
4. Preserve logs and database evidence.
5. Do not delete evidence immediately.
6. Review the failing case.
7. Patch only after understanding the root cause.

## Success Criteria

The MVP live release is successful if:

- Elvira responds safely to real patient messages.
- No final appointment is confirmed automatically.
- AppointmentRequests are created correctly.
- Google Sheets receives rows correctly.
- Dra. D'Aleman can review requests manually.
- No duplicate active AppointmentRequests are created unexpectedly.
- No serious misunderstanding or unsafe patient-facing behavior is observed.
- Rollback remains available.

## Decision

Approved direction:

Move to MVP Controlled Live Release.

This is no longer a dry beta.

The next phase should prepare the production activation checklist for this controlled MVP release.

## Closure Criteria

P6-F.9.78 can be closed when:

- The MVP release decision is documented.
- Runtime boundaries are clear.
- Rollback plan is clear.
- Success criteria are clear.
- Next activation phase is named.
