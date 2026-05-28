# P6-F.9.14.21 — Appointment Initial Copy + Slot Disclaimer Polish

## Status

SPEC CREATED / READY FOR RED TESTS

## Background

P6-F.9.14.20 validated the controlled stateful Swagger dry-run for AppointmentRequest runtime persistence.

The technical flow is green:

- `Quiero pedir una cita` moves the patient to `ST_CITA_FECHA`.
- `Maniana en la tarde` resolves the requested date and candidate afternoon slots.
- `A las 3` moves the flow to `ST_CITA_PENDIENTE`.
- `AppointmentRequest` is created in PostgreSQL.
- `estado_solicitud = pendiente_confirmacion`.
- `source_interaction_id` uses the synthetic `test-stateful-*` ID.
- Real WhatsApp sending remains disabled.

However, the dry-run exposed a product/copy issue:

The initial response to:

`Quiero pedir una cita`

currently says something like:

`Claro, me refiero a la fecha de la cita. ¿Para qué día le gustaría agendarla?`

This sounds unnatural and confusing as an initial appointment response. It only makes sense as a clarification after the patient asks something like `¿cuál fecha?`.

## Approved Product Decision

When the patient initiates an appointment request, Elvira must respond warmly and explain the general domiciliary appointment constraint from the beginning.

Approved base copy:

`Claro, con muchísimo gusto. Le cuento que las atenciones domiciliarias se manejan solamente en la tarde, normalmente en dos franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Para qué día le gustaría agendar su cita?`

## Important Safety Boundary

This initial response may mention the general afternoon windows, but it must not confirm real availability for a specific date yet.

Reason:

At the initial `cita` turn, Elvira does not know the requested date yet.

The message may say:

- domiciliary visits are generally in the afternoon
- normal candidate windows are 3–5 and 5–7
- ask for the desired appointment date

It must not say:

- `tengo disponible`
- `le confirmo`
- `queda agendada`
- anything that implies actual date-specific availability

## Desired Behavior

### Case 1 — Initial appointment request

Input:

`Quiero pedir una cita`

Expected:

- `intent = cita`
- `nuevo_estado = ST_CITA_FECHA`
- `next_action = ask_preferred_date`
- `appointment_request_decision.should_persist = false`
- response includes a warm opening
- response includes the general afternoon-only domiciliary rule
- response includes the general 3–5 and 5–7 windows
- response asks for the desired date
- response does not include `me refiero a la fecha de la cita`

### Case 2 — Clarification question inside appointment-date context

Input examples:

- `Cual fecha indicada?`
- `Cuál fecha?`
- `No entendí`
- `Qué quiere decir?`

Expected:

- remains in appointment-date context
- asks again for the appointment date
- may clarify naturally that Elvira means the day for the appointment
- must not use the initial appointment copy as if it were a fresh request

Preferred clarification copy:

`Disculpe, me refiero al día en que le gustaría agendar la cita. ¿Qué día le queda bien?`

## Explicitly Out of Scope

Do not touch:

- `/webhook`
- real WhatsApp sending
- Google Sheets
- Telegram
- n8n
- doctor confirmation flow
- calendar integration
- therapy/session package tracking
- AppointmentRequest lifecycle model
- PostgreSQL schema

## Likely Files

Inspect first:

- `app/services/llm.py`
- `app/prompts/elvira_system.txt`
- `tests/test_state_machine.py`
- any existing response/copy tests

Recommended first command:

```bash
grep -R "me refiero a la fecha" -n app tests
Development Protocol

Follow SDD:

Inspect current copy source.
Write RED test for initial cita response.
Write RED/adjusted test for clarification response if needed.
Implement minimal copy change.
Run targeted tests.
Run full suite.
Update AI_CONTEXT.md.
Commit.
Safety Rule

This block is copy/prompt polish only.

No runtime architecture changes.
