# DBG-001 — Absolute Date Resolution Regression

Status: Closed
Production closure date: 2026-07-18

## Reported Behavior

Elvira failed to resolve absolute appointment dates in these production inputs:

- `Necesito una cita el 23 de julio`
- `18 de julio`
- `18/07/2026`

The first input repeated the date question. Standalone dates were classified as general conversation.

## Root Cause

Two deterministic gaps were identified:

1. The textual absolute-date parser required an explicit four-digit year.
2. The appointment-context intent router did not recognize standalone textual or numeric absolute dates.

The graph execution order was correct and did not require modification.

## Implemented Fix

- Accept Spanish textual dates with or without an explicit year.
- Use the current Colombia year when the textual date omits the year.
- Accept numeric `DD/MM/YYYY` and `DD-MM-YYYY` formats.
- Classify absolute dates as `fecha_cita` while Elvira is inside an appointment-date context.
- Preserve the existing deterministic core, availability guards, weekend handling and appointment state transitions.

## Automated Evidence

Regression tests were added for:

- an absolute date embedded in an appointment request;
- a standalone textual absolute date;
- a standalone numeric absolute date;
- weekend rejection after numeric resolution;
- transition from `ST_INIT` to `ST_CITA_FRANJA`;
- preservation of the missing or unavailable-date guard.

Test execution was partitioned to avoid repeating the slow stateful block:

- critical appointment and stateful partition: 94 passed;
- remaining repository partition: 289 passed;
- total validated coverage: 383 tests.

## Git Evidence

- Fix commit: `1a31652`
- Production merge commit: `c0c150c`
- Rollback tag: `pre-dbg-001-absolute-date-fix-2026-07-18`

## Production Validation

The deployed production container returned:

- `/health`: HTTP 200, status `ok`;
- `/ready`: HTTP 200, status `ready`.

Validated through the non-persistent `/test/message` endpoint:

- `Necesito una cita el 23 de julio`
  - intent: `cita`
  - resolved date: `2026-07-23`
  - new state: `ST_CITA_FRANJA`
  - next action: `ask_preferred_time`

- `18 de julio`
  - intent: `fecha_cita`
  - resolved date: `2026-07-18`
  - weekend: true
  - new state: `ST_CITA_FECHA`
  - next action: `ask_preferred_date`

- `18/07/2026`
  - intent: `fecha_cita`
  - resolved date: `2026-07-18`
  - weekend: true
  - new state: `ST_CITA_FECHA`
  - next action: `ask_preferred_date`

No patient, interaction or appointment record was persisted during this validation.

## Scope Boundaries

This debugging closure did not modify:

- voice input or output;
- WhatsApp transport;
- database schema;
- environment variables;
- patient follow-up;
- the frozen voice roadmap.

Past-date policy and year rollover were not changed in DBG-001.

The incorrect mapping of `3:00 a 5:00` to the second slot remains isolated as the future `DBG-002 — Slot Range Mapping Regression`.
