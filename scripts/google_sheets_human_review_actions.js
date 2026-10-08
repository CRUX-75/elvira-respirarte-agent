/** P6-F.16: bound Sheets menu. No WhatsApp or transition rules. */

const ELVIRA_COLUMNS_ = (
  'id_solicitud,fecha_registro,telefono,nombre_paciente,fecha_solicitada_texto,' +
  'franja_solicitada,modalidad,estado_solicitud,observaciones_elvira,' +
  'interaction_id_origen,direccion_domicilio,servicio_solicitado,tipo_cita,' +
  'eps,barrio,edad_paciente,notas_clinicas_breves,fecha_confirmada,' +
  'franja_confirmada,accion_doctora,motivo_decision,revisado_por,fecha_revision,' +
  'sync_status,last_sync_at,sync_error,fecha_decision,franja_decision,' +
  'datos_faltantes,decision_id,solicitud_updated_at,decision_id_resultado,' +
  'resultado_decision,error_decision,procesado_por,fecha_procesamiento,tipo_registro'
).split(',');

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Elvira · Citas')
    .addItem('Enviar / reintentar decisión', 'elviraEnviarDecision')
    .addItem('Preparar nueva decisión', 'elviraPrepararNuevaDecision')
    .addToUi();
}

function elviraEnviarDecision() {
  elviraRun_(false);
}

function elviraPrepararNuevaDecision() {
  elviraRun_(true);
}

function elviraText_(value) {
  return value == null ? '' : String(value).trim();
}

function elviraDate_(value) {
  const date = elviraText_(value);
  if (!date) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date.startsWith('0000')) {
    throw new Error('invalid_date');
  }
  const parsed = new Date(date + 'T00:00:00Z');
  if (isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== date) {
    throw new Error('invalid_date');
  }
  return date;
}

function elviraPreparePayload_(row, storedPayload, decisionId) {
  const requestId = elviraText_(row.id_solicitud);
  if (storedPayload) {
    const stored = JSON.parse(storedPayload);
    if (stored.id_solicitud !== requestId) throw new Error('snapshot_mismatch');
    return storedPayload;
  }

  const action = elviraText_(row.accion_doctora);
  const actor = elviraText_(row.revisado_por);
  const version = elviraText_(row.solicitud_updated_at);
  if (!requestId || !action || !actor) throw new Error('missing_identity');
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(version) || isNaN(Date.parse(version))) {
    throw new Error('invalid_version');
  }

  const payload = {
    id_solicitud: requestId,
    action: action,
    actor: actor,
    reason: elviraText_(row.motivo_decision) || null,
    decision_id: decisionId,
    expected_updated_at: version,
  };

  if (action === 'confirm') {
    payload.confirmed_date = elviraDate_(row.fecha_decision);
    payload.confirmed_franja = elviraText_(row.franja_decision);
    if (!payload.confirmed_date || !payload.confirmed_franja) {
      throw new Error('missing_confirmation');
    }
  }
  if (action === 'propose_alternative' || action === 'reschedule') {
    payload.alternative_date = elviraDate_(row.fecha_decision);
    payload.alternative_franja = elviraText_(row.franja_decision) || null;
  }
  if (action === 'request_missing_data') {
    payload.missing_fields = elviraText_(row.datos_faltantes)
      .split(/[,\n]/).map(function (field) { return field.trim(); })
      .filter(function (field) { return field.length > 0; });
  }

  const serialized = JSON.stringify(payload);
  if (serialized.length > 2500) throw new Error('decision_too_long');
  return serialized;
}

function elviraPostDecision_(configuration, payload) {
  try {
    const response = UrlFetchApp.fetch(configuration.url, {
      method: 'post',
      contentType: 'application/json',
      headers: {'X-Internal-Admin-Token': configuration.token},
      payload: payload,
      followRedirects: false,
      muteHttpExceptions: true,
    });
    const code = response.getResponseCode();
    if (code !== 200) {
      return 'Resultado no confirmado (HTTP ' + code +
        '). Reintenta la misma decisión; no prepares otra todavía.';
    }

    const outcome = JSON.parse(response.getContentText());
    if (outcome.decision_id !== JSON.parse(payload).decision_id ||
        !outcome.result || typeof outcome.result.success !== 'boolean' ||
        outcome.patient_notified !== false) {
      throw new Error('invalid_response');
    }

    let message = outcome.result.success ?
      'Decisión aplicada en PostgreSQL.' :
      'Decisión rechazada. Consulta error_decision en la hoja.';
    const status = outcome.projection && outcome.projection.status;
    if (['updated', 'appended', 'skipped_stale_result'].includes(status)) {
      message += ' Resultado actual reflejado en Sheets.';
    } else {
      message += ' Sheets pendiente: reintenta la misma decisión.';
    }
    return message + ' No se envió WhatsApp; el contacto con el paciente es manual.';
  } catch (_) {
    return 'Resultado no confirmado. Reintenta la misma decisión; ' +
      'no prepares otra todavía.';
  }
}

function elviraSelectedRow_(configuration) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getActiveSheet();
  const selection = sheet.getActiveRange();
  const tab = configuration.getProperty('ELVIRA_TAB_NAME') || 'Solicitudes_Cita';
  if (sheet.getName() !== tab || !selection ||
      selection.getNumRows() !== 1 || selection.getRow() < 2) {
    throw new Error('invalid_selection');
  }

  const headers = sheet.getRange(1, 1, 1, ELVIRA_COLUMNS_.length)
    .getDisplayValues()[0];
  if (JSON.stringify(headers) !== JSON.stringify(ELVIRA_COLUMNS_)) {
    throw new Error('invalid_headers');
  }

  const rowNumber = selection.getRow();
  const values = sheet.getRange(rowNumber, 1, 1, ELVIRA_COLUMNS_.length)
    .getValues()[0];
  const row = {};
  ELVIRA_COLUMNS_.forEach(function (column, index) {
    let value = values[index];
    if (value instanceof Date) {
      if (column === 'solicitud_updated_at') throw new Error('invalid_version');
      if (column === 'fecha_decision') {
        value = Utilities.formatDate(
          value, spreadsheet.getSpreadsheetTimeZone(), 'yyyy-MM-dd'
        );
      }
    }
    row[column] = elviraText_(value);
  });

  const ids = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1)
    .getDisplayValues();
  const matches = ids.filter(function (item) {
    return elviraText_(item[0]) === row.id_solicitud;
  });
  if (!row.id_solicitud || matches.length !== 1) {
    throw new Error('invalid_request_id');
  }
  return {sheet: sheet, rowNumber: rowNumber, row: row};
}

function elviraRun_(prepareNew) {
  let lock;
  let locked = false;
  let message;
  try {
    lock = LockService.getDocumentLock();
    if (!lock || !lock.tryLock(5000)) throw new Error('busy');
    locked = true;

    const configuration = PropertiesService.getScriptProperties();
    const selected = elviraSelectedRow_(configuration);
    const properties = PropertiesService.getDocumentProperties();
    if (!properties) throw new Error('missing_document');
    const row = selected.row;
    const key = 'elvira_decision:' + row.id_solicitud;
    const storedPayload = properties.getProperty(key);
    const idCell = selected.sheet.getRange(
      selected.rowNumber, ELVIRA_COLUMNS_.indexOf('decision_id') + 1
    );

    if (prepareNew) {
      if (!storedPayload) {
        if (row.decision_id) throw new Error('missing_snapshot');
        message = 'Fila lista. Completa la decisión y usa Enviar / reintentar.';
      } else {
        const previous = JSON.parse(
          elviraPreparePayload_(row, storedPayload, null)
        );
        if (row.decision_id && row.decision_id !== previous.decision_id) {
          throw new Error('snapshot_mismatch');
        }
        if (row.decision_id_resultado !== previous.decision_id ||
            !['aplicada', 'rechazada'].includes(row.resultado_decision) ||
            !row.fecha_procesamiento) {
          throw new Error('unresolved_decision');
        }
        idCell.setValue('');
        SpreadsheetApp.flush();
        properties.deleteProperty(key);
        message = 'Nueva decisión preparada. Revisa los campos antes de enviarla.';
      }
    } else {
      const url = configuration.getProperty('ELVIRA_ACTION_URL') || '';
      const token = configuration.getProperty('ELVIRA_INTERNAL_ADMIN_TOKEN');
      if (!/^https:\/\/[a-z0-9.-]+(?::\d+)?\/internal\/human-review\/actions$/i.test(url) ||
          !token) {
        throw new Error('missing_configuration');
      }
      if (!storedPayload && row.decision_id) throw new Error('missing_snapshot');

      const payload = elviraPreparePayload_(
        row, storedPayload, storedPayload ? null : Utilities.getUuid()
      );
      const decision = JSON.parse(payload);
      if (row.decision_id && row.decision_id !== decision.decision_id) {
        throw new Error('snapshot_mismatch');
      }
      if (!storedPayload) properties.setProperty(key, payload);
      if (row.decision_id !== decision.decision_id) {
        idCell.setValue(decision.decision_id);
      }
      SpreadsheetApp.flush();
      message = elviraPostDecision_({url: url, token: token}, payload);
    }
  } catch (error) {
    const safeMessages = {
      busy: 'Hay otra operación en curso. Inténtalo nuevamente.',
      invalid_selection: 'Selecciona una sola fila de Solicitudes_Cita.',
      invalid_headers: 'El contrato de columnas no coincide. Contacta al operador.',
      invalid_request_id: 'ID vacío o duplicado. Contacta al operador.',
      missing_identity: 'Completa acción, revisado_por e ID de solicitud.',
      invalid_date: 'Usa una fecha válida con formato YYYY-MM-DD.',
      missing_confirmation: 'Completa fecha_decision y franja_decision.',
      invalid_version: 'La versión debe ser texto ISO completo. Solicita reconciliación.',
      decision_too_long: 'Reduce los campos de decisión; no incluyas datos clínicos.',
      missing_snapshot: 'Falta la copia de la decisión. Contacta al operador.',
      snapshot_mismatch: 'La copia y la fila no coinciden. Contacta al operador.',
      unresolved_decision: 'Reintenta la decisión anterior hasta ver su resultado en Sheets.',
      missing_configuration: 'La conexión no está configurada. Contacta al operador.',
    };
    message = safeMessages[error.message] ||
      'No se pudo completar la operación. Conserva la decisión y contacta al operador.';
  } finally {
    if (locked) lock.releaseLock();
  }
  SpreadsheetApp.getUi().alert(message);
}
