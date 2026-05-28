# P6-F.9.14.19 — Appointment Flow Hardening: Relative Dates, Time Windows & Clarification Guards

## Status

SPEC DRAFT / READY FOR TESTS

## Objective

Harden Elvira's appointment flow before any production WhatsApp activation.

The system must correctly handle real patient language around appointment dates and time windows, especially ambiguous Spanish expressions such as:

- mañana en la tarde
- manana en la tarde
- maniana en la tarde
- mañana en la mañana
- manana en la manana
- maniana en la maniana
- en la mañana
- en la tarde
- cuál fecha indicada?
- no entendí

The goal is to prevent unsafe appointment state transitions and prevent Elvira from referring to missing dates as if they existed.

## Production Finding

During Swagger validation of `/test/message-stateful`, the message:

```text
Maniana en la tarde

produced:

{
  "intent": "fecha_cita",
  "nuevo_estado": "ST_CITA_FRANJA",
  "fecha_solicitada": null,
  "slots_candidatos": []
}

Elvira then answered with a vague phrase:

Perfecto, se refiere a la fecha indicada...

This is not production-safe.

The system moved to an appointment time-window state without having a resolved appointment date.

Core Safety Rule

Elvira must never advance to an operational appointment state unless the minimum required structured data exists.

The model may phrase responses, but it must not compensate for missing deterministic state.

Architecture Rule

This must be solved deterministically.

The LLM must not decide:

whether a relative date is valid
whether a date was resolved
whether a time window is valid
whether the system can advance to ST_CITA_FRANJA
whether the system can advance to ST_CITA_PENDIENTE
whether an AppointmentRequest can be persisted

The deterministic flow must parse, validate, and protect the state machine first.

Required Parsing Model

Relative date and time window must be parsed independently.

Example:

mañana en la mañana

means:

relative_date = tomorrow
time_window = morning

Example:

mañana en la tarde

means:

relative_date = tomorrow
time_window = afternoon

Example:

en la mañana

means:

relative_date = missing
time_window = morning
Relative Date Normalization

The system must normalize and resolve:

mañana
manana
maniana
pasado mañana
pasado manana
pasado maniana

Expected behavior:

mañana / manana / maniana = fecha_actual_colombia + 1 day
pasado mañana / pasado manana / pasado maniana = fecha_actual_colombia + 2 days

The resolved date must populate:

fecha_solicitada
fecha_solicitada_texto
dia_semana_solicitado
date_resolution_source
Time Window Normalization

The system must normalize:

en la mañana
por la mañana
manana as time window only when context clearly means morning
maniana as time window only when context clearly means morning
en la tarde
por la tarde
tarde
en la noche
por la noche
noche

The parser must distinguish:

mañana en la tarde

from:

en la mañana

In the first case, mañana is a relative date.

In the second case, mañana is a time window.

KB Schedule Contract

Current schedule source:

schedule_id,day_type,day_name,modality,start_time,end_time,slot_duration_minutes,max_patients,location_type,is_available,notes
HOR-01,weekday,Lunes a viernes (excepto miércoles),Domiciliaria,15:00,19:00,120,2,Domicilio paciente,true,Máximo 2 pacientes por día. Franja visible al paciente: 2 horas. Slot 1: 15:00–17:00. Slot 2: 17:00–19:00. Buffer de 60 min entre citas por desplazamiento en Bogotá.
HOR-02,weekday,Miércoles,Domiciliaria,15:00,18:00,120,1,Domicilio paciente,true,Máximo 1 paciente. Solo Slot 1: 15:00–17:00. No cabe segundo slot antes del cierre a las 18:00.
HOR-03,saturday,Sábado,Sin atención domiciliaria,—,—,—,0,—,false,Sin servicio domiciliario los sábados.
HOR-04,sunday,Domingo,Sin atención,—,—,—,0,—,false,Sin atención domingos ni festivos, salvo indicación expresa de la Dra. D'Aleman.

The deterministic system must use this schedule information to decide whether requested time windows are valid.

Morning Request Rule

If the patient requests a valid date but an invalid domiciliary time window such as morning:

mañana en la mañana
manana en la manana
maniana en la maniana

Elvira must not reject the date.

Elvira must:

Resolve the date.
Confirm the resolved date.
Explain that domiciliary care is only available in the afternoon.
Offer valid KB-backed slots for that date.
Stay in appointment flow.

Example response:

Perfecto, ¿se refiere a mañana viernes 29 de mayo? Para atención domiciliaria, la doctora atiende en la tarde. Para ese día puedo registrar como preferencia estas franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Alguna de esas opciones le sirve?
Afternoon Request Rule

If the patient says:

mañana en la tarde
manana en la tarde
maniana en la tarde

and the resolved date is available, Elvira must:

Resolve the date.
Confirm the resolved date.
Present valid KB-backed afternoon slots.
Ask which slot works better.

Example response:

Perfecto, ¿se refiere a mañana viernes 29 de mayo? Para ese día puedo registrar como preferencia estas franjas: de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. ¿Cuál le sirve mejor?
Wednesday Rule

If the resolved date is Wednesday, Elvira must only offer the valid Wednesday slot:

15:00–17:00

Example:

Perfecto, ¿se refiere a mañana miércoles 3 de junio? Para atención domiciliaria, la doctora atiende en la tarde. Ese día puedo registrar como preferencia la franja de 3:00 p. m. a 5:00 p. m. ¿Le sirve esa opción?
Saturday Rule

If the resolved date is Saturday, Elvira must not offer domiciliary slots.

Example:

Perfecto, ¿se refiere a mañana sábado 30 de mayo? Los sábados no hay servicio domiciliario. ¿Desea que revisemos una opción de lunes a viernes en la tarde?
Sunday / Holiday Rule

If the resolved date is Sunday or Colombia holiday, Elvira must not offer normal slots.

Example:

Perfecto, ¿se refiere a mañana domingo 31 de mayo? Los domingos y festivos no hay atención, salvo indicación expresa de la Dra. D'Aleman. ¿Desea que revisemos una opción de lunes a viernes en la tarde?
ST_CITA_FRANJA Guard

The system may only move to:

ST_CITA_FRANJA

when:

intent == "fecha_cita"
fecha_solicitada is present
date resolution succeeded

If fecha_solicitada is missing, the system must not move to ST_CITA_FRANJA.

It must remain in date collection mode and ask for clarification.

Invalid behavior:

{
  "nuevo_estado": "ST_CITA_FRANJA",
  "fecha_solicitada": null
}
ST_CITA_PENDIENTE Guard

The system may only move to:

ST_CITA_PENDIENTE

when:

intent == "hora_cita"
fecha_solicitada exists in current state or patient appointment_context
a valid or correctable time preference exists
appointment request persistence decision allows it

If date context is missing, Elvira must ask for the date again.

Vague Date Phrase Guard

Elvira must not use these phrases unless fecha_solicitada_texto exists:

la fecha indicada
ese día
la fecha solicitada
la fecha mencionada

If the date is missing, Elvira must ask for clarification.

Correct fallback:

Disculpe, me faltó precisar la fecha. ¿Para qué día le gustaría solicitar la cita?
Clarification Handling

If the patient asks something like:

cuál fecha?
cuál fecha indicada?
qué fecha indicada?
no entendí
qué quiere decir?
no sé cuál fecha

inside an appointment flow, Elvira must not treat this as a broad general question.

It must answer with a short appointment clarification.

Example:

Disculpe, me faltó precisar la fecha. ¿Para qué día le gustaría solicitar la cita?
Required Test Scenarios

At minimum, add tests for:

Maniana en la tarde in ST_CITA_FECHA
resolves tomorrow
produces fecha_solicitada
offers afternoon slots
may move to ST_CITA_FRANJA
Maniana en la maniana in ST_CITA_FECHA
resolves tomorrow
detects morning request
corrects to afternoon domiciliary slots
does not accept morning as valid slot
En la maniana in ST_CITA_FECHA
detects morning time window
does not invent a date
asks for date clarification
Cual fecha indicada? in ST_CITA_FRANJA
does not answer as broad general
asks for date clarification
avoids loading unnecessary KB if possible
Any fecha_cita result without fecha_solicitada
must not transition to ST_CITA_FRANJA
Any response with fecha_solicitada_texto = null
must not contain "fecha indicada"
Out of Scope

Do not touch:

real POST /webhook
WhatsApp sending
Google Sheets
Telegram
n8n
Calendar
doctor confirmation automation
therapy/session package tracking
Acceptance Criteria

This block is closed only when:

tests reproduce the current bug
date normalization handles mañana/manana/maniana
time-window parsing distinguishes tomorrow from morning
state machine does not advance without required structured data
Elvira does not say "fecha indicada" without a resolved date
full pytest suite passes
AI_CONTEXT.md is updated
working tree is clean

