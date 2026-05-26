# P6-F.9.1 — Solicitudes_Cita Operational Contract

## Status

Closed as business-validated design.

This document defines the operational contract for the `Solicitudes_Cita` human review inbox used by Elvira / Respirarte.

The goal of this phase is not to automate final appointment scheduling, but to convert a clear WhatsApp appointment request into a structured request for Dra. D’Aleman to review.

---

## Core architectural decision

The appointment request flow does not depend on n8n.

Core logic remains in FastAPI / Python:

```text
WhatsApp
↓
FastAPI / Python
↓
State Machine
↓
AppointmentRequestService
↓
Google Sheets: Solicitudes_Cita
n8n must not control:

state transitions
date validation
appointment request creation
duplicate prevention
appointment request persistence rules
business decisions

Google Sheets is the human-visible operational inbox.

Telegram and/or n8n may be used later only for auxiliary notifications, not for core appointment logic.

What Solicitudes_Cita represents

Solicitudes_Cita is not a calendar and does not confirm appointments automatically.

It represents a structured appointment request that is ready for human review.

Elvira’s role:

collect minimum valid appointment request data
→ create structured request
→ leave final decision to Dra. D’Aleman
Creation rule

A request is created only when all required conditions are met:

fecha_solicitada válida
+ franja_aceptada válida
+ transition to ST_CITA_PENDIENTE
+ no equivalent pending duplicate

Equivalent duplicate means:

telefono
+ fecha_solicitada
+ franja_aceptada
+ estado_solicitud = pendiente_revision

A request must not be created when the patient only says they want an appointment, or when only the date is known, or when only a vague preference exists.

Required fields for creation

Required:

telefono
fecha_solicitada
franja_aceptada
transition to ST_CITA_PENDIENTE

Optional if already available:

direccion_domicilio
servicio_solicitado

The request must not be blocked if address or requested service are still empty.

Google Sheets tab

Sheet name:

Solicitudes_Cita

Final columns:

id_solicitud
fecha_registro
telefono
nombre_paciente
fecha_solicitada
fecha_solicitada_texto
preferencia_original
franja_aceptada
modalidad
estado_solicitud
observaciones_elvira
estado_origen
interaction_id_origen
direccion_domicilio
servicio_solicitado
fecha_confirmada
franja_confirmada
Request ID format

Request IDs use Colombia time, not server time.

Format:

SOL-YYYYMMDD-HHMMSS-ULTIMOS4

Timezone:

America/Bogota

Example:

SOL-20260526-073022-0163
Official estado_solicitud values
pendiente_revision
aprobada
rechazada
reagendada
cancelada
confirmada

Meanings:

Estado	Meaning
pendiente_revision	Elvira created the request; Dra. D’Aleman has not reviewed it yet.
aprobada	The requested date/time window is acceptable, but the patient still needs to be contacted.
rechazada	The requested date/time window is not available, but an alternative may be offered.
reagendada	The request changed to another date/time window within the same request.
cancelada	The request is closed without an appointment.
confirmada	The appointment was finally agreed with the patient.
Contraoffer / rescheduling rule

Dra. D’Aleman validated that contraoffers and rescheduling should remain inside the same appointment request.

Therefore:

rechazada → contraoffer → same Solicitudes_Cita row → reagendada or confirmada

A contraoffer does not create a new row.

The original request remains visible through:

fecha_solicitada
franja_aceptada

The final agreed result is stored in:

fecha_confirmada
franja_confirmada
Doctor validation

Dra. D’Aleman validated:

The flow reflects how she wants to manage appointment requests.
The state distinction is correct.
She normally offers alternatives when a requested slot is unavailable.
Contraoffers/rescheduling should stay in the same request.
She wants the additional state reagendada.
She needs direccion_domicilio and servicio_solicitado visible in the request table.
No additional modifications requested for now.

Doctor feedback:

“Me parece una herramienta práctica, versátil y confiable, que se adapta fácilmente a nuestras necesidades, facilitando nuestros procesos, ofreciendo soluciones ágiles, eficientes y optimizando nuestros tiempos de respuesta y ejecución en la prestación de nuestros servicios. Satisfecha con los avances obtenidos a la fecha.”

Out of scope for this phase

The following must not be mixed into Solicitudes_Cita:

calendar automation
automatic appointment confirmation
treatment/session package tracking
number of therapy sessions
remaining therapy sessions
executed sessions tracking

The therapy/session tracking request belongs to a future separate module, likely:

Planes_Terapia
Sesiones_Terapia
Next phase

Next phase:

P6-F.9.2 — AppointmentRequest internal model

Goal:

Create the internal domain model / DTO for appointment requests before implementing persistence.

