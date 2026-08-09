from app.config import Settings
from app.services.reactivation_dry_run_factory import (
    build_reactivation_dry_run_dependencies,
)


class FakeEngine:
    def __init__(self):
        self.connect_calls = 0
        self.begin_calls = 0


class FakeServiceBuilder:
    def __init__(self):
        self.calls = []

    def __call__(self, credentials):
        self.calls.append(credentials)
        return object()


class FakePatientLookup:
    def __init__(self):
        self.calls = []

    def __call__(self, phone):
        self.calls.append(phone)
        return None


def make_settings(**updates):
    values = {
        "_env_file": None,
        "google_sheets_enabled": False,
        "google_sheets_spreadsheet_id": "respirarte-crm-control",
        "google_sheets_reactivation_tab": "Reactivacion_Historica",
        "google_service_account_json": '{"control": true}',
        "reactivation_dry_run_enabled": False,
    }
    values.update(updates)
    return Settings(**values)


def test_factory_is_inert_when_reactivation_flag_is_disabled():
    service_builder = FakeServiceBuilder()

    result = build_reactivation_dry_run_dependencies(
        settings=make_settings(
            google_sheets_enabled=True,
        ),
        campaign_id="campaign-1",
        default_country_code="57",
        engine=FakeEngine(),
        patient_lookup=FakePatientLookup(),
        service_builder=service_builder,
    )

    assert result is None
    assert service_builder.calls == []


def test_factory_builds_dependencies_only_when_explicitly_enabled():
    engine = FakeEngine()
    patient_lookup = FakePatientLookup()
    service_builder = FakeServiceBuilder()

    result = build_reactivation_dry_run_dependencies(
        settings=make_settings(
            reactivation_dry_run_enabled=True,
        ),
        campaign_id="campaign-1",
        default_country_code="57",
        engine=engine,
        patient_lookup=patient_lookup,
        service_builder=service_builder,
    )

    assert result is not None
    assert result.adapter.spreadsheet_id == "respirarte-crm-control"
    assert result.adapter.tab_name == "Reactivacion_Historica"
    assert result.adapter.enabled is True
    assert result.context_resolver.campaign_id == "campaign-1"
    assert result.default_country_code == "57"

    assert service_builder.calls == ['{"control": true}']
    assert engine.connect_calls == 0
    assert engine.begin_calls == 0
    assert patient_lookup.calls == []
