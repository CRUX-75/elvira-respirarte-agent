# P6-F.10 — Human Escalation via WhatsApp

## Document status

- Status: Draft
- Implementation: Not started
- Target channel: WhatsApp
- Human reviewer: Dr. Paola D'Aleman

This is a deliberately short design document. Technical decisions that depend on the existing repository must be completed after the initial architecture audit.

## 1. Objective

Implement reliable human escalation from Elvira to the WhatsApp number of Dr. Paola D'Aleman.

The feature must transform an existing deterministic escalation decision into a safe operational notification without changing the clinical state machine.

Target flow:

```text
Patient message
    -> deterministic processing
    -> escalation_required=true
    -> escalation event
    -> WhatsApp notification to the doctor
    -> pending / sent / failed status
2. Current capability

Elvira already produces:

escalation_required
next_action
state_reason
patient identity and telephone
current and next conversation state
matched service information when available
deterministic patient response

Elvira does not yet send the escalation to the doctor.

3. In scope

Initial implementation includes:

detecting a completed escalation decision;
constructing a minimal and safe human-review notification;
obtaining the doctor's WhatsApp number from secure configuration;
sending the message through the existing WhatsApp integration;
idempotency;
delivery status;
safe retry;
privacy-safe observability;
controlled production validation.
4. Out of scope

This sprint does not include:

multitenant support;
a clinical dashboard;
patient follow-up after treatment;
appointment confirmation by the doctor;
bidirectional doctor commands;
forwarding raw voice notes;
forwarding complete transcripts;
changes to approved clinical policy;
P7 channel resilience.
5. Initial escalation triggers

At minimum:

escalate_dynamic_oximetry_missing_order
escalate_dynamic_oximetry_long_oxygen_support
tracheostomy specialist assessment
special clinical condition
clinically insufficient information
other existing actions where escalation_required=true

The architecture audit must determine whether the dispatcher should use:

escalation_required;
an allowlist of next_action values;
or both.

Default design preference:

Require escalation_required=true and an approved escalation action.

This prevents unrelated state transitions from generating operational notifications.

6. Notification content

The doctor should receive only the minimum information required to review the case:

patient name;
patient telephone;
requested service;
escalation reason;
brief safe summary;
medical order status when relevant;
relevant duration or clinical condition;
conversation state;
event date and time;
internal reference identifier when available.

The message must not include:

raw audio;
full voice transcription;
full conversation history;
credentials;
internal stack traces;
unnecessary medical details.

Example structure:

Escalamiento de Elvira

Paciente: <name>
Teléfono: <telephone>
Servicio: <service>
Motivo: <reason>
Dato relevante: <minimal clinical fact>
Estado: <conversation state>
Referencia: <event reference>

Requiere revisión humana.

The final wording must be concise and suitable for WhatsApp.

7. Configuration

The doctor's number must come from a secure environment variable.

Proposed name:

HUMAN_ESCALATION_WHATSAPP_NUMBER

A feature flag may be added if the architecture audit confirms it is useful:

HUMAN_ESCALATION_ENABLED

Rules:

never hardcode the number;
never log the complete number;
validate and normalize the number at startup or dispatch time;
do not reuse VOICE_ALLOWED_PHONE_NUMBERS;
do not commit real production values to .env.example.

.env.example may contain an empty placeholder only.

8. Delivery behavior

The escalation notification must not block the patient response.

Preferred order:

Complete deterministic patient processing.
Persist or register the escalation event.
Deliver the patient response.
Attempt the doctor's WhatsApp notification.
Record the result.

If the existing request lifecycle requires another order, the audit must document why.

A failure to notify the doctor must not:

change the patient's clinical result;
change the deterministic state;
expose internal failure details to the patient;
cause the inbound WhatsApp message to be processed twice.
9. Idempotency

A single escalation event must generate at most one successful notification.

The idempotency key should be derived from stable existing identifiers, preferably:

inbound WhatsApp message ID + escalation action

Fallback candidates, only if necessary:

patient telephone + conversation event ID + escalation action

Do not use timestamps alone.

Repeated delivery attempts may occur only while the event is not already marked sent.

10. Persistence

Required logical states:

pending
sent
failed

Recommended metadata:

event identifier;
idempotency key;
patient reference;
inbound WhatsApp message reference;
escalation action;
safe reason code;
status;
attempt count;
created timestamp;
last-attempt timestamp;
sent timestamp;
safe error category.

The architecture audit must first determine whether an existing table or repository can store these fields.

A new PostgreSQL migration is allowed only when:

no suitable existing persistence exists;
the requirement is documented;
tests cover the repository and migration;
no manual production database editing is required.

Google Sheets must not be used as the source of truth for delivery state.

11. Retry policy

Retries must be:

bounded;
idempotent;
safe after process restarts;
restricted to events not marked sent.

Errors should be classified into categories such as:

configuration error;
provider or network error;
invalid destination;
permanent Meta rejection;
unknown safe error.

Do not persist raw provider responses containing sensitive information.

The exact retry mechanism will be selected after auditing existing background jobs, request processing and persistence.

12. Privacy and logging

Logs may contain:

event reference;
safe action code;
delivery status;
attempt number;
latency;
safe error category.

Logs must not contain:

full patient message;
full clinical summary;
raw audio;
full transcript;
complete patient telephone;
doctor's complete telephone;
access tokens;
provider payloads containing personal data.

Existing voice privacy rules remain active.

13. Text and voice consistency

The escalation dispatcher must run after the shared deterministic core.

It must not depend on whether the inbound patient message was text or audio.

Voice-specific components must not independently create escalation notifications.

14. Failure handling

If notification delivery fails:

the patient response remains valid;
the event becomes failed or remains retryable according to policy;
no duplicate successful notification is created;
the operational failure is observable through privacy-safe metadata;
the patient is not told that the doctor has already received or reviewed the case.
15. Architecture audit checklist

Before implementation, inspect once:

Where escalation_required and escalation next_action values are produced.
Where inbound WhatsApp message IDs are available.
Where the patient response is delivered.
Existing WhatsApp text-send functions.
Existing repositories and persistence suitable for idempotency.
Existing retry or lease mechanisms.
Existing observability and log-sanitization utilities.
Existing configuration validation patterns.
Whether escalation can occur before or after patient persistence.
Existing tests for duplicate inbound messages.

The audit should produce a small implementation plan, not another large roadmap.

16. Acceptance criteria

P6-F.10 is complete when:

an approved escalation action creates one event;
the doctor's number comes from secure configuration;
the doctor receives the expected WhatsApp notification;
duplicate processing does not create duplicate successful notifications;
delivery status is persisted or reliably recorded;
a failed attempt can be retried safely;
notification failure does not block the patient response;
text and voice produce the same escalation event;
logs do not expose raw patient content or complete phone numbers;
targeted tests pass;
the full suite passes;
a controlled real WhatsApp test is approved.
17. Open decisions after audit
Reuse an existing table or create a dedicated escalation table.
Synchronous attempt versus persisted worker or outbox.
Exact retry cadence and maximum attempts.
Exact safe message summary source.
Exact action allowlist.
Whether the first release needs a feature flag.
Operational handling when the doctor's number is not configured.

<!-- BEGIN P6-F.10.2 REPOSITORY CONTRACT -->

## 14. Repository and delivery-claim contract

P6-F.10.2 introduces a dedicated PostgreSQL repository with:

- idempotent `create_or_get`;
- atomic delivery claims;
- expiring delivery leases;
- monotonic attempt counting;
- claim-token protection for final updates;
- `sent` and `failed` recording;
- retryable-event retrieval.

An event already marked `sent` cannot be claimed again.

A delivery worker can update an event only with the active claim token.
This prevents an expired or superseded attempt from overwriting the result of
a newer delivery attempt.

The repository receives its database engine through dependency injection.
Runtime database wiring and webhook integration remain outside this phase.

The migration remains unapplied until repository and dispatcher validation are
complete.

<!-- END P6-F.10.2 REPOSITORY CONTRACT -->

<!-- BEGIN P6-F.10.4 RUNTIME WIRING -->

## 16. Local runtime wiring

P6-F.10.4 connects the dispatcher to the existing asynchronous WhatsApp
transport and PostgreSQL engine.

The runtime call occurs only after:

1. patient response delivery has completed;
2. the interaction has been persisted;
3. patient state has been updated;
4. the inbound message has been marked processed.

The runtime receives no raw audio, full transcript, inbound message text,
provider payload or conversation history.

The delivery claim temporarily sets `retryable=false`. A handled transient
transport failure may explicitly restore `retryable=true`.

This design intentionally favors at-most-once doctor notification when the
external delivery outcome is ambiguous. If Meta accepts a message but the
application cannot persist `sent`, automatic delivery is not retried.

The feature remains disabled by default. Migration 006 must be applied before
enabling it in production.

<!-- END P6-F.10.4 RUNTIME WIRING -->

## Cierre productivo — P6-F.10.5

### Motivo del ajuste

El primer envío utilizaba texto libre. La respuesta inicial de Meta
incluía un `wamid`, pero esto solo demostraba aceptación de la
solicitud y no entrega al dispositivo. El evento se almacenaba
prematuramente como `sent`.

### Solución final

El transporte de escalamiento utiliza la plantilla aprobada:

- Nombre: `revision_humana`
- Idioma Cloud API: `es_CO`
- Tipo de mensaje: `template`
- Parámetros de cuerpo: diez valores en orden determinístico

La respuesta síncrona de Meta se registra como `accepted`. Los
webhooks posteriores actualizan el evento a `sent`, `delivered`,
`read` o `failed`.

### Reglas de actualización

- La correlación se realiza por `provider_message_id`.
- Los callbacks desconocidos se ignoran de forma segura.
- Los estados no retroceden ante callbacks tardíos o fuera de orden.
- Los errores se reducen a categorías seguras.
- No se persiste el payload crudo de Meta.
- La entrega continúa siendo best-effort y no bloqueante para el
  paciente.

### Base de datos

La migración 007:

- amplió la restricción de estados;
- añadió `template_parameters`;
- añadió `accepted_at`;
- añadió `delivered_at`;
- añadió `read_at`;
- creó un índice sobre `provider_message_id`.

Las migraciones 006 y 007 fueron aplicadas y verificadas en la base
de datos productiva.

### Evidencia de aceptación

- Suite completa: `497 passed`.
- Commit: `7c8baf1`.
- Plantilla activa en WhatsApp Manager.
- Prueba real con escalamiento por oximetría dinámica sin orden.
- Transiciones observadas:
  `accepted -> sent -> delivered`.
- La destinataria confirmó personalmente la recepción en WhatsApp.
- No se observó duplicación ni error de entrega.

### Resultado

P6-F.10 Human Escalation via WhatsApp queda aceptada, operativa y
cerrada en producción.
