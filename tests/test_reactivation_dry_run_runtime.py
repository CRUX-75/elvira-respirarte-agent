from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.services.reactivation_dry_run import ReactivationDryRunContext
from app.services.reactivation_dry_run_runtime import (
    run_reactivation_dry_run_best_effort,
)


def make_record(
    *,
    row_number,
    source_reference,
    phone_original,
    attended="SI",
    authorization_status="SI",
    doctor_review_status="APROBADO",
):
    return ReactivationSheetRecord(
        row_number=row_number,
        source_reference=source_reference,
        name=f"Paciente {source_reference}",
        phone_original=phone_original,
        attended=attended,
        authorization_status=authorization_status,
        phone_e164="",
        doctor_review_status=doctor_review_status,
        exclusion_reason="",
        reactivation_status="",
        observations="",
    )


class FakeReactivationAdapter:
    def __init__(self, records):
        self.records = tuple(records)
        self.projections = []

    def read_records(self):
        return self.records

    def update_system_projection(
        self,
        record,
        *,
        phone_e164,
        reactivation_status,
    ):
        self.projections.append(
            (
                record.row_number,
                phone_e164,
                reactivation_status,
            )
        )
        return "updated"


def default_context_resolver(record):
    return ReactivationDryRunContext()


def test_batch_evaluates_and_projects_multiple_records():
    adapter = FakeReactivationAdapter(
        [
            make_record(
                row_number=2,
                source_reference="hist-001",
                phone_original="300 000 0001",
            ),
            make_record(
                row_number=3,
                source_reference="hist-002",
                phone_original="300 000 0002",
                authorization_status="PENDIENTE",
            ),
        ]
    )

    result = run_reactivation_dry_run_best_effort(
        adapter=adapter,
        context_resolver=default_context_resolver,
        default_country_code="57",
    )

    assert result.total == 2
    assert result.eligible == 1
    assert result.excluded == 1
    assert result.invalid_input == 0
    assert result.runtime_error == 0

    assert adapter.projections == [
        (2, "573000000001", "eligible"),
        (3, "573000000002", "excluded"),
    ]

    assert [item.outcome for item in result.items] == [
        "eligible",
        "excluded",
    ]


def test_invalid_controlled_row_is_isolated_and_later_rows_continue():
    adapter = FakeReactivationAdapter(
        [
            make_record(
                row_number=2,
                source_reference="hist-invalid",
                phone_original="300 000 0001",
                authorization_status="AUTORIZADO",
            ),
            make_record(
                row_number=3,
                source_reference="hist-valid",
                phone_original="300 000 0002",
            ),
        ]
    )

    result = run_reactivation_dry_run_best_effort(
        adapter=adapter,
        context_resolver=default_context_resolver,
        default_country_code="57",
    )

    assert result.total == 2
    assert result.eligible == 1
    assert result.excluded == 0
    assert result.invalid_input == 1
    assert result.runtime_error == 0

    assert adapter.projections == [
        (3, "573000000002", "eligible"),
    ]

    assert result.items[0].row_number == 2
    assert result.items[0].source_reference == "hist-invalid"
    assert result.items[0].outcome == "invalid_input"
    assert (
        result.items[0].error_category
        == "invalid_controlled_sheet_value"
    )

    assert result.items[1].outcome == "eligible"


def test_context_resolver_safety_facts_feed_existing_domain_rules():
    adapter = FakeReactivationAdapter(
        [
            make_record(
                row_number=2,
                source_reference="hist-optout",
                phone_original="300 000 0001",
            ),
        ]
    )

    def context_resolver(record):
        return ReactivationDryRunContext(
            patient_opt_out=True,
        )

    result = run_reactivation_dry_run_best_effort(
        adapter=adapter,
        context_resolver=context_resolver,
        default_country_code="57",
    )

    assert result.total == 1
    assert result.eligible == 0
    assert result.excluded == 1

    assert adapter.projections == [
        (2, "573000000001", "excluded"),
    ]

    assert result.items[0].outcome == "excluded"
    assert "existing_opt_out" in result.items[0].exclusion_reasons


def test_context_resolver_exception_isolated_without_projection():
    adapter = FakeReactivationAdapter(
        [
            make_record(
                row_number=2,
                source_reference="hist-error",
                phone_original="300 000 0001",
            ),
            make_record(
                row_number=3,
                source_reference="hist-ok",
                phone_original="300 000 0002",
            ),
        ]
    )

    def context_resolver(record):
        if record.row_number == 2:
            raise RuntimeError(
                "database details must not escape"
            )

        return ReactivationDryRunContext()

    result = run_reactivation_dry_run_best_effort(
        adapter=adapter,
        context_resolver=context_resolver,
        default_country_code="57",
    )

    assert result.total == 2
    assert result.eligible == 1
    assert result.excluded == 0
    assert result.invalid_input == 0
    assert result.runtime_error == 1

    assert adapter.projections == [
        (3, "573000000002", "eligible"),
    ]

    failed = result.items[0]

    assert failed.outcome == "runtime_error"
    assert failed.error_category == "context_resolution_failed"
    assert "database details" not in repr(failed)


def test_projection_failure_isolated_and_counted_separately():
    class ProjectionFailingAdapter(FakeReactivationAdapter):
        def update_system_projection(
            self,
            record,
            *,
            phone_e164,
            reactivation_status,
        ):
            if record.row_number == 2:
                raise RuntimeError(
                    "sensitive sheets transport detail"
                )

            return super().update_system_projection(
                record,
                phone_e164=phone_e164,
                reactivation_status=reactivation_status,
            )

    adapter = ProjectionFailingAdapter(
        [
            make_record(
                row_number=2,
                source_reference="hist-projection-error",
                phone_original="300 000 0001",
            ),
            make_record(
                row_number=3,
                source_reference="hist-ok",
                phone_original="300 000 0002",
            ),
        ]
    )

    result = run_reactivation_dry_run_best_effort(
        adapter=adapter,
        context_resolver=default_context_resolver,
        default_country_code="57",
    )

    assert result.total == 2
    assert result.eligible == 1
    assert result.excluded == 0
    assert result.invalid_input == 0
    assert result.runtime_error == 1

    assert adapter.projections == [
        (3, "573000000002", "eligible"),
    ]

    failed = result.items[0]

    assert failed.outcome == "runtime_error"
    assert failed.error_category == "projection_failed"
    assert "sensitive sheets transport detail" not in repr(failed)


def test_empty_batch_returns_zeroed_safe_summary():
    adapter = FakeReactivationAdapter([])

    result = run_reactivation_dry_run_best_effort(
        adapter=adapter,
        context_resolver=default_context_resolver,
        default_country_code="57",
    )

    assert result.total == 0
    assert result.eligible == 0
    assert result.excluded == 0
    assert result.invalid_input == 0
    assert result.runtime_error == 0
    assert result.items == ()
    assert adapter.projections == []
