import pytest

from app.adapters.google_sheets_client import (
    GoogleSheetsApiClient,
    GoogleSheetsConfigError,
    build_google_sheets_service,
)


class FakeExecute:
    def __init__(self, payload=None):
        self.payload = payload or {}
        self.executed = False

    def execute(self):
        self.executed = True
        return self.payload


class FakeValuesResource:
    def __init__(self):
        self.get_calls = []
        self.append_calls = []
        self.update_calls = []

    def get(self, spreadsheetId, range):
        self.get_calls.append(
            {
                "spreadsheetId": spreadsheetId,
                "range": range,
            }
        )
        return FakeExecute({"values": [["id_solicitud"], ["SOL-001"]]})

    def append(self, spreadsheetId, range, valueInputOption, body):
        self.append_calls.append(
            {
                "spreadsheetId": spreadsheetId,
                "range": range,
                "valueInputOption": valueInputOption,
                "body": body,
            }
        )
        return FakeExecute({"updates": {"updatedRows": 1}})

    def update(self, spreadsheetId, range, valueInputOption, body):
        self.update_calls.append(
            {
                "spreadsheetId": spreadsheetId,
                "range": range,
                "valueInputOption": valueInputOption,
                "body": body,
            }
        )
        return FakeExecute({"updatedRows": 1})


class FakeSpreadsheetsResource:
    def __init__(self, values_resource):
        self.values_resource = values_resource

    def values(self):
        return self.values_resource


class FakeSheetsService:
    def __init__(self):
        self.values_resource = FakeValuesResource()

    def spreadsheets(self):
        return FakeSpreadsheetsResource(self.values_resource)


def test_build_google_sheets_service_rejects_missing_service_account_json():
    with pytest.raises(GoogleSheetsConfigError, match="GOOGLE_SERVICE_ACCOUNT_JSON is required"):
        build_google_sheets_service(None)


def test_build_google_sheets_service_rejects_invalid_json():
    with pytest.raises(GoogleSheetsConfigError, match="Invalid GOOGLE_SERVICE_ACCOUNT_JSON"):
        build_google_sheets_service("{not-json}")


def test_build_google_sheets_service_uses_service_account_json(monkeypatch):
    calls = {}

    def fake_credentials_from_info(info, scopes):
        calls["info"] = info
        calls["scopes"] = scopes
        return "fake-credentials"

    def fake_build(service_name, version, credentials):
        calls["service_name"] = service_name
        calls["version"] = version
        calls["credentials"] = credentials
        return FakeSheetsService()

    monkeypatch.setattr(
        "app.adapters.google_sheets_client._service_account_credentials_from_info",
        fake_credentials_from_info,
    )
    monkeypatch.setattr(
        "app.adapters.google_sheets_client._build_google_service",
        fake_build,
    )

    service = build_google_sheets_service('{"type":"service_account","project_id":"control"}')

    assert isinstance(service, FakeSheetsService)
    assert calls["info"]["type"] == "service_account"
    assert calls["scopes"] == ["https://www.googleapis.com/auth/spreadsheets"]
    assert calls["service_name"] == "sheets"
    assert calls["version"] == "v4"
    assert calls["credentials"] == "fake-credentials"


def test_get_values_calls_google_sheets_api_chain():
    service = FakeSheetsService()
    client = GoogleSheetsApiClient(service=service)

    values = client.get_values("spreadsheet-control", "Solicitudes_Cita!A:U")

    assert values == [["id_solicitud"], ["SOL-001"]]
    assert service.values_resource.get_calls == [
        {
            "spreadsheetId": "spreadsheet-control",
            "range": "Solicitudes_Cita!A:U",
        }
    ]


def test_append_row_calls_google_sheets_api_chain_with_user_entered():
    service = FakeSheetsService()
    client = GoogleSheetsApiClient(service=service)

    client.append_row(
        "spreadsheet-control",
        "Solicitudes_Cita!A:U",
        ["SOL-001", "2026-06-13"],
    )

    assert service.values_resource.append_calls == [
        {
            "spreadsheetId": "spreadsheet-control",
            "range": "Solicitudes_Cita!A:U",
            "valueInputOption": "USER_ENTERED",
            "body": {"values": [["SOL-001", "2026-06-13"]]},
        }
    ]


def test_update_row_calls_google_sheets_api_chain_with_user_entered():
    service = FakeSheetsService()
    client = GoogleSheetsApiClient(service=service)

    client.update_row(
        "spreadsheet-control",
        "Solicitudes_Cita!A:U",
        2,
        ["SOL-001", "2026-06-13"],
    )

    assert service.values_resource.update_calls == [
        {
            "spreadsheetId": "spreadsheet-control",
            "range": "Solicitudes_Cita!A2:U2",
            "valueInputOption": "USER_ENTERED",
            "body": {"values": [["SOL-001", "2026-06-13"]]},
        }
    ]
