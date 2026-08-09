from app.config import Settings


def build_settings(**updates):
    values = {
        "_env_file": None,
        "google_sheets_enabled": False,
        "google_sheets_spreadsheet_id": None,
        "google_service_account_json": None,
    }
    values.update(updates)
    return Settings(**values)


def test_reactivation_dry_run_is_disabled_by_default():
    settings = build_settings()

    assert settings.reactivation_dry_run_enabled is False


def test_generic_google_sheets_enablement_does_not_enable_reactivation():
    settings = build_settings(
        google_sheets_enabled=True,
        google_sheets_spreadsheet_id="respirarte-crm-control",
        google_service_account_json='{"control": true}',
    )

    assert settings.google_sheets_enabled is True
    assert settings.reactivation_dry_run_enabled is False


def test_reactivation_sheet_tab_has_explicit_safe_default():
    settings = build_settings()

    assert (
        settings.google_sheets_reactivation_tab
        == "Reactivacion_Historica"
    )
