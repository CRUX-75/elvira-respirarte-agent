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

<!-- P6-F.11.4-SDD-CLOSURE:START -->
## 22. Cierre de P6-F.11.4 — Opt-out y manejo de respuestas

**Estado de la fase:** CLOSED
**Fecha de cierre técnico:** 2026-07-30

### 22.1 Resultado

P6-F.11.4 establece el contrato determinístico, persistente e
idempotente para procesar respuestas a una campaña histórica de
reactivación.

La fase no conecta todavía este procesamiento al webhook productivo.

### 22.2 Clasificaciones de respuesta

El dominio distingue:

| Clasificación | Opt-out global | Opt-out de campaña | Escalamiento |
| --- | --- | --- | --- |
| `global_opt_out` | sí | sí | solo cuando también existe queja |
| `campaign_refusal` | no | sí | no |
| `positive_contact_request` | no | no | sí |
| `complaint` | no | no | sí |
| `ambiguous` | no | no | no |

La precedencia determinística es:

1. solicitud fuerte de no contacto;
2. rechazo limitado a la campaña;
3. queja;
4. interés o solicitud de contacto;
5. respuesta ambigua.

Una queja combinada con una solicitud fuerte de no contacto conserva
ambas decisiones: escalamiento y opt-out.

### 22.3 Contrato persistente

La migración versionada
`009_add_reactivation_response_persistence.sql` añade un resumen seguro
al contacto y crea `reactivation_campaign_response_events`.

El resumen del contacto conserva:

- último identificador entrante aplicable;
- última clasificación aplicable;
- último motivo seguro;
- necesidad de escalamiento;
- fecha de la última respuesta aplicable.

La tabla de eventos conserva todas las decisiones técnicas necesarias
para auditoría e idempotencia.

Quedan excluidos explícitamente:

- texto bruto del mensaje;
- transcripción completa;
- audio;
- payload Meta;
- historial conversacional.

La migración está versionada y no aplicada.

### 22.4 Correlación e idempotencia

La respuesta se correlaciona con el contacto de campaña más reciente
del mismo teléfono E.164 que ya tenga entrega aceptada por Meta.

La escritura utiliza una transacción atómica con:

- inserción idempotente del evento;
- resumen seguro del contacto;
- unicidad de `inbound_whatsapp_message_id`;
- recuperación del evento original ante duplicados;
- validación adicional de `contact_id`.

Un identificador entrante perteneciente a otro contacto no puede
devolver un evento ajeno.

### 22.5 Respuestas fuera de orden

Todo mensaje nuevo válido puede registrarse como evento.

El resumen del contacto únicamente avanza cuando:

`received_at >= responded_at`

Por tanto:

- una respuesta antigua no sustituye una clasificación más reciente;
- una respuesta antigua no elimina una necesidad de escalamiento más
  reciente;
- una respuesta antigua no modifica `responded_at`;
- el opt-out de campaña permanece monotónico;
- el contacto `opted_out` continúa disponible para correlacionar
  respuestas repetidas o posteriores.

### 22.6 Runtime best-effort

`process_reactivation_response_best_effort(...)` coordina:

1. correlación;
2. clasificación;
3. persistencia;
4. opt-out global opcional;
5. escalamiento opcional.

Los efectos laterales se ejecutan de forma independiente.

Un fallo en el opt-out global no impide intentar el escalamiento, y un
fallo de escalamiento no expone información sensible en el resultado.

El resumen del runtime no contiene el mensaje recibido.

### 22.7 Adaptadores

`persist_reactivation_global_opt_out(...)`:

- utiliza una consulta read-only;
- no crea pacientes;
- actualiza únicamente un paciente existente;
- persiste `ST_OPTOUT`;
- persiste `opt_out=True`.

`persist_reactivation_escalation(...)`:

- reutiliza `HumanEscalationEventService`;
- conserva idempotencia por mensaje entrante y acción;
- usa eventos minimizados;
- no conserva IDs internos de campaña;
- no conserva texto bruto.

Acciones nuevas aprobadas:

- `escalate_reactivation_interest`;
- `escalate_reactivation_complaint`.

### 22.8 Estado de integración

Continúan sin wiring productivo:

- `app/services/reactivation_response_runtime.py`;
- `app/services/reactivation_response_adapters.py`;
- `app/main.py`;
- `/webhook`.

No se aplicaron migraciones, no se activó la campaña y no se enviaron
mensajes.

### 22.9 Validación

- Contratos de P6-F.11.4: 40 passed.
- Regresión semántica: 45 passed.
- Regresión funcional amplia: 83 passed.
- Regresión de servicios, persistencia y callbacks: 54 passed.
- Suite completa: aprobada, exit status 0.
- Compilación: OK.
- Formato del diff: OK.
- Wiring productivo: ausente.
- PostgreSQL productivo, Sheets y Easypanel: sin cambios.

### 22.10 Roadmap restante

- P6-F.11.5 — dispatcher, transporte y tracking Meta.
- P6-F.11.6 — Google Sheets y dry run sin envío.
- P6-F.11.7 — piloto controlado y cierre productivo.

La aprobación previa del template `reactivacion_respirarte` no autoriza
su envío ni la activación de la campaña.
<!-- P6-F.11.4-SDD-CLOSURE:END -->

<!-- P6-F.11.5-SDD-CLOSURE-2026-07-31 -->

## P6-F.11.5 — Template Dispatcher and Meta Delivery Tracking

**Status:** Closed on 2026-07-31.

### Design goal

Provide a production-independent dispatcher for the approved historical
reactivation template while preserving campaign eligibility, opt-out,
idempotency and delivery-state rules already implemented in P6-F.11.1–11.4.

### Approved template contract

| Field | Required value |
|---|---|
| Template name | `reactivacion_respirarte` |
| Language | `es_CO` |
| Meta category | Marketing |
| Header | Text: `Respirarte` |
| BODY parameters | Exactly one: contact name |
| Footer | None |
| Buttons | None |

The contract is validated independently by the dispatcher and the transport
adapter. Any different template, language, empty parameter or additional
parameter is rejected before the generic WhatsApp transport is invoked.

### Components

#### `ReactivationTemplateDispatcher`

Responsibilities:

1. Remain disabled unless explicitly configured with `enabled=True`.
2. Normalize the dispatch request and require one contact identifier.
3. Acquire an atomic delivery claim through
   `ReactivationCampaignContactService`.
4. Stop when the contact is ineligible, already claimed or already committed.
5. Require canonical persisted E.164 data and a non-empty contact name.
6. Invoke an injected template sender using the approved immutable contract.
7. Extract the provider WAMID from the safe transport result.
8. Persist `accepted` with the same claim token and WAMID.
9. Convert transport exceptions into safe retry classifications.
10. Prevent automatic retry when Meta may already have accepted the message.

The dispatcher has no direct database, HTTP, webhook or production
configuration dependency.

#### `ReactivationTemplateDispatchRequest`

Immutable request object containing a normalized, non-empty contact ID.
The dispatcher remains backward compatible with direct `contact_id` calls but
rejects receiving both forms simultaneously.

#### `ReactivationTemplateTransport`

A thin adapter translates the dispatcher argument `to` into the generic
transport argument `telefono`. It performs no contact selection, campaign
activation, persistence or lifecycle decision.

The module also provides a pure payload builder for inspection and tests. The
builder performs no HTTP operation.

#### `dispatch_reactivation_contacts_best_effort`

Processes explicit contact IDs sequentially and isolates exceptions per
contact. One runtime failure cannot stop later contacts. Returned batch data
contains only safe outcomes and counters.

### Persistence and idempotency

A provider call is possible only after an atomic repository claim. Acceptance
requires all of the following:

- matching contact ID;
- matching claim token;
- current status `pending`;
- no persisted `provider_message_id`.

Failure persistence uses equivalent claim guards and also requires no WAMID.

When Meta returns a WAMID but acceptance persistence raises an exception or
returns a conflict, the dispatcher:

1. reports `delivery_outcome_ambiguous`;
2. marks the result non-retryable;
3. retains the WAMID in the safe result;
4. attempts a terminal non-retryable failure using the original claim.

If `accepted` actually committed despite the ambiguous response, repository
guards prevent the terminal failure from overwriting it.

### Provider tracking

The existing status runtime correlates callbacks by WAMID and supports:

- `sent`;
- `delivered`;
- `read`;
- `failed`.

State reduction is monotonic. Duplicate, unknown, malformed and out-of-order
callbacks are isolated and do not interrupt the callback batch. Failed
callbacks persist only sanitized provider error categories.

### Safety boundaries

P6-F.11.5 does not:

- activate a campaign;
- import or select real campaign contacts;
- send a real Meta template;
- modify `app/main.py`;
- modify product configuration or Easypanel variables;
- apply migrations 008 or 009;
- write to production PostgreSQL;
- modify Google Sheets;
- implement the pilot;
- implement P6-F.11.6 or P6-F.11.7.

### Verification

| Verification layer | Result |
|---|---:|
| P6-F.11.5 contract tests | 17 passed |
| Directed regressions | 165 passed |
| Full suite | 743 passed |
| Global compilation | Passed |
| Git diff check | Passed |
| Productive wiring | Absent |
| Unexpected working-tree files | None |

### Next phase

P6-F.11.6 remains pending and must start from the closed P6-F.11.5 baseline.

<!-- P6-F.11.6-SDD-CLOSURE-2026-08-09 -->

## P6-F.11.6 — Google Sheets and No-Send Dry Run

**Status:** Closed on 2026-08-09.

### Design goal

Provide a production-independent dry-run path for
`Reactivacion_Historica` that evaluates historical contacts using the
existing domain contracts while preserving the separation between
Google Sheets staging, PostgreSQL authority and Meta delivery.

### Google Sheets contract

The dedicated adapter uses the exact approved ten-column contract:

1. `source_reference`
2. `nombre`
3. `telefono_original`
4. `atendido`
5. `autorizado_contacto`
6. `telefono_e164`
7. `revision_doctora`
8. `motivo_exclusion`
9. `estado_reactivacion`
10. `observaciones`

The adapter fails closed when the header order differs from the
canonical contract.

The dry-run projection writes only:

- column F — `telefono_e164`;
- column I — `estado_reactivacion`.

It does not rewrite A:J and therefore does not overwrite source-owned
or human-review fields from a stale row snapshot.

### Dry-run evaluation

`evaluate_reactivation_sheet_record(...)` is a pure deterministic
boundary.

It:

- recomputes E.164 from `telefono_original`;
- validates controlled Sheet values;
- delegates eligibility to the reactivation domain;
- returns safe exclusion reasons;
- performs no database, Sheets, Meta or WhatsApp I/O.

### Read-only safety context

`ReactivationDryRunContextResolver` combines:

- canonical phone normalization;
- duplicate detection inside the current batch;
- read-only patient opt-out lookup;
- read-only campaign-contact lookup;
- committed commercial-send protection.

The campaign-contact repository exposes
`get_by_campaign_phone_read_only(...)`, which uses a SELECT through
`engine.connect()` and performs no writes.

Persisted contact states fail closed when delivery must not be
re-attempted:

- `pending`;
- `opted_out`;
- `failed` with `retryable=False`.

A contact in:

`failed + retryable=True + provider_message_id=None`

remains eligible for the retry path already defined by the delivery
claim contract.

Any persisted WAMID or committed commercial send remains blocking.

### Best-effort runtime

`run_reactivation_dry_run_best_effort(...)`:

1. reads staging rows through the dedicated adapter;
2. resolves external safety context per row;
3. evaluates eligibility;
4. projects only system-owned fields;
5. isolates row failures;
6. returns safe aggregate counters.

Raw exception text is not returned in public batch results.

### Configuration boundary

New configuration:

- `reactivation_dry_run_enabled: bool = False`;
- `google_sheets_reactivation_tab: str =
  "Reactivacion_Historica"`.

The reactivation dry run does not inherit enablement from the generic
`google_sheets_enabled` flag used by appointment review.

The dependency factory returns no reactivation composition while
`reactivation_dry_run_enabled=False`.

Building enabled dependencies constructs objects only. It does not
read Google Sheets, query PostgreSQL or execute the dry run.

### Safety boundaries

P6-F.11.6 does not:

- activate a reactivation campaign;
- select or import production contacts;
- persist dry-run decisions as campaign contacts;
- acquire delivery claims;
- invoke the P6-F.11.5 dispatcher;
- send a Meta template;
- modify `app/main.py`;
- modify `/webhook`;
- apply migrations 008 or 009;
- modify Easypanel;
- write production PostgreSQL;
- execute the pilot.

No real Google Sheets I/O was required to close the phase.

### Verification

| Verification layer | Result |
|---|---:|
| P6-F.11.6 tests | 42 passed |
| Directed expanded regression | 169 passed |
| Full repository suite | 790 passed |
| Full-suite duration | 563.38 s |
| Python compilation | Passed |
| Git diff check | Passed |
| Integrated dry run | Passed with fakes |
| Real WhatsApp sends | None |
| Productive wiring | Absent |

### Remaining roadmap

Only one P6-F.11 phase remains:

`P6-F.11.7 — Controlled pilot and productive closure`

P6-F.11.7 must require explicit authorization before any productive
migration application, campaign activation, real-contact processing
or WhatsApp delivery.

<!-- P6-F.11.6-SDD-CLOSURE-2026-08-09:END -->

<!-- P6-F.11.7-A-CLOSURE-2026-08-10 -->

## P6-F.11.7-A — Preproduction audit closure

**Closed:** 10-Aug-2026
**Branch:** `feature/p6-f-11-7-controlled-pilot-productive-closure`
**Baseline:** `main@5acc857`.

### Audit conclusions

The productive reactivation path remains intentionally disconnected.

The audit confirmed:

- migrations `008` and `009` are not applied in production;
- no historical reactivation message has been sent;
- `app/main.py` still routes productive Meta status callbacks only through
  the existing P6-F.10 human-escalation handler;
- the shared WhatsApp status router is already implemented but not connected
  productively to patient reactivation;
- inbound reactivation response processing is correlation-based and
  best-effort, but productive conversation-routing policy still requires
  explicit tests before webhook wiring;
- the real Sheets dry-run primitives exist, but there is no productive
  administrative execution surface;
- the template dispatcher remains disabled and has no productive composition.

### Migration contract defect found and corrected locally

Migration `008` defines:

`reactivation_campaign_contacts.id TEXT`

Migration `009` incorrectly defined:

`reactivation_campaign_response_events.contact_id UUID`

The Python domain/repository/service contract uses string contact IDs
throughout, therefore the FK types were incompatible.

A RED contract test reproduced the defect.

Migration `009` was corrected to:

`contact_id TEXT NOT NULL REFERENCES reactivation_campaign_contacts(id)`

The correction is versioned source only. No production migration has been
executed.

### Validation evidence

- response-event contract: **5 passed**;
- directed persistence/response regression: **22 passed**;
- complete reactivation test set: **276 passed**;
- shared/P6-F.10 callback regression: **15 passed**;
- affected Python compilation: OK;
- `git diff --check`: OK.

### Production gate

Applying migrations remains a separate P6-F.11.7-B operation requiring
explicit authorization.

Required order when authorized:

1. verify/backup PostgreSQL production state;
2. apply migration `008`;
3. validate resulting campaign/contact schema;
4. apply corrected migration `009`;
5. validate FK, indexes and response-event schema;
6. perform read-only operational verification;
7. confirm normal Elvira and P6-F.10 remain healthy.

Migration authorization does not authorize campaign activation, Google Sheets
dry-run execution, dispatcher activation, webhook wiring or any real
reactivation send.

<!-- P6-F.11.7-B-CLOSURE-2026-08-10 -->

## P6-F.11.7-B — Productive persistence closure

**Closed:** 10-Aug-2026
**Branch:** `feature/p6-f-11-7-controlled-pilot-productive-closure`

### Production persistence installation

The productive PostgreSQL schema was audited read-only before any DDL.

Initial state:

- `reactivation_campaigns`: absent;
- `reactivation_campaign_contacts`: absent;
- `reactivation_campaign_response_events`: absent;
- no partial P6-F.11 foreign keys or indexes.

A pre-migration custom-format PostgreSQL backup was successfully created and
validated with `pg_restore -l`.

Backup:

`/tmp/elvira_respirarte_prod_pre_p6f117_20260810T065009Z.dump`

SHA-256:

`6bffba6a7514b53032928add66050bf230f2b4eb72fec58f669e5e8891ad3b6b`

### Migration 008

Migration 008 was applied only after explicit production authorization.

SHA-256:

`6d46446c74bc665f8fc983a8070a3dd95d1428c3a1548ea89ec3c7fcc49b2097`

Post-008 validation confirmed:

- campaigns table present;
- contacts table present;
- response-events table still absent;
- campaign FK correct;
- expected indexes present.

### Migration 009

The deployed application image still contained the historical defective 009
with `contact_id UUID`.

That file was not executed.

A temporary corrected copy was prepared with only:

`contact_id UUID` -> `contact_id TEXT`

Its SHA-256 matched the corrected source validated in Git:

`6ae91ac71b48fd02641185953a3beacdf62a2f5b61e1c467f70691008b2edab2`

Migration 009 was applied only after a second explicit production
authorization.

Post-009 validation confirmed:

- response-events table present;
- `contact_id TEXT NOT NULL`;
- FK to `reactivation_campaign_contacts.id`;
- expected response-event indexes;
- safe response metadata columns on campaign contacts;
- `POST_009_SCHEMA=OK`.

### Post-migration state

Read-only counts:

- campaigns: 0;
- contacts: 0;
- response events: 0.

No campaign or contact was created as part of persistence installation.

Production health after both migrations:

- `/health`: HTTP 200;
- `/ready`: HTTP 200;
- no ready-state hard failures;
- database and existing repositories configured;
- existing production Elvira remains online.

P6-F.11 remains operationally inert:

- no reactivation campaign activation;
- no real historical reactivation send;
- no productive dispatcher composition;
- no productive reactivation status routing;
- no productive inbound reactivation response wiring.

P6-F.11.7-C may now execute a controlled real Google Sheets dry run while
preserving the no-send boundary.


<!-- P6-F.11.7-C-CLOSURE-2026-08-13 -->

## P6-F.11.7-C — Controlled real dry run closure

**Closed:** 13-Aug-2026
**Branch:** `feature/p6-f-11-7-controlled-pilot-productive-closure`
**Implementation checkpoint:** `28a55db`

### Implemented administrative boundary

A minimal administrative entrypoint was added:

`scripts/manual_reactivation_dry_run.py`

The entrypoint:

- requires exact `REACTIVATION_DRY_RUN_ENABLED=1`;
- requires an explicit dry-run campaign id;
- composes the existing dry-run factory;
- executes the existing best-effort runtime;
- emits aggregate safe output only;
- imports neither Meta dispatcher nor WhatsApp transport;
- fails closed on ambiguous configuration and unexpected runtime failure.

During integration validation, the productive repository contract exposed a
keyword-only boundary:

`get_by_campaign_phone_read_only(*, campaign_id, phone_e164)`

`ReactivationDryRunContextResolver` was aligned with that contract by using
named arguments.

Final directed regression before productive execution:

- 51 tests passed;
- compile checks passed;
- `git diff --check` passed.

### External configuration preflight

The first local external smoke failed before any Sheets or PostgreSQL access
because the local `GOOGLE_SERVICE_ACCOUNT_JSON` value contained one redundant
outer double-quote layer.

Safe structural validation confirmed that removing only that redundant layer
yielded a valid Google service-account document with all required fields.

The defect was corrected in local configuration rather than application code.

Local PostgreSQL access was not possible because the configured productive
database hostname `elvira_elvira` is internal to the deployment network.

### Controlled deployment

Production normally deploys from `main`.

For P6-F.11.7-C only, and after explicit authorization, Easypanel was
temporarily pointed to:

`feature/p6-f-11-7-controlled-pilot-productive-closure`

The deployed image contained checkpoint `28a55db` functionality.

Pre-execution validation confirmed:

- administrative entrypoint present;
- keyword-only repository compatibility fix present;
- compile check successful;
- disabled entrypoint returns rc=2;
- `/health`: HTTP 200;
- `/ready`: HTTP 200;
- productive PostgreSQL hostname resolvable from the application container.

### Productive read-only smoke

Before allowing any Sheets projection, a real external smoke was executed
without invoking the dry-run runtime.

Observed path:

Google Sheets `Reactivacion_Historica`
→ read A:J through the existing adapter
→ PostgreSQL read-only safety context

Observed results:

- 5 sheet rows read;
- 5 contexts resolved;
- 0 context-resolution failures;
- 0 duplicate-in-campaign;
- 0 patient opt-out;
- 0 already-processed;
- 0 prior complaint;
- 0 sensitive case;
- 0 representative number.

PostgreSQL counts before and after remained identical:

- campaigns: 0;
- contacts: 0;
- response events: 0.

No runtime, projection or WhatsApp operation was invoked during this smoke.

### Controlled real dry run execution

The real administrative entrypoint was executed once with explicit process
enablement, a non-persisted technical campaign id and Colombian default
country code `57`.

Safe aggregate result:

- total: 5;
- eligible: 0;
- excluded: 5;
- invalid input: 0;
- runtime error: 0;
- entrypoint rc: 0.

Productive PostgreSQL counts remained unchanged:

- campaigns: 0;
- contacts: 0;
- response events: 0.

No WhatsApp operation was invoked.

### Sheets projection verification

A subsequent read-only verification confirmed:

- 5 rows present;
- `telefono_e164` projected for all 5 rows;
- `estado_reactivacion = excluded` for all 5 rows.

The verification did not invoke the runtime or any additional Sheets write.

The productive dry-run write boundary remained the existing adapter contract:

- column F: `telefono_e164`;
- column I: `estado_reactivacion`;
- no human/source columns modified by the dry-run projection path.

### Production rollback

After the real dry run, Easypanel was explicitly restored from the temporary
feature branch to:

`main`

A successful `main` deployment followed.

Post-rollback verification confirmed:

- the temporary administrative entrypoint is absent from the current `main`
  image;
- `/health`: HTTP 200;
- `/ready`: HTTP 200;
- productive PostgreSQL DNS remains resolvable;
- normal production remains online.

Checkpoint `28a55db` remains on the feature branch and was not merged into
`main` as part of P6-F.11.7-C.

### Closure decision

P6-F.11.7-C is CLOSED.

The real environment has demonstrated:

Google Sheets
→ PostgreSQL read-only context
→ deterministic eligibility
→ safe F/I projection

with:

- zero PostgreSQL writes;
- zero campaign/contact creation;
- zero Meta dispatcher invocation;
- zero WhatsApp transport invocation;
- zero real reactivation messages;
- no `app/main.py` productive wiring.

The next roadmap step is:

P6-F.11.7-D — Minimal pilot preparation.

C does not authorize campaign activation, productive wiring, real sending,
automatic mass selection or the real pilot.
