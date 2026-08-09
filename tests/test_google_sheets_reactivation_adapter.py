import pytest

from app.adapters.google_sheets_reactivation import (
    GOOGLE_SHEETS_REACTIVATION_COLUMNS,
    GoogleSheetsReactivationAdapter,
    ReactivationSheetContractError,
    ReactivationSheetRecord,
)


class FakeSheetsClient:
    def __init__(self, values=None):
        self.values = values or []
        self.get_calls = []
        self.appended_rows = []
        self.updated_rows = []
        self.updated_values = []

    def get_values(self, spreadsheet_id, range_name):
        self.get_calls.append((spreadsheet_id, range_name))
        return self.values

    def append_row(self, spreadsheet_id, range_name, row):
        self.appended_rows.append((spreadsheet_id, range_name, row))

    def update_values(
        self,
        spreadsheet_id,
        range_name,
        values,
    ):
        self.updated_values.append(
            (
                spreadsheet_id,
                range_name,
                values,
            )
        )

    def update_row(
        self,
        spreadsheet_id,
        range_name,
        row_number,
        row,
    ):
        self.updated_rows.append(
            (
                spreadsheet_id,
                range_name,
                row_number,
                row,
            )
        )


def build_adapter(*, client, enabled=True):
    return GoogleSheetsReactivationAdapter(
        client=client,
        spreadsheet_id="respirarte-crm-control",
        tab_name="Reactivacion_Historica",
        enabled=enabled,
    )


def test_reactivation_sheet_columns_match_approved_contract():
    assert GOOGLE_SHEETS_REACTIVATION_COLUMNS == [
        "source_reference",
        "nombre",
        "telefono_original",
        "atendido",
        "autorizado_contacto",
        "telefono_e164",
        "revision_doctora",
        "motivo_exclusion",
        "estado_reactivacion",
        "observaciones",
    ]


def test_reads_reactivation_records_without_applying_domain_decisions():
    client = FakeSheetsClient(
        values=[
            GOOGLE_SHEETS_REACTIVATION_COLUMNS,
            [
                "hist-001",
                "María Control",
                "300 123 4567",
                "SI",
                "PENDIENTE",
                "",
                "PENDIENTE",
                "",
                "",
                "Validación inicial",
            ],
        ]
    )
    adapter = build_adapter(client=client)

    records = adapter.read_records()

    assert records == (
        ReactivationSheetRecord(
            row_number=2,
            source_reference="hist-001",
            name="María Control",
            phone_original="300 123 4567",
            attended="SI",
            authorization_status="PENDIENTE",
            phone_e164="",
            doctor_review_status="PENDIENTE",
            exclusion_reason="",
            reactivation_status="",
            observations="Validación inicial",
        ),
    )
    assert client.get_calls == [
        (
            "respirarte-crm-control",
            "Reactivacion_Historica!A:J",
        )
    ]


def test_read_is_skipped_without_calling_sheets_when_disabled():
    client = FakeSheetsClient(
        values=[GOOGLE_SHEETS_REACTIVATION_COLUMNS]
    )
    adapter = build_adapter(
        client=client,
        enabled=False,
    )

    records = adapter.read_records()

    assert records == ()
    assert client.get_calls == []
    assert client.appended_rows == []
    assert client.updated_rows == []


def test_rejects_missing_required_columns_without_exposing_row_content():
    client = FakeSheetsClient(
        values=[
            [
                "source_reference",
                "nombre",
                "telefono_original",
            ],
            [
                "sensitive-source",
                "Sensitive Name",
                "Sensitive Phone",
            ],
        ]
    )
    adapter = build_adapter(client=client)

    with pytest.raises(
        ReactivationSheetContractError,
        match="Missing required Reactivacion_Historica columns",
    ) as exc_info:
        adapter.read_records()

    error = str(exc_info.value)

    assert "atendido" in error
    assert "telefono_e164" in error
    assert "Sensitive Name" not in error
    assert "Sensitive Phone" not in error


def test_updates_only_system_owned_projection_columns():
    client = FakeSheetsClient(
        values=[GOOGLE_SHEETS_REACTIVATION_COLUMNS]
    )
    adapter = build_adapter(client=client)
    record = ReactivationSheetRecord(
        row_number=4,
        source_reference="hist-004",
        name="Paciente Control",
        phone_original="300 555 0004",
        attended="SI",
        authorization_status="SI",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="Revisión humana preservada",
        reactivation_status="",
        observations="No sobrescribir",
    )

    result = adapter.update_system_projection(
        record,
        phone_e164="+573005550004",
        reactivation_status="eligible",
    )

    assert result == "updated"
    assert client.updated_rows == []
    assert client.updated_values == [
        (
            "respirarte-crm-control",
            "Reactivacion_Historica!F4",
            [["+573005550004"]],
        ),
        (
            "respirarte-crm-control",
            "Reactivacion_Historica!I4",
            [["eligible"]],
        ),
    ]
    assert client.appended_rows == []


def test_projection_update_is_skipped_when_disabled():
    client = FakeSheetsClient()
    adapter = build_adapter(
        client=client,
        enabled=False,
    )
    record = ReactivationSheetRecord(
        row_number=2,
        source_reference="hist-disabled",
        name="Control",
        phone_original="3000000000",
        attended="SI",
        authorization_status="SI",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="",
    )

    result = adapter.update_system_projection(
        record,
        phone_e164="+573000000000",
        reactivation_status="eligible",
    )

    assert result == "skipped_disabled"
    assert client.get_calls == []
    assert client.updated_rows == []


def test_system_projection_updates_only_system_owned_cells():
    client = FakeSheetsClient()

    def update_values(spreadsheet_id, range_name, values):
        if not hasattr(client, "updated_values"):
            client.updated_values = []
        client.updated_values.append(
            (spreadsheet_id, range_name, values)
        )

    client.update_values = update_values

    adapter = build_adapter(client=client)

    record = ReactivationSheetRecord(
        row_number=7,
        source_reference="hist-007",
        name="Paciente Control",
        phone_original="300 000 0007",
        attended="SI",
        authorization_status="SI",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="NO SOBRESCRIBIR",
    )

    result = adapter.update_system_projection(
        record,
        phone_e164="573000000007",
        reactivation_status="eligible",
    )

    assert result == "updated"
    assert client.updated_rows == []
    assert client.updated_values == [
        (
            "respirarte-crm-control",
            "Reactivacion_Historica!F7",
            [["573000000007"]],
        ),
        (
            "respirarte-crm-control",
            "Reactivacion_Historica!I7",
            [["eligible"]],
        ),
    ]


def test_reordered_headers_fail_closed_before_projection():
    reordered_headers = list(GOOGLE_SHEETS_REACTIVATION_COLUMNS)
    reordered_headers[4], reordered_headers[5] = (
        reordered_headers[5],
        reordered_headers[4],
    )

    client = FakeSheetsClient(
        values=[
            reordered_headers,
            [
                "hist-001",
                "Paciente Control",
                "300 000 0001",
                "SI",
                "",
                "SI",
                "APROBADO",
                "",
                "",
                "",
            ],
        ]
    )

    adapter = build_adapter(client=client)

    with pytest.raises(
        ReactivationSheetContractError,
        match="column order",
    ):
        adapter.read_records()
