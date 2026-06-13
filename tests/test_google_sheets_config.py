from app.config import Settings


def test_google_sheets_config_defaults_are_safe():
    settings = Settings()

    assert settings.google_sheets_enabled is False
    assert settings.google_sheets_spreadsheet_id is None
    assert settings.google_sheets_solicitudes_cita_tab == "Solicitudes_Cita"
    assert settings.google_service_account_json is None


def test_google_sheets_config_can_be_enabled_with_env_values(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "spreadsheet-control")
    monkeypatch.setenv("GOOGLE_SHEETS_SOLICITUDES_CITA_TAB", "Solicitudes_Cita")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type":"service_account"}')

    settings = Settings()

    assert settings.google_sheets_enabled is True
    assert settings.google_sheets_spreadsheet_id == "spreadsheet-control"
    assert settings.google_sheets_solicitudes_cita_tab == "Solicitudes_Cita"
    assert settings.google_service_account_json == '{"type":"service_account"}'
