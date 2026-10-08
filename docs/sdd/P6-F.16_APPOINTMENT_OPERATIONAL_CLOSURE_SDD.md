# P6-F.16 — Cierre operativo de solicitudes de cita

## Estado
Backend y Apps Script implementados en la rama de trabajo. Sin cambios productivos.
Validación local: 187 tests Python y 3 tests JavaScript GREEN.
Pendientes: concurrencia real en PostgreSQL, regresión final y cierre.
Base verificada: main, 868275b.
Rama: feat/p6-f16-cierre-operativo-citas.

## Problema
Checkpoint operativo aportado por el operador:
- PostgreSQL: 16 solicitudes; Sheets: 4 solicitudes.
- Última solicitud: 2026-08-28, hora de Bogotá.
- Ninguna solicitud confirmada.
- 12 números colombianos y 4 números de prueba o extranjeros.
- Sin evidencia de nuevas solicitudes reales después del 28 de agosto.

La discrepancia requiere reconciliación. Su causa todavía no está determinada.

## Objetivo
PostgreSQL → Sheets → decisión explícita de la doctora
→ validación backend → PostgreSQL → resultado en Sheets.

PostgreSQL continúa siendo la fuente de verdad.
HumanReviewService conserva la autoridad sobre las transiciones.

## Implementación existente inspeccionada
- GoogleSheetsHumanReviewWriter hace upsert por id_solicitud.
- Conserva cuatro columnas humanas, pero reescribe la fila completa.
- GoogleSheetsApiClient permite lectura y actualización de rangos concretos.
- POST /internal/human-review/actions exige INTERNAL_ADMIN_TOKEN.
- El endpoint invoca HumanReviewService y actualiza PostgreSQL.
- El endpoint no envía WhatsApp ni proyecta el resultado en Sheets.
- HumanReviewAction no incluye identificador idempotente de decisión.
- propose_alternative puede conservar pendiente_confirmacion.
- El repositorio de citas no dispone de listado para reconciliación.
- No se identificó scheduler en el repositorio.
- El operador confirma que no hay triggers ni tareas automáticas configuradas.
- Despliegue documentado: Easypanel sobre Hetzner; Dockerfile existente.

## Comparación de integración
| Opción | Ventaja | Coste o limitación |
| --- | --- | --- |
| Apps Script llama al endpoint de acciones | Reutiliza la API existente; ejecución desde Sheets | Requiere configurar credencial, contrato de decisiones y devolución del resultado |
| Apps Script dispara procesamiento backend | Reutiliza el cliente de Sheets; concentra procesamiento en Python | Requiere una entrada protegida y desplegar el script |
| Backend lee decisiones periódicamente | Toda la integración queda en Python | Requiere un mecanismo de programación que hoy no existe |
| Ejecución manual backend | Facilita reconciliación y validación inicial | Mantiene dependencia del operador; no completa la autonomía de la doctora |

Decisión final pendiente de definir el contrato y comparar el coste real.
Apps Script es candidato, no una decisión cerrada.
No añadir scheduler, contenedor o servicio adicional sin necesidad demostrada.

## Contrato operativo pendiente
Antes de tests RED deben definirse:
- campos de entrada para las seis acciones;
- propiedad de fecha/franja de decisión, sin confundirlas con la proyección;
- envío explícito de una decisión completa, evitando procesar ediciones parciales;
- identificador estable de decisión y semántica de repetición;
- rechazo de reutilización de identificador con contenido distinto;
- control de concurrencia y estado esperado;
- persistencia atómica de resultado y transición;
- actor, fecha backend, resultado y error seguro;
- columnas de resultado propiedad del sistema;
- recuperación cuando PostgreSQL confirma y Sheets falla;
- identificación de pruebas mediante evidencia explícita:
  un prefijo extranjero no basta para declarar un registro como prueba.

## Reconciliación
- Listar todas las solicitudes existentes, sin eliminar ninguna.
- Validar encabezados e identificadores antes de escribir.
- Crear filas ausentes y actualizar únicamente columnas del sistema.
- No sobrescribir columnas humanas, tampoco ante ediciones concurrentes.
- Detectar duplicados y filas inválidas con resultados seguros.
- Aislar errores por solicitud.
- Repetir la reconciliación sin duplicar filas.
- No procesar decisiones humanas durante una reconciliación de visibilidad.

## Acciones
confirm, request_missing_data, propose_alternative,
reschedule, cancel y close.

Todas deben pasar por HumanReviewService.
No duplicar reglas de transición en Apps Script o Sheets.

## Notificación al paciente
Propuesta de alcance: envío automático fuera de P6-F.16.
El servicio existente produce patient_message, pero el endpoint no lo envía.
La doctora mantiene el contacto manual durante esta fase.
should_notify_patient no constituye evidencia de envío.
Documentar esta limitación en el procedimiento operativo.

## Límites
No modificar:
- P6-F.15 ni la visibilidad de reactivación;
- reactivación por lotes o sus disparadores;
- limpieza de pacientes y solicitudes de prueba;
- flujo clínico, voz, KB o disponibilidad;
- integración Calendar o seguimiento posatención.

No incluir secretos, datos clínicos innecesarios ni mensajes crudos
de excepciones en logs, resultados o documentación.

## Validación
Inspección → contrato → RED → implementación mínima → GREEN
→ regresión → documentación → git diff --check → commit.

Tests con fakes y bases de prueba, sin servicios productivos.
Validar:
- reconciliación de 16 solicitudes, repetida sin duplicados;
- preservación de columnas humanas;
- acción válida aplicada una sola vez;
- repetición y concurrencia sin efectos duplicados;
- acción inválida sin cambio de estado;
- aislamiento por fila;
- recuperación tras fallo de Sheets posterior al commit PostgreSQL;
- actor, fecha y resultados seguros;
- ausencia de envío WhatsApp.

## Cierre
- Integración elegida y justificada.
- Contrato operativo documentado.
- Tests relevantes y regresión GREEN.
- Revisión de diff y git diff --check limpios.
- SDD y sección vigente de AI_CONTEXT.md actualizados antes del commit.
- Evidencia productiva registrada únicamente cuando se haya comprobado.

## Decisión de integración y contrato v1

Esta sección resuelve las opciones y pendientes anteriores.

### Superficie operativa
Apps Script añade un menú para enviar explícitamente la decisión de
la fila seleccionada a POST /internal/human-review/actions.
No usar onEdit ni triggers periódicos.
Apps Script no valida transiciones ni modifica estados de solicitud.
No se añade scheduler, servicio o contenedor.

La reconciliación se ejecuta separadamente desde backend y no procesa
decisiones. El resultado de cada acción se proyecta desde backend.
Una repetición puede recuperar la proyección sin reaplicar la acción.

### Entradas de Sheets
Se conservan las columnas humanas existentes:
accion_doctora, motivo_decision, revisado_por y fecha_revision.

Se añaden entradas humanas:
- fecha_decision: fecha ISO YYYY-MM-DD.
- franja_decision: franja elegida por la doctora.
- datos_faltantes: nombres de campos separados por comas.

Mapeo:
- confirm: fecha_decision y franja_decision a confirmed_date/franja.
- request_missing_data: datos_faltantes a missing_fields.
- propose_alternative y reschedule: fecha_decision y franja_decision
  a alternative_date/franja.
- cancel y close: sin fecha ni franja obligatorias.
- motivo_decision a reason y, para close, a notes.
- revisado_por a actor; obligatorio y no vacío.
- fecha_revision es información humana, no reloj de auditoría.

Para confirm desde Sheets se exige fecha y franja explícitas.
El contrato interno existente de confirm sin fecha permanece compatible.
Los campos adicionales se validan en backend antes de aplicar la acción.

### Idempotencia y concurrencia
Cada envío explícito recibe decision_id UUID, persistido en una columna
técnica antes de efectuar la llamada.
Un retry reutiliza el mismo identificador y contenido.
Una decisión posterior requiere un nuevo identificador explícito.
No regenerar el identificador automáticamente ante timeout.

La llamada incluye expected_updated_at de la proyección PostgreSQL.
El backend compara esa versión dentro de la transacción.
El control por estado solo no basta para propose_alternative.

Una tabla versionada de decisiones conserva:
decision_id, id_solicitud, huella del comando, actor, fecha backend,
estado previo/nuevo, resultado y error seguro.
No guarda patient_message, teléfono, datos clínicos ni payload completo.

Resultado y actualización de solicitud se confirman atómicamente.
La misma decisión devuelve el resultado original sin nueva actualización.
El mismo ID con contenido distinto produce idempotency_conflict.
Una versión obsoleta produce stale_request sin modificar la solicitud.
Las reglas de transición siguen exclusivamente en HumanReviewService.
Las acciones sin decision_id mantienen el contrato interno existente;
Apps Script siempre debe utilizar el contrato idempotente.

### Proyección y propiedad
fecha_confirmada y franja_confirmada son proyección del sistema:
la doctora utiliza fecha_decision y franja_decision como entradas.

Columnas técnicas nuevas:
- decision_id: gestionada por Apps Script para el envío explícito.
- solicitud_updated_at: versión PostgreSQL.
- decision_id_resultado: identifica el resultado proyectado.
- resultado_decision.
- error_decision.
- procesado_por.
- fecha_procesamiento.
- tipo_registro: prueba_confirmada, operativo o sin_clasificar.

El sistema no reescribe columnas humanas ni decision_id al proyectar.
Las escrituras se limitan a rangos de propiedad del sistema.
Antes de escribir se verifica el contrato de encabezados y la unicidad
de id_solicitud; nunca se toma el número de fila como identidad persistente.
Resultados de decisiones anteriores no sobrescriben resultados posteriores.

La clasificación de pruebas usa identificadores confirmados explícitamente.
La reconciliación puede representar las 16 solicitudes sin eliminaciones.

### Fallos y seguridad
Un fallo de Sheets posterior al commit no revierte PostgreSQL.
La respuesta distingue resultado de negocio y estado de proyección.
Retry o reconciliación recuperan la visibilidad.
No hay efectos WhatsApp.

La credencial se configura fuera del código y de las celdas.
El procedimiento debe advertir que los editores del proyecto Apps Script
pueden acceder a sus propiedades; revisar permisos antes de activarlo.
No registrar tokens, comandos completos ni excepciones crudas.
No desplegar Apps Script como web app pública.

### Notificación
Decisión de alcance: envío automático al paciente excluido de P6-F.16.
La doctora contacta manualmente al paciente.
La interfaz muestra expresamente que aplicar una decisión no envía WhatsApp.

### Orden de implementación
1. Reconciliación y escrituras que preservan columnas humanas.
2. Persistencia idempotente y control de versión, con tests.
3. Endpoint y proyección de resultados.
4. Apps Script y procedimiento operativo.
5. Regresión, documentación y revisión final.

La migración se prepara y prueba localmente.
Su aplicación productiva se realiza en la etapa de despliegue,
después de validación y revisión del cambio.

## Roadmap y avance — 2026-10-07

| Bloque | Entregable | Estado |
| --- | --- | --- |
| 1 | Base de reconciliación y protección de columnas humanas | GREEN local |
| 2 | Decisiones persistentes, idempotencia, auditoría y concurrencia | GREEN SQLite; concurrencia PostgreSQL pendiente |
| 3 | Endpoint, proyección de resultados y entrada operativa de reconciliación | Pendiente |
| 4 | Menú Apps Script y procedimiento de la doctora | Pendiente |
| 5 | Regresión final, documentación, revisión y commit | Pendiente |

### Evidencia del bloque 1
- list_all recupera todas las solicitudes en orden estable.
- El writer actualiza A:S y X:Z sin escribir T:W.
- Encabezados reordenados y IDs duplicados se rechazan antes de escribir.
- Reconciliación validada con 4 filas iniciales y 16 solicitudes.
- La repetición conserva 16 filas únicas y los valores humanos.
- Un fallo por solicitud no bloquea las demás.
- Los resultados no exponen detalles crudos de excepciones.
- RED confirmado antes de cada implementación.
- Regresión conjunta: 35 passed, según resultado del operador.

No se ha ejecutado reconciliación productiva.
No hay cambios productivos, migraciones aplicadas ni envíos WhatsApp.
La ampliación de columnas y clasificación explícita de pruebas se integrará
con la proyección del bloque 3.

Los tests pendientes se agruparán por bloque.
No se duplicará la cobertura existente de transiciones de HumanReviewService.

### Evidencia del bloque 2
- El repositorio puede reutilizar una conexión dentro de una transacción.
- HumanReviewDecisionProcessor delega las transiciones a HumanReviewService.
- decision_id se normaliza como UUID y el comando se identifica mediante SHA-256.
- Una repetición devuelve el resultado original sin modificar la solicitud.
- Un ID reutilizado con contenido distinto produce idempotency_conflict.
- La versión updated_at se compara antes de aplicar una decisión nueva.
- Una transición aplicada genera una nueva versión temporal.
- Decisión y actualización se confirman o revierten en la misma transacción.
- No se guarda el comando completo ni patient_message en la auditoría.
- Migración preparada: scripts/sql/010_create_human_review_decisions.sql.
- Tests del procesador y regresión de servicio/repositorio: 35 passed.
- Tests del procesador usando la migración real: 6 passed.
- La importación incorrecta del test se corrigió antes de confirmar RED.

PostgreSQL utiliza advisory lock por decision_id y bloqueo de solicitud
FOR UPDATE. Estos mecanismos todavía no se han probado con concurrencia
real en PostgreSQL; SQLite no constituye evidencia de esa validación.

Sin aplicación de migración productiva, wiring del endpoint ni envíos.

## Revisión de proyección y recuperación

Evidencia local:
- Reconciliación, escritor y proyección: 20 tests GREEN.
- Entrada manual con vista previa por defecto y escritura con --apply.
- git diff --check limpio antes de añadir la entrada manual.
- Sin ejecución productiva.

La revisión de la API detectó dos criterios pendientes:
- Recuperar desde la auditoría el resultado que no pudo escribirse en Sheets.
- Evitar que un reintento antiguo proyecte su resultado sobre un estado posterior.

Contrato de corrección:
- API y reconciliación reutilizan una proyección backend común.
- La proyección lee el estado vigente y la última decisión auditada en PostgreSQL.
- En PostgreSQL bloquea la solicitud durante esa lectura y escritura en Sheets,
  coordinándose con el bloqueo usado por el procesador de decisiones.
- Si no existe una decisión auditada, realiza únicamente la proyección de visibilidad.
- Un fallo de Sheets conserva intactos el estado y la auditoría de PostgreSQL.
- La reconciliación no ejecuta decisiones ni envía WhatsApp.
- La validación de concurrencia real en PostgreSQL sigue pendiente.

## Evidencia del bloque backend

- Regresión de citas, revisión humana y Sheets: 187 tests GREEN.
- API y entrada operativa reutilizan HumanReviewSheetProjector.
- La reconciliación recupera el último resultado auditado sin ejecutar decisiones.
- La proyección relee la solicitud vigente y conserva las columnas humanas.
- Recuperación tras fallo de Sheets validada con SQLite y cliente fake.
- Concurrencia real en PostgreSQL pendiente de validación.
- Apps Script y procedimiento operativo pendientes.
- Sin migraciones, reconciliación ni cambios en producción.
- Sin envío de WhatsApp.

## Contrato Apps Script

- Script vinculado a Sheets, con menú de envío/reintento y preparación de nueva decisión.
- onOpen únicamente añade el menú; no procesa solicitudes.
- Sin onEdit, tareas periódicas ni procesamiento por lotes.
- El envío congela UUID, campos de decisión y expected_updated_at antes del HTTP.
- Los reintentos reutilizan exactamente esa copia, aunque cambien las celdas.
- La copia se conserva en DocumentProperties, sin teléfono, nombre ni notas clínicas.
- Una nueva decisión requiere que Sheets refleje el resultado auditado de la anterior.
- El script escribe únicamente decision_id; PostgreSQL proyecta los resultados.
- URL HTTPS y token se configuran en ScriptProperties, nunca en celdas o Git.
- El script vinculado comparte permisos con la hoja: solo editores de confianza.
- No se muestran respuestas HTTP crudas, excepciones ni credenciales.
- El menú informa que el contacto con el paciente es manual.
- Las reglas de transición permanecen en HumanReviewService.
- solicitud_updated_at debe conservarse como texto ISO completo, sin perder precisión.

Referencias:
- https://developers.google.com/apps-script/reference/properties/properties-service
- https://developers.google.com/apps-script/reference/url-fetch/url-fetch-app
- https://developers.google.com/apps-script/reference/base/ui
- https://developers.google.com/apps-script/guides/bound

## Evidencia Apps Script

- 3 tests JavaScript GREEN: copia inmutable, seis acciones y HTTP seguro.
- Guía: docs/P6-F.16_APPOINTMENT_OPERATIONAL_CLOSURE_RUNBOOK.md.
- Script sin instalación ni autorización productiva todavía.
- Validación real del menú en Google Sheets pendiente.

## Validación PostgreSQL prevista

Contenedor local temporal postgres:16, puerto 15432 ligado a 127.0.0.1.
Base dedicada elvira_p6_f16_test; cada test crea y elimina su propio esquema.
La conexión de tests se construye explícitamente para ese contenedor.
Migraciones reales: 001, 004 y 010.
Comprobaciones: repetición concurrente del UUID, versiones concurrentes
y bloqueo compartido entre proyección y procesamiento.
Activación explícita mediante P6_F16_POSTGRES_TESTS=1.
Resultados todavía pendientes.

## Cierre técnico y hallazgo productivo — 2026-10-08

Las secciones de avance anteriores son checkpoints históricos. Estado vigente:

- Bloques 1–5 implementados y fusionados mediante PR #5.
- Concurrencia real validada en PostgreSQL: 3 escenarios GREEN.
- Suite funcional P6-F.16: 64 tests GREEN.
- Regresión completa: 971 passed, 3 skipped.
- Apps Script: 3 tests JavaScript GREEN.
- Backup productivo y copia de Solicitudes_Cita realizados.
- Migración 010 aplicada y human_review_decisions validada vacía.
- Proyección de Sheets pausada durante la transición.
- El preflight productivo detectó de forma segura un contrato legado de
  24 columnas; no escribió ni modificó filas.
- El hotfix admite exclusivamente los contratos conocidos de 24, 26 y
  37 columnas. El paso 24 → 37 remapea encabezados y filas en una sola
  operación de Sheets y conserva por nombre los campos humanos.
- La reconciliación productiva y la instalación real del menú permanecen
  pendientes hasta desplegar y validar el hotfix.
