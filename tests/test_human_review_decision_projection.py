from copy import deepcopy

from app.adapters.google_sheets_human_review_writer import (
    GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
    GoogleSheetsHumanReviewWriter,
)
from tests.test_google_sheets_human_review_writer import FakeSheetsClient, make_request


def outcome(decision_id="decision-new", processed_at="2026-10-07T12:00:00+00:00"):
    return {
        "decision_id": decision_id,
        "processed_at": processed_at,
        "actor": "dra_test",
        "replayed": False,
        "result": {
            "success": True,
            "id_solicitud": "SOL-SHEETS-001",
            "action": "confirm",
            "new_status": "confirmada",
            "error_code": None,
        },
    }


def setup_writer():
    headers = GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
    values = dict.fromkeys(headers, "")
    values.update({
        "id_solicitud": "SOL-SHEETS-001",
        "accion_doctora": "confirm",
        "motivo_decision": "Decisión humana",
        "revisado_por": "dra_test",
        "fecha_revision": "2026-10-07",
        "fecha_decision": "2026-10-08",
        "franja_decision": "15:00–17:00",
        "datos_faltantes": "direccion_domicilio",
        "decision_id": "decision-new",
    })
    client = FakeSheetsClient([list(headers), [values[column] for column in headers]])
    writer = GoogleSheetsHumanReviewWriter(
        client=client, spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita", enabled=True,
    )
    return writer, client, values


def test_projects_result_and_version_without_rewriting_human_inputs():
    writer, client, original = setup_writer()
    request = make_request(
        estado_solicitud="confirmada",
        fecha_confirmada="2026-10-08",
        franja_confirmada="15:00–17:00",
        updated_at="2026-10-07T11:59:00+00:00",
    )

    assert writer.project_decision(request, outcome()) == "updated"
    row = dict(zip(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS, client.existing_rows[1]))

    for column in (
        "accion_doctora", "motivo_decision", "revisado_por", "fecha_revision",
        "fecha_decision", "franja_decision", "datos_faltantes", "decision_id",
    ):
        assert row[column] == original[column]

    assert row["estado_solicitud"] == "confirmada"
    assert row["solicitud_updated_at"] == request.updated_at
    assert row["decision_id_resultado"] == "decision-new"
    assert row["resultado_decision"] == "aplicada"
    assert row["error_decision"] == ""
    assert row["procesado_por"] == "dra_test"
    assert row["fecha_procesamiento"] == outcome()["processed_at"]
    assert client.updated_rows == []


def test_old_result_cannot_overwrite_newer_projection():
    writer, client, _ = setup_writer()
    request = make_request(estado_solicitud="confirmada")
    writer.project_decision(request, outcome())
    snapshot = deepcopy(client.existing_rows)
    writes = len(client.range_updates)

    status = writer.project_decision(
        request,
        outcome("decision-old", "2026-10-07T11:00:00+00:00"),
    )

    assert status == "skipped_stale_result"
    assert client.existing_rows == snapshot
    assert len(client.range_updates) == writes
