from app.adapters.google_sheets_human_review_writer import GoogleSheetsHumanReviewWriter
from app.adapters.google_sheets_human_review_writer_factory import (
    build_google_sheets_human_review_writer,
)
from app.config import Settings


class FakeSheetsService:
    pass


def fake_service_builder(service_account_json):
    return FakeSheetsService()


def test_factory_returns_none_when_google_sheets_disabled(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_ENABLED", "false")
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "spreadsheet-control")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type":"service_account"}')

    writer = build_google_sheets_human_review_writer(
        settings=Settings(_env_file=None),
        service_builder=fake_service_builder,
    )

    assert writer is None


def test_factory_returns_none_when_spreadsheet_id_missing(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_ENABLED", "true")
    monkeypatch.delenv("GOOGLE_SHEETS_SPREADSHEET_ID", raising=False)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type":"service_account"}')

    writer = build_google_sheets_human_review_writer(
        settings=Settings(_env_file=None),
        service_builder=fake_service_builder,
    )

    assert writer is None


def test_factory_returns_none_when_service_account_json_missing(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "spreadsheet-control")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)

    writer = build_google_sheets_human_review_writer(
        settings=Settings(_env_file=None),
        service_builder=fake_service_builder,
    )

    assert writer is None


def test_factory_builds_writer_when_all_required_config_exists(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "spreadsheet-control")
    monkeypatch.setenv("GOOGLE_SHEETS_SOLICITUDES_CITA_TAB", "Solicitudes_Cita")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type":"service_account"}')

    writer = build_google_sheets_human_review_writer(
        settings=Settings(_env_file=None),
        service_builder=fake_service_builder,
    )

    assert isinstance(writer, GoogleSheetsHumanReviewWriter)
    assert writer.spreadsheet_id == "spreadsheet-control"
    assert writer.tab_name == "Solicitudes_Cita"
    assert writer.enabled is True
