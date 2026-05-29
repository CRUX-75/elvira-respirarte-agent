# P6-F.9.14.27 — KB-Based Exact-Hour Franja Clarification Guard SPEC

## Status

SPEC CREATED / READY FOR TESTS

## Reason

During P6-F.9.14.26 production dry-run, the technical slot mapping was validated for:

- `se puede a las 5?` → `5:00 p. m.–7:00 p. m.`

However, after reviewing the appointment contract with Dra. D'Aleman, a product-level clarification was introduced:

Patients may ask for an exact hour inside a valid appointment franja, for example:

- `se puede a las 4?`
- `a las 6`
- `puede venir a las 4?`

The system must not respond brusquely or block the patient unnecessarily.

The correct behavior is to explain politely that Respirarte works by time windows/franjas, not exact guaranteed hours, and then ask the patient to confirm the corresponding franja.

## Contract Basis

Operational principle:

Elvira recoge.  
La doctora decide.  
El sistema registra.

Elvira must not:

- confirm real availability
- approve or reject appointments
- promise exact hour inside a franja

Elvira may:

- collect appointment intent
- collect preferred date
- present KB-backed franjas
- collect preferred franja
- register an AppointmentRequest after the patient confirms a valid franja

## Validated Doctor Decisions

Dra. D'Aleman validated:

1. Expected response time:
   - 30–60 minutes.

2. Patient terminal message after request registration:
   - “Hemos recibido su solicitud, pronto recibirá confirmación de la hora en que recibirá la atención.”

3. Doctor notification channel:
   - WhatsApp.

4. Exact-hour requests:
   - The patient should be told politely that care is handled by time window/franja.
   - It is not possible to guarantee an exact hour inside the assigned block.
   - The patient should be advised to keep the full time window available.

5. Out-of-hours message:
   - “Gracias por escribirnos. En este momento nuestro horario de atención ha finalizado, pero hemos recibido su mensaje. Pronto nos pondremos en contacto para ayudarte con tu agendamiento.”

## Source of Truth for Franjas

The system must use KB_Horarios as the source of truth for valid appointment franjas.

Do not hardcode only `3:00 p. m.–5:00 p. m.`.

The doctor's example mentioning 3–5 is treated as an example, not a fixed global response.

Examples from KB_Horarios:

- Monday / Tuesday / Thursday / Friday:
  - `3:00 p. m.–5:00 p. m.`
  - `5:00 p. m.–7:00 p. m.`

- Wednesday:
  - `3:00 p. m.–5:00 p. m.`
  - `5:00 p. m.–6:00 p. m.` if configured as visible in KB

- Saturday / Sunday / Colombian holidays:
  - no standard domiciliary service

## New Behavior

### Case 1 — Exact hour inside a visible KB franja

Example:

Patient already selected a valid date with available slots:

- `3:00 p. m.–5:00 p. m.`
- `5:00 p. m.–7:00 p. m.`

Patient says:

`se puede a las 4?`

Expected behavior:

- Do not persist AppointmentRequest yet.
- Do not confirm exact hour.
- Detect that `4` belongs to `3:00 p. m.–5:00 p. m.`
- Stay in `ST_CITA_FRANJA`.
- Set next_action to something like:
  - `ask_confirm_exact_hour_as_slot`
- Store pending franja in appointment context.
- Ask patient to confirm the corresponding franja.

Expected response direction:

“Con gusto. Le cuento que la atención domiciliaria se maneja por franjas horarias, por lo que no es posible garantizar una hora exacta dentro del bloque asignado. Para ese día, la hora que menciona corresponde a la franja de 3:00 p. m. a 5:00 p. m. ¿Desea que registre su solicitud para esa franja?”

### Case 2 — Exact hour inside second visible KB franja

Patient says:

`se puede a las 6?`

If KB_Horarios for that date includes:

`5:00 p. m.–7:00 p. m.`

Expected behavior:

- Do not persist yet.
- Explain franja policy.
- Propose `5:00 p. m.–7:00 p. m.`
- Ask confirmation.

Expected response direction:

“Con gusto. Le cuento que la atención domiciliaria se maneja por franjas horarias, por lo que no es posible garantizar una hora exacta dentro del bloque asignado. Para ese día, la hora que menciona corresponde a la franja de 5:00 p. m. a 7:00 p. m. ¿Desea que registre su solicitud para esa franja?”

### Case 3 — Patient confirms proposed franja

After Case 1 or Case 2, patient says:

- `sí`
- `si`
- `claro`
- `perfecto`
- `está bien`
- `de acuerdo`

Expected behavior:

- Use pending franja from appointment context.
- Persist AppointmentRequest.
- Move to `ST_CITA_PENDIENTE`.
- Set AppointmentRequest status to pending human review.
- Send terminal message based on doctor-approved copy.

Expected terminal response direction:

“Hemos recibido su solicitud. Pronto recibirá confirmación de la franja en que recibirá la atención. Normalmente le confirmaremos en un lapso aproximado de 30 a 60 minutos.”

### Case 4 — Exact hour outside all KB franjas

Patient says:

- `a las 2`
- `a las 8`
- `a las 10`

Expected behavior:

- Do not persist.
- Stay in `ST_CITA_FRANJA`.
- Show valid KB-backed franjas.
- Ask patient to choose one.

Expected response direction:

“Gracias por indicarlo. Para ese día la atención domiciliaria solo está disponible dentro de estas franjas: 3:00 p. m. a 5:00 p. m. o 5:00 p. m. a 7:00 p. m. ¿Cuál de las dos le queda mejor?”

## State Machine Recommendation

Do not create a new state yet.

Keep:

`ST_CITA_FRANJA`

Use a new `next_action` for the clarification step:

`ask_confirm_exact_hour_as_slot`

The selected candidate franja should be stored in appointment context, for example:

```json
{
  "pending_exact_hour_franja": "3:00 p. m.–5:00 p. m.",
  "pending_exact_hour_text": "se puede a las 4?",
  "pending_exact_hour_requires_confirmation": true
}

When the patient confirms, the system should use this pending franja to create the AppointmentRequest.

Architecture Boundaries

Do not touch yet:

real POST /webhook
real WhatsApp sending
Google Sheets adapter
Doctor WhatsApp Notification Adapter
Telegram
n8n
Calendar
therapy/session package tracking

n8n remains excluded from the core appointment scheduling flow.

Next Implementation Plan

Follow SDD:

Add tests for exact-hour inside first franja.
Add tests for exact-hour inside second franja.
Add tests for exact-hour outside all franjas.
Add tests for patient confirmation after exact-hour clarification.
Implement pure helper to resolve exact hour against KB-backed slots.
Wire helper into /test/message-stateful only.
Keep real /webhook untouched.
Run targeted tests.
Run full suite.
Update AI_CONTEXT.md.
Commit.
