# P6-F.11 — Patient Reactivation via WhatsApp SDD

## 1. Estado

PLANNED / FUNCTIONALLY DEFINED / NOT IMPLEMENTED

## 2. Objetivo

Ejecutar una campaña única de reactivación para los contactos
históricos marcados como atendidos por Respirarte.

El objetivo es presentar de forma general los servicios respiratorios
domiciliarios y permitir que las personas interesadas continúen dentro
del flujo normal de Elvira.

P6-F.11 no es seguimiento clínico ni seguimiento posatención.

## 3. Contexto de negocio

La base suministrada por la Dra. Paola D'Aleman contiene:

- 65 registros;
- 49 registros marcados como atendidos;
- 16 registros marcados como no atendidos;
- ninguna gestión previa registrada por Elvira.

La base histórica no contiene información consistente sobre fecha de
atención y servicio recibido. Por tanto, no debe utilizarse para un
seguimiento posatención contextualizado.

La decisión operativa es realizar un único contacto general para
presentar nuevamente los servicios de Respirarte.

## 4. Separación del seguimiento futuro

El seguimiento posatención pertenecerá a una fase independiente para
pacientes atendidos desde el 1 de agosto de 2026.

La tabla futura deberá incluir como mínimo:

- fecha de atención;
- servicio recibido;
- nombre;
- teléfono;
- autorización;
- fecha prevista de seguimiento;
- estado del seguimiento;
- resultado;
- opt-out;
- escalamiento.

Esta funcionalidad queda fuera del alcance de P6-F.11.

## 5. Alcance

P6-F.11 incluye:

- importación controlada de la base histórica;
- validación y normalización de teléfonos;
- exclusión de contactos no elegibles;
- creación de campaña;
- persistencia por contacto;
- transporte mediante template aprobado;
- seguimiento de estados de entrega;
- clasificación de respuestas;
- opt-out semántico;
- integración con el flujo normal de Elvira;
- escalamiento humano cuando corresponda;
- protección contra duplicados.

## 6. Fuera de alcance

P6-F.11 no incluye:

- seguimiento clínico;
- preguntas sobre evolución;
- recordatorios periódicos;
- campañas recurrentes;
- contacto a registros con `ATENDIDO=NO`;
- multitenancy;
- panel administrativo nuevo;
- modificación del flujo de citas;
- modificación de P6-F.10;
- almacenamiento de conversaciones clínicas completas.

## 7. Criterios de elegibilidad

Un contacto podrá incluirse cuando:

- `ATENDIDO=SI`;
- el teléfono sea válido;
- el teléfono pueda normalizarse a E.164;
- no exista opt-out;
- no exista duplicado dentro de la campaña;
- no esté marcado como caso sensible;
- no tenga una inconformidad previa conocida;
- cumpla las condiciones de autorización definidas por Respirarte.

Motivos mínimos de exclusión:

- `not_attended`
- `invalid_phone`
- `duplicate_phone`
- `existing_opt_out`
- `prior_dissatisfaction`
- `sensitive_case`
- `authorization_not_confirmed`

## 8. Contrato del mensaje inicial

El mensaje debe:

- identificar a Elvira;
- identificar a Respirarte;
- describir de forma general la atención respiratoria domiciliaria;
- invitar a responder para conocer servicios o solicitar atención;
- permitir rechazar futuros mensajes.

El mensaje no debe:

- mencionar diagnósticos;
- mencionar tratamientos anteriores;
- afirmar que el receptor es paciente;
- revelar información clínica;
- crear urgencia artificial;
- fingir que existe una conversación activa;
- insistir ante la falta de respuesta.

La redacción final y el nombre del template se aprobarán antes de la
activación.

## 9. Flujo funcional

Contacto elegible:

`registro idempotente -> template -> accepted -> sent -> delivered -> read`

Después de una respuesta:

- Interés o pregunta sobre servicios:
  flujo normal de Elvira.
- Negativa o rechazo:
  opt-out, `ST_OPTOUT` y confirmación breve.
- Queja con solicitud de solución:
  escalamiento humano.
- Queja más solicitud de no contacto:
  escalamiento humano y opt-out.
- Hostilidad aislada como rechazo:
  opt-out.

## 10. Opt-out semántico

### 10.1 Principio

La intención de rechazo tiene prioridad sobre la forma exacta del
mensaje.

No se exige que el contacto escriba literalmente `NO`.

### 10.2 Categorías detectables

- negativa directa;
- falta de interés;
- solicitud de detener mensajes;
- solicitud de borrar o eliminar el contacto;
- objeción de autorización o privacidad;
- hostilidad;
- insulto usado como rechazo;
- variantes ortográficas y coloquiales;
- lenguaje colombiano;
- mayúsculas y repeticiones;
- emojis hostiles;
- transcripciones de audio equivalentes.

### 10.3 Resultado determinístico

Cuando se confirme la intención:

- `intent=optout`
- `next_action=confirm_optout`
- `nuevo_estado=ST_OPTOUT`
- `opt_out=true`

Respuesta:

`Entendido. No le enviaremos más mensajes de Respirarte.
Que tenga un buen día.`

No se permite:

- discutir;
- responder al insulto;
- preguntar por qué;
- intentar recuperar la venta;
- enviar otro mensaje comercial;
- reintroducir el contacto mediante una carga futura.

### 10.4 Categorías seguras

- `explicit_refusal`
- `stop_contact_request`
- `hostile_rejection`
- `privacy_objection`

No debe copiarse el insulto completo al registro de campaña.

## 11. Diferencia entre queja y rechazo

| Respuesta | Opt-out | Escalamiento |
|---|---:|---:|
| No me interesa | Sí | No |
| No vuelvan a escribirme | Sí | No |
| Insulto aislado como rechazo | Sí | No |
| El servicio fue malo y quiero una solución | No automático | Sí |
| El servicio fue malo, no me escriban más | Sí | Sí |
| Quiero hablar con la doctora | No automático | Sí |

## 12. Persistencia conceptual

### Campaña

- `campaign_id`
- `campaign_type`
- `template_name`
- `template_language`
- `status`
- `created_at`
- `activated_at`
- `completed_at`

### Contacto de campaña

- `id`
- `campaign_id`
- `source_reference`
- `patient_name`
- `phone_e164`
- `eligibility_status`
- `exclusion_reason`
- `dispatch_status`
- `attempt_count`
- `provider_message_id`
- `accepted_at`
- `sent_at`
- `delivered_at`
- `read_at`
- `failed_at`
- `response_classification`
- `opt_out`
- `opt_out_reason`
- `escalation_required`
- `internal_reference`

Restricción natural propuesta:

`UNIQUE (campaign_id, phone_e164)`

## 13. Idempotencia

- Un contacto no puede recibir dos mensajes de la misma campaña.
- Un retry técnico debe reutilizar el registro existente.
- Un nuevo webhook no debe crear otro contacto.
- Una nueva importación no debe crear un duplicado.
- Una importación nunca debe reactivar un opt-out.
- Los callbacks fuera de orden no deben regresar el estado.
- `accepted`, `sent`, `delivered` o `read` bloquean otro envío
  comercial de la misma campaña.

## 14. Integración con Elvira

Después de que el contacto responda, Elvira seguirá usando:

- parser actual de WhatsApp;
- estado persistente del paciente;
- intent router determinístico;
- KB de servicios;
- flujo de solicitud de cita;
- voz cuando el mensaje entrante sea audio;
- reglas existentes de escalamiento;
- estado `ST_OPTOUT`.

P6-F.11 no crea un segundo agente conversacional.

## 15. Seguridad y privacidad

- No exponer la base de contactos en logs.
- No registrar teléfonos completos en mensajes de diagnóstico.
- No incluir información clínica en el template.
- No persistir payloads crudos de Meta.
- No duplicar contenido hostil en la tabla de campaña.
- Respetar opt-out antes de cualquier envío.
- No contactar registros marcados con `ATENDIDO=NO`.
- No liberar la campaña sin validación controlada.

## 16. Activación

Antes de producción deben estar verdes:

- importación sin duplicados;
- normalización de teléfonos;
- exclusión de opt-outs;
- template aprobado;
- persistencia idempotente;
- estados `accepted`, `sent`, `delivered`, `read` y `failed`;
- opt-out explícito;
- opt-out hostil;
- queja sin opt-out;
- queja con opt-out;
- integración con el flujo normal;
- escalamiento humano;
- suite completa;
- prueba controlada.

La campaña permanecerá desactivada durante el diseño y la
implementación inicial.

## 17. Cierre de P6-F.11.1 — Architecture and Source Audit

Estado: **cerrado**.

P6-F.11.1 completó la auditoría de arquitectura y fuente sin implementar
envíos ni modificar el comportamiento productivo de Elvira.

### Fuente y Google Sheets

Se reutiliza el spreadsheet `Respirarte CRM` mediante la pestaña
`Reactivacion_Historica`.

Contrato aprobado:

- `source_reference`
- `nombre`
- `telefono_original`
- `atendido`
- `autorizado_contacto`
- `telefono_e164`
- `revision_doctora`
- `motivo_exclusion`
- `estado_reactivacion`
- `observaciones`

Google Sheets funciona como staging, revisión humana y proyección operativa
resumida. PostgreSQL continúa siendo la fuente de verdad.

Cinco contactos fueron cargados únicamente para validar la estructura. No
se normalizaron teléfonos, no se calculó elegibilidad y no se enviaron
mensajes.

Las sincronizaciones deben preservar las columnas de revisión humana.

Se reutilizará `app/adapters/google_sheets_client.py`. Se creará un adapter
independiente para `Reactivacion_Historica`. No se reutilizará el writer de
`Solicitudes_Cita`.

### Persistencia e idempotencia

Persistencia conceptual independiente:

- `reactivation_campaigns`;
- `reactivation_campaign_contacts`.

Restricción natural:

`UNIQUE (campaign_id, phone_e164)`

No se reutiliza `human_escalation_events`.

`patients.opt_out` debe comprobarse inmediatamente antes de cada envío
mediante una consulta read-only que no cree pacientes.

Una importación, retry técnico, webhook repetido o edición de Google Sheets
no puede generar un segundo mensaje comercial.

### Template de reactivación

Templates existentes auditados:

- `revision_humana`;
- `franja_no_disponible`;
- `cita_confirmada`;
- `franja_atencion_prompt`;
- `solicitud_cita_recibida`;
- `hello_world`.

Ninguno cumple el propósito del primer contacto de reactivación.

Template creado:

- nombre: `reactivacion_respirarte`;
- categoría: `Marketing`;
- idioma: `Spanish (COL)` / `es_CO`;
- header de texto: `Respirarte`;
- parámetro del body `{{1}}`: nombre del contacto;
- footer: ninguno;
- botones: ninguno;
- estado: enviado a revisión de Meta.

La plantilla todavía no está aprobada.

El transporte genérico `send_whatsapp_template_message(...)` es
reutilizable.

### Callbacks de Meta

`WhatsAppPayload.extract_status_updates()` es reutilizable.

El routing actual está acoplado a P6-F.10 porque `/webhook` retorna después
de ejecutar el handler de human escalation.

P6-F.11.2 implementó el router genérico best-effort en
`app/services/whatsapp_status_runtime.py`. El router distribuye copias
aisladas del mismo lote entre:

- human escalation;
- patient reactivation.

El fallo de un dominio no bloquea al otro. El router no conoce tablas,
repositorios ni reglas de lifecycle. Cada dominio actualizará únicamente
su propia persistencia.

El router todavía no está conectado a `/webhook`; el comportamiento
productivo de P6-F.10 permanece intacto.

### Opt-out

El flujo determinístico actual se conserva.

P6-F.11.2 implementó la ampliación semántica mediante pruebas para cubrir:

- rechazo directo;
- falta de interés dentro del contexto de reactivación;
- solicitud de no contacto;
- solicitud de eliminación del número;
- objeciones de privacidad;
- lenguaje coloquial colombiano;
- errores ortográficos y abreviaciones;
- hostilidad e insultos usados como rechazo;
- transcripciones de voz equivalentes.

Los rechazos fuertes se reconocen globalmente. Los rechazos suaves
requieren contexto explícito de reactivación. Una queja no implica
automáticamente opt-out.

### Condición de cierre

P6-F.11.1 queda cerrada porque se definieron:

- fuente;
- pestaña operativa;
- contrato de columnas;
- propiedad de campos;
- autoridad de PostgreSQL;
- persistencia conceptual;
- idempotencia;
- exclusiones;
- integración con Google Sheets;
- transporte reutilizable;
- extensión de callbacks;
- template propio;
- brecha del opt-out semántico;
- campaña desactivada.

No se aplicaron migraciones, no se modificó Easypanel y no se enviaron
mensajes.

## 18. Cierre de P6-F.11.2 — Campaign Domain Contracts and Test-First Foundation

Estado: **cerrado y validado localmente**.

P6-F.11.2 implementó la base de dominio de la campaña sin introducir
persistencia productiva, migraciones aplicadas ni envíos.

### 18.1 Modelos y lifecycle

Archivo:

`app/models/reactivation_campaign.py`

Estados de campaña:

- `draft`
- `ready`
- `active`
- `paused`
- `completed`
- `cancelled`

Estados de contacto:

- `staged`
- `excluded`
- `eligible`
- `pending`
- `accepted`
- `sent`
- `delivered`
- `read`
- `failed`
- `opted_out`

También se definieron:

- estados de autorización;
- estados de revisión de la doctora;
- motivos seguros de exclusión;
- entrada y resultado de elegibilidad.

Las transiciones inválidas son rechazadas de forma explícita.

### 18.2 Normalización, elegibilidad e idempotencia

Archivo:

`app/services/reactivation_domain.py`

Contratos implementados:

- normalización de teléfonos a E.164 compatible con WhatsApp;
- prefijo colombiano únicamente cuando se suministra como país por defecto;
- rechazo de teléfonos ambiguos o inválidos;
- clave estable por campaña y teléfono;
- elegibilidad determinística;
- múltiples motivos seguros de exclusión;
- bloqueo de un nuevo envío después de `accepted`, `sent`, `delivered` o
  `read`;
- bloqueo cuando ya existe `provider_message_id`;
- retry permitido únicamente para fallos retryable anteriores a la
  aceptación;
- reducción monotónica de callbacks;
- callbacks repetidos sin regresión del estado.

La restricción persistente futura continúa siendo:

`UNIQUE (campaign_id, phone_e164)`

### 18.3 Consulta read-only de pacientes

Se añadió:

`find_patient_by_phone_read_only(...)`

La consulta:

- usa únicamente `SELECT`;
- proyecta `id`, `telefono` y `opt_out`;
- no utiliza `get_or_create_patient_by_phone(...)`;
- no crea pacientes;
- no actualiza nombres;
- no modifica estado conversacional;
- no elimina registros.

Este contrato se utilizará inmediatamente antes del claim o envío futuro.

### 18.4 Opt-out semántico

Se implementó una decisión semántica segura con las categorías:

- `explicit_refusal`
- `stop_contact_request`
- `hostile_rejection`
- `privacy_objection`

Reglas:

- rechazos fuertes de contacto o privacidad tienen prioridad global;
- respuestas suaves como `No gracias` y `No me interesa` requieren contexto
  explícito de reactivación;
- errores ortográficos, abreviaciones, repeticiones, emojis y lenguaje
  coloquial están cubiertos;
- las transcripciones de voz usan el mismo contrato;
- una queja que solicita solución requiere escalamiento y no implica
  automáticamente opt-out;
- una queja con solicitud de no contacto produce escalamiento y opt-out;
- la decisión no conserva el mensaje hostil completo.

La máquina de estados existente continúa produciendo:

- `intent=optout`
- `next_action=confirm_optout`
- `nuevo_estado=ST_OPTOUT`
- `opt_out=true`

### 18.5 Router genérico de callbacks

Se añadió:

`app/services/whatsapp_status_runtime.py`

El router:

- recibe el lote ya extraído por `WhatsAppPayload`;
- entrega una copia aislada a cada dominio;
- no filtra ni deduplica callbacks;
- no conoce tablas ni repositorios;
- no altera lifecycle por sí mismo;
- permite que un dominio falle sin bloquear al otro;
- devuelve únicamente métricas y categorías seguras.

El router todavía no está conectado a `/webhook`.

P6-F.10 continúa recibiendo los callbacks productivos mediante su handler
actual.

### 18.6 Evidencia

- pruebas nuevas de P6-F.11.2: **147 passed**;
- regresiones dirigidas de P6-F.10, callbacks, webhook y voz:
  **57 passed**;
- suite completa: **644 passed**;
- compilación Python: aprobada;
- `git diff --check`: aprobado;
- `app/main.py`: sin modificaciones.

### 18.7 Límites conservados

No se realizaron:

- migraciones;
- cambios de Easypanel;
- cambios en Google Sheets;
- importaciones de contactos;
- escrituras en PostgreSQL de campaña;
- conexión del router al webhook;
- envío del template;
- mensajes reales.

La campaña permanece desactivada.

## 19. Próximo sprint

`P6-F.11.3 — Campaign Persistence Schema and Repository Foundation`

Orden:

1. definir esquemas SQL de campaña y contacto;
2. crear migraciones versionadas sin aplicarlas;
3. proteger `UNIQUE (campaign_id, phone_e164)`;
4. implementar repositorios con pruebas first;
5. crear o reutilizar campañas y contactos de forma idempotente;
6. implementar claim atómico de entrega;
7. persistir `provider_message_id`;
8. aplicar estados de Meta de forma monotónica;
9. impedir retries después de aceptación del proveedor;
10. consultar `patients.opt_out` inmediatamente antes del claim o envío;
11. mantener el router desconectado de `/webhook`;
12. no implementar todavía importación, envío ni activación;
13. no modificar Easypanel;
14. no aplicar migraciones sin autorización expresa.

## 20. Decisión vigente

P6-F.11 continúa siendo una campaña única de reactivación histórica.

Solo se incorporarán contactos realmente utilizables y aprobados.

El seguimiento posatención queda reservado para una fase independiente
basada en pacientes atendidos desde el 1 de agosto de 2026.

El template `reactivacion_respirarte` no podrá utilizarse hasta confirmar
formalmente su aprobación en Meta.

## 21. Protocolo de trabajo

- `AI_CONTEXT.md` y el SDD se documentan en una sola ventana;
- no se repiten bloques ni comandos ya ejecutados;
- el trabajo avanza paso a paso;
- la documentación se actualiza después de cada fase;
- se utilizan `grep`, `cat` y `sed` para inspección y validación;
- la campaña permanece desactivada hasta una decisión explícita.

<!-- P6-F.11.3-SDD-CLOSURE:START -->
## P6-F.11.3 — Cierre de persistencia de campañas

**Estado de la fase:** CLOSED
**Fecha de cierre técnico:** 2026-07-29

### Resultado

P6-F.11.3 establece la base persistente e idempotente para campañas
históricas de reactivación de pacientes sin activar todavía el flujo
productivo.

Se implementaron dos agregados persistentes independientes:

1. `reactivation_campaigns`
2. `reactivation_campaign_contacts`

El contacto conserva los contratos definidos en P6-F.11.2:

- teléfono original y teléfono normalizado E.164;
- asistencia;
- autorización;
- revisión médica;
- exclusiones seguras;
- estado de elegibilidad;
- idempotencia;
- estado de entrega Meta;
- reintentos y claims.

### Seguridad transaccional

La adquisición de un contacto para entrega ocurre mediante un
`UPDATE ... WHERE ... RETURNING` atómico.

El claim solo puede prosperar cuando:

- la campaña relacionada está `active`;
- el contacto está `eligible`, o está `failed` y es retryable;
- no existe un `provider_message_id`;
- no existe un claim vigente;
- el paciente no está marcado con `patients.opt_out = TRUE`.

La consulta de opt-out se ejecuta dentro del claim inmediatamente
antes de reservar el contacto.

El repositorio no invoca `get_or_create_patient_by_phone(...)` ni
realiza mutaciones de pacientes.

### Idempotencia y callbacks

La persistencia protege:

- `UNIQUE (campaign_id, phone_e164)`;
- unicidad de `idempotency_key`;
- unicidad parcial de `provider_message_id`.

Los callbacks Meta son repetibles y monotónicos:

- `sent` no puede regresar `delivered` o `read`;
- `delivered` no puede regresar `read`;
- callbacks posteriores válidos pueden recuperar un registro
  `failed`;
- callbacks duplicados no generan un segundo contacto ni un segundo
  envío;
- callbacks desconocidos se ignoran de forma segura;
- un fallo individual no interrumpe el lote completo.

### Estado de integración

El handler
`process_reactivation_status_updates_best_effort(...)` está
implementado, pero continúa desconectado de:

- `app/main.py`;
- `/webhook`;
- `route_whatsapp_status_updates_best_effort(...)`.

La migración
`008_create_reactivation_campaign_persistence.sql` está versionada,
pero no fue aplicada.

### Validación

- Persistencia y callbacks: 42 passed.
- Regresiones dirigidas: 36 passed.
- Suite completa: 686 passed.
- Tiempo de suite completa: 558.93 segundos.
- Compilación: OK.
- Formato del diff: OK.
- Sin cambios en producción, PostgreSQL, Sheets o Easypanel.

### Dependencias externas

El template `reactivacion_respirarte` fue observado aprobado y activo
en Meta el 28 de julio de 2026.

Este estado elimina la espera externa prevista, pero no constituye
autorización para activar la campaña ni enviar mensajes.

### Roadmap restante

- P6-F.11.4 — opt-out semántico y respuestas.
- P6-F.11.5 — dispatcher, transporte y tracking Meta.
- P6-F.11.6 — Google Sheets y dry run sin envío.
- P6-F.11.7 — piloto controlado y cierre productivo.

Estimación restante: 4.5–6.5 sesiones enfocadas, aproximadamente
8–15 horas de trabajo técnico, sujeta a los resultados del dry run y
del piloto.
<!-- P6-F.11.3-SDD-CLOSURE:END -->
