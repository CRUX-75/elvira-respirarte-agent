# P6-F.9.6 — AppointmentRequest Factory

## Status

Draft specification — SDD first pass.

No implementation code must be written before this specification is reviewed and accepted.

---

## 1. Purpose

This document defines the creation rules for a new internal `AppointmentRequest`.

The factory is responsible for building a valid `AppointmentRequest` object consistently when the backend determines that a patient appointment request should exist.

This phase does not implement persistence, Google Sheets, calendar automation, Telegram notifications, or n8n workflows.

---

## 2. Contractual Sources

This factory specification is based on:

```text
docs/P6-F.9.1_SOLICITUDES_CITA_OPERATIONAL_CONTRACT.md
docs/P6-F.9.2_APPOINTMENT_REQUEST_INTERNAL_MODEL.md
docs/P6-F.9.4_APPOINTMENT_REQUEST_LIFECYCLE_VALIDATION.md

The factory must remain aligned with the operational contract, the internal model, and the lifecycle validation rules.

3. Scope
In scope

This phase defines:

When a new AppointmentRequest may be created.
Which fields are required at creation time.
Which fields may be optional at creation time.
How id_solicitud should be generated.
How initial timestamps should be generated.
How Colombia timezone should be handled for visible request IDs.
Which initial states are allowed.
What the factory must not do.
Out of scope

The following are explicitly excluded:

Database persistence.
Repository layer.
Google Sheets implementation.
Google Sheets append/update logic.
Google Calendar integration.
Calendar availability checking.
Automatic appointment confirmation.
Telegram notifications.
n8n workflows.
Therapy-session tracking.
Treatment package tracking.
Remaining-session counters.
Updating an existing request.
Searching for existing open requests.
4. Core Rule

The factory creates an appointment request.

It does not confirm an appointment.

Therefore, at creation time:

fecha_confirmada = None
franja_confirmada = None
estado_solicitud != confirmada

The factory must never create a request already confirmed.

5. When to Create an AppointmentRequest

A new AppointmentRequest may be created when the deterministic backend flow detects that:

intent = cita

and there is no existing active appointment request for the same patient and same appointment conversation context.

The factory itself does not search for existing requests.

That responsibility belongs to a future service or repository layer.

The factory only creates a new object when it is explicitly called by a higher-level service.

6. Anti-Duplication Principle

Contraoffers and renegotiation must remain in the same appointment request.

A new request must not be created just because:

- the patient accepts an alternative date
- the patient changes the preferred time range
- the doctor proposes another slot
- Elvira asks for missing data
- the request moves from requested to accepted data

This factory does not implement duplicate detection.

However, the specification establishes that future orchestration must check for an existing active request before calling the factory.

7. Required Creation Inputs

The factory must require at least:

telefono

Recommended optional inputs:

nombre_paciente
source_interaction_id
intent_origen
canal_origen
fecha_solicitada
franja_solicitada
hora_solicitada_texto
servicio_solicitado
direccion_domicilio
observaciones

The following values should be generated internally by the factory:

id_solicitud
estado_solicitud
created_at
updated_at
created_by
8. Initial State Rules

The factory may create requests with only these initial states:

nueva
pendiente_datos
pendiente_confirmacion

Default state:

nueva

Recommended logic:

If only appointment intent exists:
    estado_solicitud = nueva

If appointment intent exists but required operational data is missing:
    estado_solicitud = pendiente_datos

If enough operational data is already available for human review:
    estado_solicitud = pendiente_confirmacion

The factory must not create requests with:

confirmada
reagendada
cancelada
cerrada

Those states belong to later lifecycle transitions.

9. Required Data for Human Review

A request may be considered ready for human review when it has enough operational context, such as:

telefono
fecha_solicitada or fecha_aceptada
franja_solicitada or franja_aceptada

The following fields are important but may be progressively collected:

servicio_solicitado
direccion_domicilio

The first implementation may keep readiness logic conservative and explicit.

If there is uncertainty, prefer:

pendiente_datos

over:

pendiente_confirmacion
10. ID Generation

The factory must generate id_solicitud.

Recommended format:

SOL-YYYYMMDD-HHMMSS-LAST4

Where:

SOL      = fixed prefix for Solicitud
YYYYMMDD = Colombia local date
HHMMSS   = Colombia local time
LAST4    = last four digits of telefono

Example:

SOL-20260526-073022-2233

The visible timestamp must use Colombia time, not server time.

This avoids confusion when the server runs in Germany or another timezone.

The timezone must be:

America/Bogota
11. Timestamp Rules

The model may store timestamps as ISO strings to stay consistent with the current lightweight Pydantic style.

The factory should generate:

created_at
updated_at

Both should be set at creation time.

Recommended timestamp format:

ISO 8601 string

The timestamp should represent the actual creation moment.

For display-oriented request IDs, Colombia local time must be used.

12. Confirmation Protection

At creation time, the factory must always enforce:

fecha_confirmada = None
franja_confirmada = None

Even if the user says something like:

“Confirmo la cita mañana en la tarde.”

The patient cannot self-confirm operational availability.

Human confirmation is required later.

13. Suggested Implementation Shape

Future implementation file:

app/services/appointment_request_factory.py

Suggested function:

def create_appointment_request(
    telefono: str,
    nombre_paciente: str | None = None,
    source_interaction_id: str | None = None,
    intent_origen: str = "cita",
    canal_origen: str = "whatsapp",
    fecha_solicitada: str | None = None,
    franja_solicitada: str | None = None,
    hora_solicitada_texto: str | None = None,
    servicio_solicitado: str | None = None,
    direccion_domicilio: str | None = None,
    observaciones: str | None = None,
) -> AppointmentRequest:
    ...

Suggested helper:

def generate_appointment_request_id(
    telefono: str,
    now: datetime | None = None,
) -> str:
    ...

The optional now parameter is recommended for deterministic tests.

14. Test Expectations

Future test file:

tests/test_appointment_request_factory.py

Required test coverage:

Creates a minimal appointment request with telefono.
Generates id_solicitud with prefix SOL.
Uses Colombia time in id_solicitud.
Includes the last four phone digits in id_solicitud.
Defaults to estado_solicitud = nueva.
Allows optional patient name.
Allows requested date and range.
Does not fill confirmed date or range.
Rejects or avoids confirmed initial state.
Includes servicio_solicitado and direccion_domicilio when provided.
Sets created_at and updated_at.
Does not import or depend on n8n, Google Sheets, Calendar, Telegram, DB, or LLM services.
15. Invalid Factory Behavior

The factory must not:

create confirmed appointments
check real calendar availability
write to Google Sheets
send Telegram notifications
call n8n
persist to database
call OpenAI or any LLM
create therapy session counters
create treatment plans
decide doctor availability
create a new request for every contraoffer
16. Acceptance Criteria

P6-F.9.6 is accepted when:

This specification exists under:
docs/P6-F.9.6_APPOINTMENT_REQUEST_FACTORY.md
The spec defines when a new AppointmentRequest may be created.
The spec defines required and optional creation inputs.
The spec defines id_solicitud generation.
The spec requires Colombia time for visible request IDs.
The spec protects against automatic confirmation.
The spec keeps contraoffers inside the same appointment request.
The spec explicitly excludes:
Google Sheets
Google Calendar
Telegram
n8n
therapy-session tracking
database persistence
LLM calls
No implementation code has been created before this specification.
17. Next Step After Approval

After this spec is reviewed and accepted, the next implementation step may be:

P6-F.9.7 — Implement AppointmentRequest factory

Expected implementation tasks:

Create app/services/appointment_request_factory.py.
Create tests/test_appointment_request_factory.py.
Add deterministic ID generation using Colombia time.
Add factory tests.
Run targeted tests.
Run appointment request model, lifecycle, and factory tests together.
