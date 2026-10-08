# P6-F.16 — Procedimiento operativo de solicitudes de cita

## Estado

Preparación técnica. Sin activación ni reconciliación productiva comprobadas.
PostgreSQL es la fuente de verdad. Esta fase no envía WhatsApp.

## Preparación del operador

1. Completar validaciones, revisión, commit y proceso habitual de publicación.
2. Obtener respaldo de PostgreSQL y copia de la pestaña Solicitudes_Cita.
3. Aplicar la migración revisada scripts/sql/010_create_human_review_decisions.sql
   antes de usar el nuevo circuito de decisiones o reconciliación con auditoría.
4. Coordinar el despliegue y la ampliación de encabezados:
   producción puede usar el contrato legado de 24 columnas o el intermedio
   de 26; el contrato nuevo tiene 37. Pausar la proyección de Sheets durante
   esa transición. Cualquier otro orden de encabezados se rechaza.
5. Conservar solicitud_updated_at como texto sin formato, con el ISO completo.
   Mantener las columnas y sus posiciones; no ordenar filas durante escrituras.
6. Ejecutar primero la vista previa del script de reconciliación.
   Si la proyección está pausada en el servicio, habilitarla únicamente en el
   proceso del script mediante GOOGLE_SHEETS_ENABLED=true.
7. Revisar total, present, missing, duplicate_request_ids y contract.
   La vista previa no amplía encabezados ni escribe filas.
8. Ejecutar con --apply. El contrato de 26 columnas amplía AA1:AK1.
   El contrato legado exacto de 24 columnas se remapea a 37 en una sola
   operación, preservando por nombre los campos humanos, y después se
   reconcilian las filas. Revisar failed y errors; repetir para comprobar
   ausencia de duplicados.
9. Usar --test-request-id únicamente para IDs verificados como pruebas.
   Un teléfono extranjero permanece sin_clasificar si no existe evidencia.
10. Restaurar la proyección del servicio cuando el contrato esté preparado.

Entrada: scripts/manual_appointment_request_reconciliation.py.
Opciones: --apply y --test-request-id repetible.
No elimina solicitudes, no procesa decisiones y no envía WhatsApp.
El total productivo debe verificarse al ejecutar; 16 es el checkpoint inicial.

## Instalación del menú

- Abrir la hoja mediante Extensiones → Apps Script.
- Incorporar scripts/google_sheets_human_review_actions.js como archivo .gs.
- Revisar primero si ya existe onOpen; integrar el menú sin reemplazar otros menús.
- Configurar en las propiedades del script:
  - ELVIRA_ACTION_URL: URL HTTPS exacta de /internal/human-review/actions.
  - ELVIRA_INTERNAL_ADMIN_TOKEN: configurar directamente, nunca copiar al chat.
  - ELVIRA_TAB_NAME: opcional; por defecto Solicitudes_Cita.
- El script vinculado comparte permisos con la hoja: permitir solo editores
  de confianza. ScriptProperties no aísla el token frente a esos editores.
- Autorizar los permisos necesarios y volver a abrir la hoja.
- No instalar onEdit, triggers periódicos ni un despliegue web público.
- Proteger los encabezados y columnas del sistema frente a ediciones accidentales.

## Campos que completa la doctora

Siempre: accion_doctora y revisado_por.
motivo_decision contiene únicamente una explicación operativa cuando corresponda.
fecha_revision sigue siendo una columna humana; la fecha backend es fecha_procesamiento.

| Acción | Entrada de decisión |
| --- | --- |
| confirm | fecha_decision y franja_decision |
| request_missing_data | datos_faltantes: nombres de campos separados por comas |
| propose_alternative | fecha_decision y franja_decision para la alternativa |
| reschedule | fecha_decision y franja_decision para la nueva propuesta |
| cancel | motivo_decision cuando corresponda |
| close | motivo_decision cuando corresponda |

Formato de fecha: YYYY-MM-DD.
No escribir la decisión en fecha_confirmada o franja_confirmada:
esas columnas son una proyección de PostgreSQL.
HumanReviewService valida la acción y la transición.

## Enviar y reintentar

1. Completar los campos y seleccionar una sola fila.
2. Elegir Elvira · Citas → Enviar / reintentar decisión.
3. Revisar resultado_decision, error_decision, procesado_por y fecha_procesamiento.
4. Contactar al paciente manualmente según el resultado.

El primer envío guarda una copia de la decisión y su UUID antes del HTTP.
Los reintentos reutilizan exactamente esa copia, incluso si se editan las celdas
o cambia solicitud_updated_at. Las ediciones posteriores no alteran ese envío.

Ante timeout, HTTP fallido o proyección pendiente, reintentar la misma decisión.
No borrar decision_id ni generar otra decisión para resolver un resultado incierto.
Si Sheets sigue fallando, el operador puede recuperar la proyección con reconciliación.

Para otra decisión, esperar a que la hoja refleje el resultado auditado de la
anterior y elegir Preparar nueva decisión. Este paso conserva los campos humanos:
revisarlos y modificarlos antes de enviar.

Si falta la copia persistente o no coincide con la fila, contactar al operador.
No reconstruir automáticamente un comando incierto.

## Comprobación y recuperación

- Resultado aplicada: la decisión quedó registrada en PostgreSQL.
- Resultado rechazada: consultar el error seguro; no modificó el estado.
- Reintento: no aplica nuevamente la transición.
- Fallo de Sheets: conserva estado y auditoría; reintentar o reconciliar.
- Filas duplicadas o inválidas: revisar errores; no impiden tratar otras solicitudes.
- Una reconciliación recupera el estado vigente y la última decisión auditada.
- No se eliminan registros de prueba ni se altera la reactivación.
- Registrar evidencia productiva solo después de comprobarla.
