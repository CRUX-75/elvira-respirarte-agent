# P6-F.9.2 — AppointmentRequest Internal Model

## Status

Draft specification — SDD first pass.

No implementation code must be written before this specification is reviewed and accepted.

---

## 1. Purpose

This document defines the internal Python domain model `AppointmentRequest`.

The model represents a patient appointment request inside the Elvira / Respirarte backend before any external operational export is implemented.

The purpose of this model is to provide a deterministic, auditable, and testable internal contract aligned with:

```text
docs/P6-F.9.1_SOLICITUDES_CITA_OPERATIONAL_CONTRACT.md

This model is the internal source used by backend services to represent appointment requests. It is not a Google Sheets implementation and it is not a calendar automation layer.

2. SDD Rule

This phase follows Specification-Driven Development.

Therefore:

Define the contract first.
Validate field meaning and allowed states.
Define exclusions clearly.
Only after this specification is accepted, create the Python model.
No Google Sheets writer, calendar automation, Telegram notification, n8n workflow, or therapy-session tracking may be implemented in this phase.
3. Contractual Source

The source of truth for the operational appointment-request structure is:

docs/P6-F.9.1_SOLICITUDES_CITA_OPERATIONAL_CONTRACT.md

The internal AppointmentRequest model must remain aligned with the validated Solicitudes_Cita operational contract.

If a future change is needed, the operational contract must be updated first or together with this internal model specification.

4. Scope
In scope

This phase defines:

The internal AppointmentRequest model.
The separation between:
requested appointment data
accepted appointment data
confirmed appointment data
The appointment request lifecycle states.
Required fields for operational visibility.
Fields required by Dra. D’Aleman:
direccion_domicilio
servicio_solicitado
The additional state:
reagendada
Data-level validation expectations.
Future mapping expectations toward Solicitudes_Cita.
Out of scope

The following are explicitly excluded from P6-F.9.2:

Calendar automation.
Google Calendar integration.
Automatic appointment confirmation.
Google Sheets implementation.
Google Sheets append/update logic.
Telegram notifications.
n8n workflows.
n8n state handling.
n8n scheduling logic.
Treatment/session package tracking.
Number of therapy sessions.
Remaining therapy sessions.
Executed therapy sessions.
Therapy plan lifecycle.
Any future Planes_Terapia or Sesiones_Terapia module.

Those topics must not be mixed into AppointmentRequest.

5. Architectural Decision

The appointment request lifecycle belongs to the FastAPI/Python backend.

The core appointment request flow must not depend on n8n.

The backend owns:

State validation.
Appointment request creation.
Appointment request updates.
Appointment request lifecycle transitions.
Internal persistence.
Auditability.
Mapping toward the human-visible operational inbox.

Google Sheets may later be used as a human-visible operational inbox, but not as the authoritative source for appointment request logic.

Telegram and n8n may later be used only as auxiliary notification layers, not as sources of truth.

6. Model Name

The internal model name must be:

AppointmentRequest

The model should live in the backend domain layer.

Suggested future location:

src/core/domain/appointment_request.py

or, if the project already groups domain models in a shared file:

src/core/domain/models.py

The exact file location must be decided during implementation, after checking the existing repo structure.

7. Core Concept

An AppointmentRequest is not the same as a confirmed appointment.

It represents the full lifecycle of a patient asking for an appointment, including negotiation, accepted alternatives, confirmation, cancellation, or rescheduling.

The model must separate three moments clearly:

What the patient originally requested.
What the patient accepted after negotiation.
What the doctor or clinic finally confirmed.

This prevents Elvira from treating a patient preference as a confirmed appointment.

8. Required Separation of Appointment Data
8.1 Requested data

Requested data represents what the patient initially asks for.

Example:

“Mañana en la tarde.”

This may become:

fecha_solicitada = 2026-05-27
franja_solicitada = tarde

Requested data must not be treated as confirmed availability.

8.2 Accepted data

Accepted data represents an alternative or proposed slot accepted by the patient during negotiation.

Example:

“Entonces sí, el jueves en la tarde está bien.”

This may become:

fecha_aceptada = 2026-05-28
franja_aceptada = tarde

Accepted data still does not mean the appointment is confirmed by the doctor.

8.3 Confirmed data

Confirmed data represents the final appointment details confirmed by Dra. D’Aleman or the operational team.

Example:

fecha_confirmada = 2026-05-28
franja_confirmada = tarde

Only confirmed data represents a final operational appointment decision.

9. Required Fields

The internal model must include at least the following fields.

9.1 Identity fields
id_solicitud
telefono
nombre_paciente

Expected meaning:

id_solicitud: unique appointment request identifier.
telefono: patient phone number, normalized when possible.
nombre_paciente: patient name when available.

id_solicitud must be generated by the backend, not by n8n.

The final ID format is not implemented in this phase, but the model must allow storing it.

Recommended future format:

SOL-YYYYMMDD-HHMMSS-LAST4

The timestamp should use Colombia time if visible to clinic staff.

9.2 Request context fields
estado_solicitud
intent_origen
canal_origen
created_at
updated_at

Expected meaning:

estado_solicitud: current lifecycle state of the appointment request.
intent_origen: deterministic intent that triggered the request, for example cita.
canal_origen: source channel, normally whatsapp.
created_at: creation timestamp.
updated_at: last update timestamp.
9.3 Requested appointment fields
fecha_solicitada
franja_solicitada
hora_solicitada_texto

Expected meaning:

fecha_solicitada: date requested by the patient, when resolved.
franja_solicitada: time range requested by the patient, for example mañana, tarde, or another supported slot label.
hora_solicitada_texto: original time expression when the patient provides a non-normalized phrase, for example tipo 3, después de almuerzo, mañana en la tarde.

These fields represent patient preference only.

They must not imply confirmed availability.

9.4 Accepted appointment fields
fecha_aceptada
franja_aceptada

Expected meaning:

fecha_aceptada: date accepted by the patient after an alternative or proposal.
franja_aceptada: time range accepted by the patient after an alternative or proposal.

These fields represent patient acceptance only.

They must not imply final confirmation by Dra. D’Aleman.

9.5 Confirmed appointment fields
fecha_confirmada
franja_confirmada

Expected meaning:

fecha_confirmada: final confirmed appointment date.
franja_confirmada: final confirmed appointment range.

These fields may only be filled once the appointment is operationally confirmed by the doctor or clinic team.

Elvira must not fill these fields based only on patient preference.

9.6 Service and address fields
servicio_solicitado
direccion_domicilio

Expected meaning:

servicio_solicitado: service requested by the patient, for example respiratory therapy, valuation, follow-up, or another service known to the KB.
direccion_domicilio: patient home address or reference point for domiciliary care.

These fields were explicitly requested as visible operational fields by Dra. D’Aleman.

They should be optional during initial request creation, because the patient may not provide them in the first message.

They may be completed progressively.

9.7 Operational notes fields
observaciones
motivo_reagendamiento
motivo_cancelacion

Expected meaning:

observaciones: free operational notes.
motivo_reagendamiento: reason or context for rescheduling, when applicable.
motivo_cancelacion: reason or context for cancellation, when applicable.

These fields support human review and auditability.

9.8 Audit fields
source_interaction_id
created_by
updated_by

Expected meaning:

source_interaction_id: reference to the interaction that created or last materially changed the request.
created_by: actor that created the request, for example system, elvira, or future staff user.
updated_by: actor that last updated the request.

The first implementation may keep these values simple, but the model must allow future auditability.

10. Appointment Request States

The internal model must support the following lifecycle states:

nueva
pendiente_datos
pendiente_confirmacion
confirmada
reagendada
cancelada
cerrada
11. State Definitions
11.1 nueva

The appointment request has been created but may not yet contain all necessary operational information.

Typical trigger:

Patient asks for an appointment.
Backend creates an internal appointment request.
11.2 pendiente_datos

The request exists, but required information is still missing.

Examples of missing information:

requested date
requested time range
service requested
home address or address reference point

This state is useful when the patient has shown appointment intent but the system still needs more information.

11.3 pendiente_confirmacion

The request contains enough information for Dra. D’Aleman or the operational team to review.

This does not mean the appointment is confirmed.

Typical meaning:

Patient has requested or accepted a possible date/range.
Elvira has collected enough information.
The request is ready for human review.
11.4 confirmada

The appointment has been confirmed by Dra. D’Aleman or the operational team.

Only this state may be treated as confirmed.

11.5 reagendada

The request was previously confirmed, accepted, or pending, but the date/range was changed through a rescheduling process.

This state was explicitly requested by Dra. D’Aleman.

Rescheduling must remain part of the same appointment request when it refers to the same original request.

A contraoffer or renegotiation should not create a new appointment request by default.

11.6 cancelada

The request was cancelled.

Cancellation may happen because:

The patient cancels.
The clinic cancels.
The patient no longer wants the service.
The request becomes invalid.
11.7 cerrada

The request lifecycle is closed.

This may happen after:

The appointment was handled.
The operational team no longer needs the request active.
A cancelled request has been archived.
A completed operational handoff has been finalized.

This state does not imply therapy-session tracking.

12. Allowed State Transition Expectations

The implementation must define transitions conservatively.

Expected high-level transitions:

nueva -> pendiente_datos
nueva -> pendiente_confirmacion
pendiente_datos -> pendiente_confirmacion
pendiente_confirmacion -> confirmada
pendiente_confirmacion -> cancelada
confirmada -> reagendada
confirmada -> cancelada
reagendada -> pendiente_confirmacion
reagendada -> confirmada
reagendada -> cancelada
cancelada -> cerrada
confirmada -> cerrada

The implementation must avoid uncontrolled arbitrary transitions.

A future service should validate transitions explicitly.

13. Validation Expectations

The internal model should support validation rules compatible with Pydantic or dataclass-based validation.

Expected validation principles:

telefono should be present.
estado_solicitud must be one of the allowed states.
Confirmed fields must not be filled casually by Elvira.
fecha_confirmada and franja_confirmada should only be filled when the state is confirmada or when there is explicit human confirmation.
fecha_aceptada and franja_aceptada may exist while the state is still pendiente_confirmacion.
direccion_domicilio and servicio_solicitado may be empty initially.
Rescheduling should preserve the same request identity when it belongs to the same original appointment request.
The model must not create therapy session counters or treatment package fields.
14. Non-Confirmation Rule

The model must protect this core rule:

Patient requested data is not the same as confirmed appointment data.

Therefore:

fecha_solicitada != fecha_confirmada
franja_solicitada != franja_confirmada

unless explicitly confirmed by the doctor or clinic team.

Likewise:

fecha_aceptada != fecha_confirmada
franja_aceptada != franja_confirmada

unless explicitly confirmed by the doctor or clinic team.

15. Future Mapping to Solicitudes_Cita

The internal model should later map cleanly to the operational Solicitudes_Cita table or sheet.

Expected future mapping:

AppointmentRequest.id_solicitud          -> Solicitudes_Cita.id_solicitud
AppointmentRequest.telefono              -> Solicitudes_Cita.telefono
AppointmentRequest.nombre_paciente       -> Solicitudes_Cita.nombre_paciente
AppointmentRequest.estado_solicitud      -> Solicitudes_Cita.estado_solicitud
AppointmentRequest.fecha_solicitada      -> Solicitudes_Cita.fecha_solicitada
AppointmentRequest.franja_solicitada     -> Solicitudes_Cita.franja_solicitada
AppointmentRequest.fecha_aceptada        -> Solicitudes_Cita.fecha_aceptada
AppointmentRequest.franja_aceptada       -> Solicitudes_Cita.franja_aceptada
AppointmentRequest.fecha_confirmada      -> Solicitudes_Cita.fecha_confirmada
AppointmentRequest.franja_confirmada     -> Solicitudes_Cita.franja_confirmada
AppointmentRequest.servicio_solicitado   -> Solicitudes_Cita.servicio_solicitado
AppointmentRequest.direccion_domicilio   -> Solicitudes_Cita.direccion_domicilio
AppointmentRequest.observaciones         -> Solicitudes_Cita.observaciones

The actual Google Sheets writer is not part of this phase.

16. Example Lifecycle
Example A — Simple request

Patient says:

Buenas, quiero pedir una cita.

Expected internal result:

estado_solicitud = nueva or pendiente_datos
telefono = patient phone
canal_origen = whatsapp

No confirmed date or range exists.

Example B — Patient requests a range

Patient says:

Mañana en la tarde.

Expected internal result:

fecha_solicitada = resolved Colombia date
franja_solicitada = tarde
estado_solicitud = pendiente_datos or pendiente_confirmacion

No confirmed date or range exists.

Example C — Patient accepts an alternative

Elvira offers a possible alternative and the patient says:

Sí, el jueves en la tarde me sirve.

Expected internal result:

fecha_aceptada = resolved Colombia date
franja_aceptada = tarde
estado_solicitud = pendiente_confirmacion

No confirmed date or range exists.

Example D — Doctor confirms

Dra. D’Aleman confirms operationally:

Jueves en la tarde confirmado.

Expected internal result:

fecha_confirmada = confirmed date
franja_confirmada = tarde
estado_solicitud = confirmada
Example E — Appointment is rescheduled

The same appointment request changes to another date/range.

Expected internal result:

estado_solicitud = reagendada
motivo_reagendamiento = optional reason/context

The same id_solicitud should be preserved unless a human explicitly decides to create a new request.

17. Explicit Anti-Patterns

The implementation must not do the following:

Do not create a new request every time the patient accepts an alternative.
Do not treat requested date as confirmed date.
Do not treat accepted date as confirmed date.
Do not let Elvira confirm real availability.
Do not use n8n as the source of appointment request state.
Do not use Google Sheets as the source of business logic.
Do not implement calendar automation in this phase.
Do not implement Telegram notifications in this phase.
Do not add therapy session counters to AppointmentRequest.
Do not add treatment plan tracking to AppointmentRequest.
18. Acceptance Criteria

P6-F.9.2 is accepted when:

This specification exists under:
docs/P6-F.9.2_APPOINTMENT_REQUEST_INTERNAL_MODEL.md
The spec clearly separates:
requested
accepted
confirmed
The spec includes:
direccion_domicilio
servicio_solicitado
The spec includes the state:
reagendada
The spec explicitly excludes:
calendar automation
Google Sheets implementation
Telegram
n8n
therapy-session tracking
No implementation code has been created before this specification.
19. Next Step After Approval

After this spec is reviewed and accepted, the next implementation step may be:

P6-F.9.3 — Create AppointmentRequest domain model

Expected implementation tasks for the next phase:

Inspect existing domain model structure.
Decide final model location.
Create AppointmentRequestStatus.
Create AppointmentRequest.
Add minimal unit tests for field separation and state validity.
Do not implement Google Sheets integration yet.

