# P6-F.9.70 — Human Review Inbox Operational Readiness Review

## Status

SPEC / CONTRACT REVIEW / NO RUNTIME IMPLEMENTATION YET

## Context

P6-F.9.69 was closed GREEN.

Validated:

- `/test/message-stateful` works.
- AppointmentRequest is persisted in PostgreSQL.
- Google Sheets human review inbox was validated with `human_review_inbox.status=appended`.
- A row was visually confirmed in `Solicitudes_Cita`.
- `WHATSAPP_SENDING_ENABLED=false`.
- `GOOGLE_SHEETS_ENABLED` must remain false by default except during controlled phases.
- `KB_RUNTIME_ENABLED=true` remains active.

Dra. D’Aleman reviewed the `Solicitudes_Cita` table and provided operational feedback.

## Doctor Feedback

The doctor requested or confirmed:

1. Add column: `Cita primera vez o control`.
2. Add required patient data: `EPS`.
3. `Dirección o punto del domicilio` must be mandatory.
4. `Servicio solicitado` must always appear.
5. Add column: `Barrio`.
6. Add patient age.
7. Do not add `Motivo de consulta` for now.
8. Do not add `Prioridad o urgencia` for now.
9. Add brief clinical notes, but this remains pending definition with Nabit.
10. No technical columns were confusing.

## Objective

Adapt the operational contract of the human review inbox according to real doctor feedback before implementing more automation.

This phase defines the contract first.

No real WhatsApp activation, Telegram, n8n, Calendar, or doctor automation will be implemented in this phase.

## Scope

Define the updated human review inbox contract for:

- PostgreSQL AppointmentRequest model alignment.
- Google Sheets human review inbox columns.
- Required vs optional operational fields.
- Future readiness checks before a request is considered complete for human review.

## New Fields To Add To The Contract

| Field | Meaning | Required Now? | Notes |
|---|---|---:|---|
| `tipo_cita` | Whether the appointment is first visit or follow-up/control | No | Doctor requested: “Cita primera vez o control” |
| `eps` | Patient EPS / insurance entity | No | Doctor requested it as additional data |
| `barrio` | Neighborhood / zone in Bogotá | No | Doctor requested “Barrio” |
| `edad_paciente` | Patient age | No | Doctor requested age |
| `notas_clinicas_breves` | Short clinical notes | No | Pending definition with Nabit and doctor |

## Fields That Must Become Mandatory Before Human Review Readiness

| Field | Required? | Reason |
|---|---:|---|
| `direccion_domicilio` | Yes | Doctor needs the location or address point to evaluate domiciliary care |
| `servicio_solicitado` | Yes | Doctor needs to know what service the patient is requesting |

## Fields Not Added For Now

| Field | Decision | Reason |
|---|---|---|
| `motivo_consulta` | Do not add now | Doctor said no |
| `prioridad_urgencia` | Do not add now | Doctor said no |

## Operational Readiness Rule

An AppointmentRequest can exist in PostgreSQL even if some operational fields are missing.

However, a request should not be considered fully ready for human review unless it contains at least:

- `direccion_domicilio`
- `servicio_solicitado`

This phase only defines the rule.

It does not yet implement automatic patient follow-up messages to collect missing fields.

## Google Sheets Contract Impact

The `Solicitudes_Cita` sheet should eventually include these additional visible columns:

- `tipo_cita`
- `eps`
- `barrio`
- `edad_paciente`
- `notas_clinicas_breves`

Existing columns remain valid:

- `id_solicitud`
- `fecha_registro`
- `telefono`
- `nombre_paciente`
- `fecha_solicitada_texto`
- `franja_aceptada`
- `modalidad`
- `estado_solicitud`
- `observaciones_elvira`
- `interaction_id_origen`
- `direccion_domicilio`
- `servicio_solicitado`
- `fecha_confirmada`
- `franja_confirmada`

## Out Of Scope

Do not implement in this phase:

- Real `/webhook` changes.
- `WHATSAPP_SENDING_ENABLED=true`.
- Google Sheets enabled by default.
- Telegram.
- n8n.
- Calendar.
- Doctor confirmation automation.
- Patient response automation for missing fields.
- Campaigns.
- Real patient activation.

## Safety Baseline

Must remain:

- `WHATSAPP_SENDING_ENABLED=false`
- `GOOGLE_SHEETS_ENABLED=false` by default
- `KB_RUNTIME_ENABLED=true`

Google Sheets may only be enabled during a named controlled validation phase.

## Proposed Next Phase

P6-F.9.71 — Human Review Inbox Contract Implementation Plan

Purpose:

Define exactly which files must change before implementation, likely including:

- `app/models/appointment_request.py`
- database migration script
- Google Sheets writer mapping
- Google Sheets header contract tests
- AppointmentRequest service readiness logic tests

No implementation should start until P6-F.9.70 is reviewed and accepted.
