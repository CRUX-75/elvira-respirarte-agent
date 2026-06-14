

import pytest

from app.models.appointment_request import AppointmentRequest
from app.adapters.google_sheets_human_review_writer import (
    GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
    GoogleSheetsHumanReviewWriter,
    map_appointment_request_to_sheet_row,
)


def make_request(**overrides):
    data = {
        "id_solicitud": "SOL-SHEETS-001",
        "telefono": "573001112233",
        "nombre_paciente": "Paciente Control",
        "fecha_solicitada": "2026-06-17",
        "franja_solicitada": "3:00 p. m.–6:00 p. m.",
        "estado_solicitud": "pendiente_confirmacion",
        "servicio_solicitado": "Terapia Respiratoria",
        "direccion_domicilio": "Calle 123 #45-67",
        "source_interaction_id": "wamid.control.001",
        "canal_origen": "whatsapp",
        "observaciones": "Solicitud registrada por Elvira.",
        "created_at": "2026-06-13T12:00:00Z",
        "updated_at": "2026-06-13T12:00:00Z",
    }
    data.update(overrides)
    return AppointmentRequest(**data)


class FakeSheetsClient:
    def __init__(self, existing_rows=None):
        self.existing_rows = existing_rows or []
        self.appended_rows = []
        self.updated_rows = []

    def get_values(self, spreadsheet_id, range_name):
        return self.existing_rows

    def append_row(self, spreadsheet_id, range_name, row):
        self.appended_rows.append((spreadsheet_id, range_name, row))

    def update_row(self, spreadsheet_id, range_name, row_number, row):
        self.updated_rows.append((spreadsheet_id, range_name, row_number, row))


def test_sheet_columns_match_contract():
    assert GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS == [
        "id_solicitud",
        "fecha_registro",
        "telefono",
        "nombre_paciente",
        "fecha_solicitada_texto",
        "franja_solicitada",
        "modalidad",
        "estado_solicitud",
        "observaciones_elvira",
        "interaction_id_origen",
        "direccion_domicilio",
        "servicio_solicitado",
        "tipo_cita",
        "eps",
        "barrio",
        "edad_paciente",
        "notas_clinicas_breves",
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


def test_maps_appointment_request_to_expected_sheet_row():
    request = make_request()

    row = map_appointment_request_to_sheet_row(request)

    assert row["id_solicitud"] == "SOL-SHEETS-001"
    assert row["telefono"] == "573001112233"
    assert row["nombre_paciente"] == "Paciente Control"
    assert row["fecha_solicitada_texto"] == "2026-06-17"
    assert row["franja_solicitada"] == "3:00 p. m.–6:00 p. m."
    assert row["modalidad"] == "Domiciliaria"
    assert row["estado_solicitud"] == "pendiente_confirmacion"
    assert row["observaciones_elvira"] == "Solicitud registrada por Elvira."
    assert row["interaction_id_origen"] == "wamid.control.001"
    assert row["direccion_domicilio"] == "Calle 123 #45-67"
    assert row["servicio_solicitado"] == "Terapia Respiratoria"
    assert row["sync_status"] == "pendiente"
    assert row["sync_error"] == ""


def test_missing_optional_fields_become_empty_strings():
    request = make_request(
        fecha_solicitada=None,
        franja_solicitada=None,
        servicio_solicitado=None,
        direccion_domicilio=None,
        source_interaction_id=None,
        observaciones=None,
    )

    row = map_appointment_request_to_sheet_row(request)

    assert row["fecha_solicitada_texto"] == ""
    assert row["franja_solicitada"] == ""
    assert row["servicio_solicitado"] == ""
    assert row["direccion_domicilio"] == ""
    assert row["interaction_id_origen"] == ""
    assert row["observaciones_elvira"] == ""


def test_appends_missing_request_row():
    client = FakeSheetsClient(existing_rows=[GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS])
    writer = GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id="spreadsheet-control",
        tab_name="Solicitudes_Cita",
        enabled=True,
    )

    result = writer.upsert_request(make_request())

    assert result == "appended"
    assert len(client.appended_rows) == 1
    assert client.updated_rows == []


def test_updates_existing_request_row_by_id_solicitud():
    existing_row = ["SOL-SHEETS-001"] + [""] * (len(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS) - 1)
    client = FakeSheetsClient(
        existing_rows=[
            GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
            existing_row,
        ]
    )
    writer = GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id="spreadsheet-control",
        tab_name="Solicitudes_Cita",
        enabled=True,
    )

    result = writer.upsert_request(make_request())

    assert result == "updated"
    assert client.appended_rows == []
    assert len(client.updated_rows) == 1
    assert client.updated_rows[0][2] == 2


def test_preserves_existing_doctor_owned_values_on_update():
    existing = dict.fromkeys(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS, "")
    existing["id_solicitud"] = "SOL-SHEETS-001"
    existing["accion_doctora"] = "aprobar"
    existing["motivo_decision"] = "Confirmar visita"
    existing["revisado_por"] = "dra_daleman"
    existing["fecha_revision"] = "2026-06-13T12:30:00Z"

    existing_row = [existing[column] for column in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS]
    client = FakeSheetsClient(
        existing_rows=[
            GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS,
            existing_row,
        ]
    )
    writer = GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id="spreadsheet-control",
        tab_name="Solicitudes_Cita",
        enabled=True,
    )

    writer.upsert_request(make_request())

    updated_row = client.updated_rows[0][3]
    updated = dict(zip(GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS, updated_row))

    assert updated["accion_doctora"] == "aprobar"
    assert updated["motivo_decision"] == "Confirmar visita"
    assert updated["revisado_por"] == "dra_daleman"
    assert updated["fecha_revision"] == "2026-06-13T12:30:00Z"


def test_writer_is_skipped_when_disabled():
    client = FakeSheetsClient(existing_rows=[GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS])
    writer = GoogleSheetsHumanReviewWriter(
        client=client,
        spreadsheet_id="spreadsheet-control",
        tab_name="Solicitudes_Cita",
        enabled=False,
    )

    result = writer.upsert_request(make_request())

    assert result == "skipped_disabled"
    assert client.appended_rows == []
    assert client.updated_rows == []


def test_sheet_columns_include_doctor_requested_operational_fields():
    assert "tipo_cita" in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
    assert "eps" in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
    assert "barrio" in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
    assert "edad_paciente" in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS
    assert "notas_clinicas_breves" in GOOGLE_SHEETS_HUMAN_REVIEW_COLUMNS


def test_maps_doctor_requested_operational_fields_to_sheet_row():
    request = make_request(
        tipo_cita="control",
        eps="Compensar",
        barrio="Suba",
        edad_paciente=12,
        notas_clinicas_breves="Control respiratorio domiciliario.",
    )

    row = map_appointment_request_to_sheet_row(request)

    assert row["tipo_cita"] == "control"
    assert row["eps"] == "Compensar"
    assert row["barrio"] == "Suba"
    assert row["edad_paciente"] == "12"
    assert row["notas_clinicas_breves"] == "Control respiratorio domiciliario."
