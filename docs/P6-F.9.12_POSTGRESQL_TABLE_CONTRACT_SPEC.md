# P6-F.9.12.6 — AppointmentRequest PostgreSQL Table Contract SPEC

## Status

Draft / SPEC.

## Purpose

Define the PostgreSQL table contract for persisting `AppointmentRequest` records before implementing the real repository.

This block is specification-only.

No PostgreSQL repository implementation is allowed in this block.

## Architecture boundary

The PostgreSQL table stores appointment request data.

It does not own:

- lifecycle decisions
- duplicate prevention decisions
- appointment availability
- doctor confirmation
- WhatsApp sending
- Telegram notification
- Google Sheets formatting
- n8n workflow logic

The service layer remains responsible for orchestration.

The repository layer remains responsible for persistence and retrieval.

## Official table name

```text
appointment_requests
Primary key
id_solicitud

Type:

TEXT PRIMARY KEY

Reason:

id_solicitud is the visible operational appointment request ID and must remain stable during contraoffers, rescheduling, and lifecycle transitions.

Required columns
id_solicitud TEXT PRIMARY KEY
telefono TEXT NOT NULL
estado_solicitud TEXT NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
created_by TEXT NOT NULL
Optional columns
nombre_paciente TEXT
intent_origen TEXT
canal_origen TEXT
fecha_solicitada TEXT
franja_solicitada TEXT
hora_solicitada_texto TEXT
fecha_aceptada TEXT
franja_aceptada TEXT
fecha_confirmada TEXT
franja_confirmada TEXT
servicio_solicitado TEXT
direccion_domicilio TEXT
observaciones TEXT
source_interaction_id TEXT
updated_by TEXT
Valid lifecycle states

The database must store only states supported by the AppointmentRequest model:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada
Active states

For active lookup by phone:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
Terminal states

Terminal states:

cancelada
cerrada

Terminal requests must not block creation of a new appointment request for the same patient.

Recommended check constraint

The table should enforce valid states at the database level:

estado_solicitud IN (
  'nueva',
  'pendiente_datos',
  'pendiente_confirmacion',
  'confirmada',
  'reagendada',
  'cancelada',
  'cerrada'
)
Required indexes
Phone lookup index
CREATE INDEX idx_appointment_requests_telefono
ON appointment_requests (telefono);
Active lookup index
CREATE INDEX idx_appointment_requests_active_lookup
ON appointment_requests (telefono, estado_solicitud, updated_at DESC, created_at DESC, id_solicitud DESC);

Purpose:

Support deterministic lookup for:

find_active_by_telefono(telefono)
Active lookup ordering

When multiple active requests exist for the same phone number, the repository must return the latest active request using this deterministic order:

updated_at DESC
created_at DESC
id_solicitud DESC

This protects the system from legacy data or manual inconsistencies without making service behavior ambiguous.

Timestamp semantics
created_at

Creation timestamp of the appointment request.

Must not change after creation.

updated_at

Last persistence update timestamp.

Must be updated when the request lifecycle or operational fields change.

Timezone

Use TIMESTAMPTZ.

Application-level timestamps may be generated with Colombia context where needed, but persistence must remain timezone-aware.

Model to database mapping

AppointmentRequest fields map directly to table columns.

The repository must persist and restore the same model field names:

id_solicitud
telefono
nombre_paciente
estado_solicitud
intent_origen
canal_origen
fecha_solicitada
franja_solicitada
hora_solicitada_texto
fecha_aceptada
franja_aceptada
fecha_confirmada
franja_confirmada
servicio_solicitado
direccion_domicilio
observaciones
source_interaction_id
created_by
updated_by
created_at
updated_at
Database row to model mapping

The repository must convert a database row back into an AppointmentRequest.

No business rules should be applied during mapping.

Invalid data should fail loudly through model validation instead of being silently corrected.

Repository behavior required by this table

The future PostgreSQL repository must support:

save(request)
update(request)
get_by_id(id_solicitud)
find_active_by_telefono(telefono)
Save semantics

save(request) must:

insert a new row
preserve id_solicitud
return the persisted AppointmentRequest
fail if the same id_solicitud already exists
Update semantics

update(request) must:

update by id_solicitud
preserve id_solicitud
return the updated AppointmentRequest
not create duplicate rows
fail if id_solicitud does not exist
get_by_id semantics

get_by_id(id_solicitud) must:

return AppointmentRequest when found
return None when not found
find_active_by_telefono semantics

find_active_by_telefono(telefono) must:

search only active states
ignore terminal states
return the latest active request
return None when no active request exists
Explicitly out of scope

This SPEC does not implement:

SQL migration file
repository class
SQLAlchemy model
raw SQL adapter
Google Sheets adapter
Telegram notification
Calendar integration
n8n workflow
WhatsApp sending changes
appointment availability logic
automatic appointment confirmation
Next recommended block

P6-F.9.12.7 — PostgreSQL Repository Tests RED

Objective:

Create tests for the future PostgreSQL repository behavior before implementing the repository.

The tests should initially fail because the repository implementation does not exist yet.
