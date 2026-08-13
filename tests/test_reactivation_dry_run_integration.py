from app.adapters.google_sheets_reactivation import (
    GOOGLE_SHEETS_REACTIVATION_COLUMNS,
    GoogleSheetsReactivationAdapter,
)
from app.services.reactivation_dry_run_context import (
    ReactivationDryRunContextResolver,
)
from app.services.reactivation_dry_run_runtime import (
    run_reactivation_dry_run_best_effort,
)


class FakeSheetsClient:
    def __init__(self):
        self.values = [
            GOOGLE_SHEETS_REACTIVATION_COLUMNS,
            [
                "hist-001",
                "Paciente Control",
                "300 000 0001",
                "SI",
                "SI",
                "",
                "APROBADO",
                "",
                "",
                "",
            ],
        ]
        self.updated_values = []

    def get_values(self, spreadsheet_id, range_name):
        return self.values

    def update_values(self, spreadsheet_id, range_name, values):
        self.updated_values.append(
            (spreadsheet_id, range_name, values)
        )


def test_complete_dry_run_path_uses_safe_projection_without_real_io():
    client = FakeSheetsClient()

    adapter = GoogleSheetsReactivationAdapter(
        client=client,
        spreadsheet_id="respirarte-crm-control",
        tab_name="Reactivacion_Historica",
        enabled=True,
    )

    resolver = ReactivationDryRunContextResolver(
        campaign_id="campaign-1",
        default_country_code="57",
        patient_lookup=lambda phone: None,
        campaign_contact_lookup=(
            lambda *, campaign_id, phone_e164: None
        ),
    )

    result = run_reactivation_dry_run_best_effort(
        adapter=adapter,
        context_resolver=resolver,
        default_country_code="57",
    )

    assert result.total == 1
    assert result.eligible == 1
    assert result.excluded == 0
    assert result.invalid_input == 0
    assert result.runtime_error == 0

    assert client.updated_values == [
        (
            "respirarte-crm-control",
            "Reactivacion_Historica!F2",
            [["573000000001"]],
        ),
        (
            "respirarte-crm-control",
            "Reactivacion_Historica!I2",
            [["eligible"]],
        ),
    ]
