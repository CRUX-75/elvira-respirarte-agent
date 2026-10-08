const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadScript(fetch) {
  const context = {
    UrlFetchApp: {fetch},
  };
  vm.createContext(context);
  vm.runInContext(
    fs.readFileSync(
      path.join(__dirname, '../scripts/google_sheets_human_review_actions.js'),
      'utf8'
    ),
    context
  );
  return context;
}

function row() {
  return {
    id_solicitud: 'SOL-SCRIPT-001',
    accion_doctora: 'confirm',
    revisado_por: 'dra_test',
    motivo_decision: 'Validación operativa',
    fecha_decision: '2026-10-08',
    franja_decision: 'tarde',
    datos_faltantes: 'direccion_domicilio, eps',
    solicitud_updated_at: '2026-10-07T10:00:00.123456+00:00',
    telefono: 'dato innecesario',
    nombre_paciente: 'dato innecesario',
    notas_clinicas_breves: 'dato innecesario',
  };
}

test('retry preserves UUID, input fields and original version', () => {
  const script = loadScript();
  const original = row();
  const frozen = script.elviraPreparePayload_(
    original, null, '00000000-0000-0000-0000-000000000001'
  );
  const edited = {
    ...original,
    accion_doctora: 'cancel',
    motivo_decision: 'Edición posterior',
    solicitud_updated_at: '2026-10-07T12:00:00+00:00',
  };
  const retry = script.elviraPreparePayload_(
    edited, frozen, '00000000-0000-0000-0000-000000000002'
  );
  assert.equal(retry, frozen);
  assert.equal(JSON.parse(retry).expected_updated_at, original.solicitud_updated_at);
});

test('six actions map decision fields without copying patient data', () => {
  const script = loadScript();
  for (const action of [
    'confirm', 'request_missing_data', 'propose_alternative',
    'reschedule', 'cancel', 'close',
  ]) {
    const payload = JSON.parse(script.elviraPreparePayload_(
      {...row(), accion_doctora: action},
      null,
      '00000000-0000-0000-0000-000000000001'
    ));
    assert.equal(payload.action, action);
    assert.equal(payload.actor, 'dra_test');
    assert.equal(payload.reason, 'Validación operativa');
    assert.equal(payload.telefono, undefined);
    assert.equal(payload.nombre_paciente, undefined);
    assert.equal(payload.notas_clinicas_breves, undefined);
    if (action === 'confirm') {
      assert.equal(payload.confirmed_date, '2026-10-08');
      assert.equal(payload.confirmed_franja, 'tarde');
    }
    if (action === 'reschedule' || action === 'propose_alternative') {
      assert.equal(payload.alternative_date, '2026-10-08');
      assert.equal(payload.alternative_franja, 'tarde');
    }
    if (action === 'request_missing_data') {
      assert.deepEqual(payload.missing_fields, ['direccion_domicilio', 'eps']);
    }
  }
});

test('HTTP failures expose no raw details and preserve the exact payload', () => {
  let captured;
  const script = loadScript((url, options) => {
    captured = {url, options};
    return {
      getResponseCode: () => 500,
      getContentText: () => 'private credential and clinical detail',
    };
  });
  const payload = script.elviraPreparePayload_(
    row(), null, '00000000-0000-0000-0000-000000000001'
  );
  const message = script.elviraPostDecision_({
    url: 'https://example.invalid/internal/human-review/actions',
    token: 'fake-test-token',
  }, payload);

  assert.equal(captured.options.payload, payload);
  assert.equal(captured.options.followRedirects, false);
  assert.equal(captured.options.muteHttpExceptions, true);
  assert.match(message, /500/);
  assert.doesNotMatch(message, /credential|clinical|fake-test-token/);
});
