from copy import deepcopy

from app.adapters.google_sheets_human_review_writer import (
    GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
    GoogleSheetsHumanReviewWriter,
)
from app.models.appointment_request import AppointmentRequest
from app.services.appointment_request_reconciliation import (
    reconcile_appointment_requests,
)


class FakeRepository:
    def __init__(self, count=16):
        self.requests = [
            AppointmentRequest(
                id_solicitud=f"SOL-RECON-{index:02d}",
                telefono="493001112233" if index < 4 else "573001112233",
                estado_solicitud="pendiente_confirmacion",
            )
            for index in range(count)
        ]

    def list_all(self):
        return deepcopy(self.requests)


class StatefulSheetsClient:
    def __init__(self, requests):
        headers = list(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS)
        self.rows = [headers]
        for request in requests:
            row = [""] * len(headers)
            row[0] = request.id_solicitud
            row[headers.index("accion_doctora")] = "confirm"
            row[headers.index("revisado_por")] = "dra_test"
            self.rows.append(row)

    def get_values(self, spreadsheet_id, range_name):
        return deepcopy(self.rows)

    def append_row(self, spreadsheet_id, range_name, row):
        self.rows.append(list(row))

    def update_values(self, spreadsheet_id, range_name, values):
        cells = range_name.split("!", 1)[1]
        first = cells.split(":")[0]
        row_number = int("".join(char for char in first if char.isdigit()))
        def column_index(cell):
            result = 0
            for char in cell:
                if char.isalpha():
                    result = result * 26 + ord(char) - ord("A") + 1
            return result - 1

        last = cells.split(":")[1]
        start, end = column_index(first), column_index(last) + 1
        for offset, cells_values in enumerate(values):
            index = row_number - 1 + offset
            while len(self.rows) <= index:
                self.rows.append([])
            row = self.rows[index]
            row.extend([""] * max(0, end - len(row)))
            row[start:end] = cells_values


def test_reconciliation_expands_four_to_sixteen_and_is_repeatable():
    repository = FakeRepository()
    original = deepcopy(repository.requests)
    client = StatefulSheetsClient(repository.requests[:4])
    human_values = [row[19:23] for row in client.rows[1:]]
    writer = GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita",
        enabled=True,
    )

    first = reconcile_appointment_requests(repository=repository, writer=writer)
    second = reconcile_appointment_requests(repository=repository, writer=writer)

    assert first == {
        "total": 16, "appended": 12, "updated": 4,
        "skipped": 0, "failed": 0, "errors": [],
    }
    assert second == {
        "total": 16, "appended": 0, "updated": 16,
        "skipped": 0, "failed": 0, "errors": [],
    }
    assert len(client.rows) == 17
    assert len({row[0] for row in client.rows[1:]}) == 16
    assert [row[19:23] for row in client.rows[1:5]] == human_values
    assert repository.requests == original


def test_reconciliation_isolates_failure_and_does_not_expose_exception():
    repository = FakeRepository(count=3)
    visited = []

    class FailingWriter:
        def upsert_request(self, request):
            visited.append(request.id_solicitud)
            if request.id_solicitud == "SOL-RECON-01":
                raise RuntimeError("private credential detail")
            return "updated"

    result = reconcile_appointment_requests(
        repository=repository, writer=FailingWriter(),
    )

    assert visited == [request.id_solicitud for request in repository.requests]
    assert result == {
        "total": 3, "appended": 0, "updated": 2,
        "skipped": 0, "failed": 1,
        "errors": [
            {"id_solicitud": "SOL-RECON-01", "error_code": "sheets_write_failed"},
        ],
    }
    assert "private credential detail" not in str(result)


def test_contract_upgrade_is_explicit_and_preserves_existing_rows():
    from app.services.appointment_request_reconciliation import (
        prepare_human_review_sheet_contract,
    )

    repository = FakeRepository(count=1)
    client = StatefulSheetsClient(repository.requests)
    client.rows[0] = client.rows[0][:26]
    client.rows[1] = client.rows[1][:26]
    original = deepcopy(client.rows)
    writer = GoogleSheetsHumanReviewWriter(
        client=client, spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita", enabled=True,
    )

    assert prepare_human_review_sheet_contract(writer=writer) == "upgrade_required"
    assert client.rows == original
    assert prepare_human_review_sheet_contract(writer=writer, apply=True) == "upgraded"
    assert client.rows[0] == GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
    assert client.rows[1:] == original[1:]
    assert prepare_human_review_sheet_contract(writer=writer, apply=True) == "current"


def test_contract_upgrade_migrates_production_legacy_24_columns():
    from app.services.appointment_request_reconciliation import (
        prepare_human_review_sheet_contract,
    )

    legacy_columns = [
        "id_solicitud",
        "fecha_registro",
        "telefono",
        "nombre_paciente",
        "fecha_solicitada",
        "fecha_solicitada_texto",
        "preferencia_original",
        "franja_solicitada",
        "modalidad",
        "estado_solicitud",
        "observaciones_elvira",
        "estado_origen",
        "interaction_id_origen",
        "direccion_domicilio",
        "servicio_solicitado",
        "fecha_confirmada",
        "franja_confirmada",
        "accion_doctora",
        "motivo_decision",
        "revisado_por",
        "fecha_revision",
        "sync_status",
        "last_sync_at",
        "sync_error",
    ]
    legacy_values = {column: "" for column in legacy_columns}
    legacy_values.update({
        "id_solicitud": "SOL-LEGACY-001",
        "fecha_solicitada_texto": "jueves 8 de octubre",
        "accion_doctora": "confirm",
        "motivo_decision": "Validado por la doctora",
        "revisado_por": "Dra. D'Aleman",
        "fecha_revision": "2026-10-08",
    })

    client = StatefulSheetsClient([])
    client.rows = [
        legacy_columns,
        [legacy_values[column] for column in legacy_columns],
    ]
    original = deepcopy(client.rows)
    writer = GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita",
        enabled=True,
    )

    assert prepare_human_review_sheet_contract(writer=writer) == (
        "legacy_upgrade_required"
    )
    assert client.rows == original
    assert prepare_human_review_sheet_contract(
        writer=writer,
        apply=True,
    ) == "legacy_upgraded"

    assert client.rows[0] == GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
    migrated = dict(zip(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS, client.rows[1]))
    assert migrated["id_solicitud"] == "SOL-LEGACY-001"
    assert migrated["fecha_solicitada_texto"] == "jueves 8 de octubre"
    assert migrated["accion_doctora"] == "confirm"
    assert migrated["motivo_decision"] == "Validado por la doctora"
    assert migrated["revisado_por"] == "Dra. D'Aleman"
    assert migrated["fecha_revision"] == "2026-10-08"


def test_test_classification_requires_explicit_request_id():
    repository = FakeRepository(count=2)
    client = StatefulSheetsClient(repository.requests)
    writer = GoogleSheetsHumanReviewWriter(
        client=client, spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita", enabled=True,
        test_request_ids=frozenset({"SOL-RECON-00"}),
    )

    reconcile_appointment_requests(repository=repository, writer=writer)
    rows = [
        dict(zip(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS, row))
        for row in client.rows[1:]
    ]

    assert rows[0]["tipo_registro"] == "prueba_confirmada"
    assert rows[1]["tipo_registro"] == "sin_clasificar"


def test_operator_reconciliation_preview_does_not_write_or_upgrade():
    from scripts.manual_appointment_request_reconciliation import run_reconciliation

    repository = FakeRepository()
    requests = repository.list_all()
    client = StatefulSheetsClient(requests[:4])
    client.rows = [row[:26] for row in client.rows]
    before = deepcopy(client.rows)
    writer = GoogleSheetsHumanReviewWriter(
        client=client, spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita", enabled=True,
    )

    result = run_reconciliation(repository=repository, writer=writer)

    assert result["mode"] == "preview"
    assert result["total"] == 16
    assert result["present"] == 4
    assert result["missing"] == 12
    assert result["contract"] == "upgrade_required"
    assert client.rows == before


def test_operator_reconciliation_apply_upgrades_and_reconciles_idempotently():
    from scripts.manual_appointment_request_reconciliation import run_reconciliation

    repository = FakeRepository()
    requests = repository.list_all()
    client = StatefulSheetsClient(requests[:4])
    client.rows = [row[:26] for row in client.rows]
    human_before = [row[19:23] for row in client.rows[1:]]
    writer = GoogleSheetsHumanReviewWriter(
        client=client, spreadsheet_id="test-sheet",
        tab_name="Solicitudes_Cita", enabled=True,
    )

    first = run_reconciliation(
        repository=repository, writer=writer, apply=True,
        test_request_ids={"SOL-RECON-00"},
    )
    second = run_reconciliation(
        repository=repository, writer=writer, apply=True,
        test_request_ids={"SOL-RECON-00"},
    )

    assert first["mode"] == "apply"
    assert first["appended"] == 12
    assert first["updated"] == 4
    assert first["failed"] == 0
    assert second["appended"] == 0
    assert second["updated"] == 16
    assert len(client.rows) == 17
    assert [row[19:23] for row in client.rows[1:5]] == human_before
    assert client.rows[1][
        GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS.index("tipo_registro")
    ] == "prueba_confirmada"
