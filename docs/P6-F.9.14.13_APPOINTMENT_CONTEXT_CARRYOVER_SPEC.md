# P6-F.9.14.13 — Appointment Context Carryover SPEC

## Status

PLANNED

## Problem

AppointmentRequest persistence currently fails after the patient selects a time window.

Observed production dry-run:

1. Patient says: "El viernes"
2. Runtime resolves:
   - fecha_solicitada = 2026-05-29
   - slots_candidatos = ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."]
   - nuevo_estado = ST_CITA_FRANJA
3. Patient says: "En la tarde"
4. Runtime correctly classifies:
   - intent = hora_cita
   - nuevo_estado = ST_CITA_PENDIENTE
   - next_action = confirm_appointment_request
5. But AppointmentRequest persistence is skipped:
   - reason = skipped_missing_fecha_solicitada

Root cause:

The date context from the previous turn is not persisted across messages.

## Current Persistence

`patients` persists:

- telefono
- nombre
- estado_actual
- opt_out
- timestamps

`interactions` persists:

- mensaje
- respuesta
- intent
- estado_anterior
- nuevo_estado
- next_action
- state_reason
- versions
- kb flags
- WhatsApp metadata

Neither table currently persists the active appointment date context.

## Decision

Persist active appointment context in `patients`.

New column:

```sql
appointment_context JSONB

This field stores only the active conversational appointment context needed to continue a pending appointment request.

Appointment Context Contract

Expected shape:

{
  "fecha_solicitada": "2026-05-29",
  "fecha_solicitada_texto": "viernes 29 de mayo",
  "slots_candidatos": [
    "3:00 p. m.–5:00 p. m.",
    "5:00 p. m.–7:00 p. m."
  ],
  "es_dia_disponible": true,
  "is_weekend": false,
  "is_colombia_holiday": false,
  "colombia_holiday_name": null
}
Capture Rule

Store appointment context when:

result.intent == "fecha_cita"
result.nuevo_estado == "ST_CITA_FRANJA"
result.fecha_solicitada is present
Carryover Rule

Apply stored appointment context when:

result.intent == "hora_cita"
result.nuevo_estado == "ST_CITA_PENDIENTE"
result.fecha_solicitada is missing
patient.appointment_context has a stored fecha_solicitada

The runtime should fill:

fecha_solicitada
fecha_solicitada_texto
slots_candidatos
es_dia_disponible
is_weekend
is_colombia_holiday
colombia_holiday_name

before calling decide_appointment_request_persistence(...).

Clear Rule

Clear appointment context when:

request is persisted successfully
opt_out becomes true
flow leaves appointment states in a later cleanup phase

For this block, minimum required clear behavior:

clear after successful AppointmentRequest persistence
clear on opt_out
Safety Boundaries

Still out of scope:

POST /webhook wiring
real WhatsApp sending
Google Sheets
Telegram
n8n
doctor confirmation
calendar integration
therapy/session package tracking
Success Criteria

The same Swagger dry-run flow should complete:

"Hola buenos días"
"Quiero pedir una cita"
"El viernes"
"En la tarde"

Expected final response:

intent = hora_cita
nuevo_estado = ST_CITA_PENDIENTE
appointment_request_decision.should_persist = true
appointment_request.estado_solicitud = pendiente_confirmacion
appointment_request.source_interaction_id = whatsapp_message_id
