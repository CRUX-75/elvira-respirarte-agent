import pytest

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
    ReactivationExclusionReason,
)
from app.services.reactivation_dry_run import ReactivationDryRunDecision
from app.services.reactivation_manual_trigger import (
    build_manual_reactivation_contact,
)


def _record() -> ReactivationSheetRecord:
    return ReactivationSheetRecord(
        row_number=2,
        source_reference="HIST-001",
        name="Paciente Prueba",
        phone_original="3204454568",
        attended="SI",
        authorization_status="SI",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="",
    )


def test_builds_persistable_contact_for_eligible_record():
    record = _record()

    decision = ReactivationDryRunDecision(
        row_number=2,
        source_reference="HIST-001",
        phone_e164="573204454568",
        status=ReactivationContactStatus.ELIGIBLE,
        exclusion_reasons=(),
    )

    contact = build_manual_reactivation_contact(
        campaign_id="reactivacion-manual-2026-09",
        record=record,
        decision=decision,
    )

    assert contact is not None
    assert contact.campaign_id == "reactivacion-manual-2026-09"
    assert contact.source_reference == "HIST-001"
    assert contact.name == "Paciente Prueba"
    assert contact.phone_original == "3204454568"
    assert contact.phone_e164 == "573204454568"
    assert contact.attended is True
    assert (
        contact.authorization_status
        == ReactivationAuthorizationStatus.APPROVED
    )
    assert (
        contact.doctor_review_status
        == ReactivationDoctorReviewStatus.APPROVED
    )
    assert contact.status == ReactivationContactStatus.ELIGIBLE
    assert contact.idempotency_key.startswith("reactivation:")
    assert contact.id.startswith("manual-reactivation:")


def test_excluded_record_is_not_built_for_persistence():
    record = _record()

    decision = ReactivationDryRunDecision(
        row_number=2,
        source_reference="HIST-001",
        phone_e164="573204454568",
        status=ReactivationContactStatus.EXCLUDED,
        exclusion_reasons=(
            ReactivationExclusionReason.AUTHORIZATION_PENDING,
        ),
    )

    contact = build_manual_reactivation_contact(
        campaign_id="reactivacion-manual-2026-09",
        record=record,
        decision=decision,
    )

    assert contact is None


def test_refuses_decision_from_different_sheet_record():
    record = _record()

    decision = ReactivationDryRunDecision(
        row_number=3,
        source_reference="HIST-002",
        phone_e164="573204454568",
        status=ReactivationContactStatus.ELIGIBLE,
        exclusion_reasons=(),
    )

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        build_manual_reactivation_contact(
            campaign_id="reactivacion-manual-2026-09",
            record=record,
            decision=decision,
        )


class _FakeContactRepository:
    def __init__(self):
        self.by_natural_key = {}
        self.create_calls = 0

    def create_or_get(self, contact):
        self.create_calls += 1

        key = (
            contact.campaign_id,
            contact.phone_e164,
        )

        existing = self.by_natural_key.get(key)

        if existing is not None:
            return existing

        self.by_natural_key[key] = contact
        return contact


def _eligible_decision(
    *,
    row_number=2,
    source_reference="HIST-001",
    phone_e164="573204454568",
):
    return ReactivationDryRunDecision(
        row_number=row_number,
        source_reference=source_reference,
        phone_e164=phone_e164,
        status=ReactivationContactStatus.ELIGIBLE,
        exclusion_reasons=(),
    )


def test_persists_only_eligible_contacts():
    from app.services.reactivation_manual_trigger import (
        persist_manual_reactivation_contacts,
    )

    eligible_record = _record()

    excluded_record = ReactivationSheetRecord(
        row_number=3,
        source_reference="HIST-002",
        name="Paciente Excluido",
        phone_original="3204459999",
        attended="SI",
        authorization_status="PENDIENTE",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="",
    )

    excluded_decision = ReactivationDryRunDecision(
        row_number=3,
        source_reference="HIST-002",
        phone_e164="573204459999",
        status=ReactivationContactStatus.EXCLUDED,
        exclusion_reasons=(
            ReactivationExclusionReason.AUTHORIZATION_PENDING,
        ),
    )

    repository = _FakeContactRepository()

    persisted = persist_manual_reactivation_contacts(
        campaign_id="reactivacion-manual-2026-09",
        prepared_items=(
            (
                eligible_record,
                _eligible_decision(),
            ),
            (
                excluded_record,
                excluded_decision,
            ),
        ),
        contact_repository=repository,
    )

    assert len(persisted) == 1
    assert persisted[0].source_reference == "HIST-001"
    assert persisted[0].status == ReactivationContactStatus.ELIGIBLE
    assert repository.create_calls == 1


def test_persistence_is_idempotent_through_repository_contract():
    from app.services.reactivation_manual_trigger import (
        persist_manual_reactivation_contacts,
    )

    repository = _FakeContactRepository()

    prepared = (
        (
            _record(),
            _eligible_decision(),
        ),
    )

    first = persist_manual_reactivation_contacts(
        campaign_id="reactivacion-manual-2026-09",
        prepared_items=prepared,
        contact_repository=repository,
    )

    second = persist_manual_reactivation_contacts(
        campaign_id="reactivacion-manual-2026-09",
        prepared_items=prepared,
        contact_repository=repository,
    )

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].id == second[0].id
    assert first[0].idempotency_key == second[0].idempotency_key

    assert len(repository.by_natural_key) == 1


def test_empty_campaign_id_is_refused_before_persistence():
    from app.services.reactivation_manual_trigger import (
        persist_manual_reactivation_contacts,
    )

    repository = _FakeContactRepository()

    with pytest.raises(
        ValueError,
        match="campaign_id is required",
    ):
        persist_manual_reactivation_contacts(
            campaign_id=" ",
            prepared_items=(),
            contact_repository=repository,
        )

    assert repository.create_calls == 0


class _FakeSheetAdapter:
    def __init__(self, records):
        self.records = tuple(records)

    def read_records(self):
        return self.records


def test_manual_preflight_counts_eligible_and_excluded():
    from app.services.reactivation_dry_run import ReactivationDryRunContext
    from app.services.reactivation_manual_trigger import (
        preflight_manual_reactivation,
    )

    eligible_record = _record()

    excluded_record = ReactivationSheetRecord(
        row_number=3,
        source_reference="HIST-002",
        name="Paciente Excluido",
        phone_original="3204459999",
        attended="SI",
        authorization_status="PENDIENTE",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="",
    )

    result = preflight_manual_reactivation(
        adapter=_FakeSheetAdapter(
            (eligible_record, excluded_record)
        ),
        context_resolver=lambda record: ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert result.total == 2
    assert result.eligible == 1
    assert result.excluded == 1
    assert result.invalid_input == 0
    assert result.runtime_error == 0
    assert len(result.prepared_items) == 2


def test_manual_preflight_isolates_invalid_sheet_value():
    from app.services.reactivation_dry_run import ReactivationDryRunContext
    from app.services.reactivation_manual_trigger import (
        preflight_manual_reactivation,
    )

    invalid_record = ReactivationSheetRecord(
        row_number=2,
        source_reference="HIST-INVALID",
        name="Paciente Prueba",
        phone_original="3204454568",
        attended="TALVEZ",
        authorization_status="SI",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="",
    )

    result = preflight_manual_reactivation(
        adapter=_FakeSheetAdapter((invalid_record,)),
        context_resolver=lambda record: ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert result.total == 1
    assert result.eligible == 0
    assert result.excluded == 0
    assert result.invalid_input == 1
    assert result.runtime_error == 0
    assert result.prepared_items == ()


def test_manual_preflight_isolates_context_resolution_failure():
    from app.services.reactivation_manual_trigger import (
        preflight_manual_reactivation,
    )

    def failing_context_resolver(record):
        raise RuntimeError("simulated context failure")

    result = preflight_manual_reactivation(
        adapter=_FakeSheetAdapter((_record(),)),
        context_resolver=failing_context_resolver,
        default_country_code="57",
    )

    assert result.total == 1
    assert result.eligible == 0
    assert result.excluded == 0
    assert result.invalid_input == 0
    assert result.runtime_error == 1
    assert result.prepared_items == ()


def _preflight_result_for_selection(*items):
    from app.services.reactivation_manual_trigger import (
        ManualReactivationPreflightResult,
    )

    return ManualReactivationPreflightResult(
        total=len(items),
        eligible=sum(
            decision.status == ReactivationContactStatus.ELIGIBLE
            for _, decision in items
        ),
        excluded=sum(
            decision.status == ReactivationContactStatus.EXCLUDED
            for _, decision in items
        ),
        invalid_input=0,
        runtime_error=0,
        prepared_items=tuple(items),
    )


def test_manual_selection_does_not_auto_select_other_eligible_rows():
    from app.services.reactivation_manual_trigger import (
        select_manual_reactivation_items,
    )

    first_record = _record()
    first_decision = _eligible_decision()

    second_record = ReactivationSheetRecord(
        row_number=3,
        source_reference="TEST-MANUAL-001",
        name="Contacto Controlado",
        phone_original="004915166800000",
        attended="SI",
        authorization_status="SI",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="Prueba controlada P6-F.12",
    )

    second_decision = _eligible_decision(
        row_number=3,
        source_reference="TEST-MANUAL-001",
        phone_e164="4915166800000",
    )

    preflight = _preflight_result_for_selection(
        (first_record, first_decision),
        (second_record, second_decision),
    )

    selection = select_manual_reactivation_items(
        preflight=preflight,
        source_references=("TEST-MANUAL-001",),
    )

    assert selection.source_references == ("TEST-MANUAL-001",)
    assert selection.eligible == 1
    assert selection.excluded == 0
    assert len(selection.prepared_items) == 1
    assert (
        selection.prepared_items[0][0].source_reference
        == "TEST-MANUAL-001"
    )


def test_manual_selection_refuses_duplicate_requested_references():
    from app.services.reactivation_manual_trigger import (
        select_manual_reactivation_items,
    )

    preflight = _preflight_result_for_selection(
        (_record(), _eligible_decision()),
    )

    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        select_manual_reactivation_items(
            preflight=preflight,
            source_references=("HIST-001", "HIST-001"),
        )


def test_manual_selection_refuses_unknown_or_failed_reference():
    from app.services.reactivation_manual_trigger import (
        select_manual_reactivation_items,
    )

    preflight = _preflight_result_for_selection(
        (_record(), _eligible_decision()),
    )

    with pytest.raises(
        ValueError,
        match="not successfully evaluated",
    ):
        select_manual_reactivation_items(
            preflight=preflight,
            source_references=("TEST-NOT-FOUND",),
        )


def test_manual_selection_can_report_explicit_excluded_record():
    from app.services.reactivation_manual_trigger import (
        select_manual_reactivation_items,
    )

    record = _record()

    decision = ReactivationDryRunDecision(
        row_number=2,
        source_reference="HIST-001",
        phone_e164="573204454568",
        status=ReactivationContactStatus.EXCLUDED,
        exclusion_reasons=(
            ReactivationExclusionReason.AUTHORIZATION_PENDING,
        ),
    )

    preflight = _preflight_result_for_selection(
        (record, decision),
    )

    selection = select_manual_reactivation_items(
        preflight=preflight,
        source_references=("HIST-001",),
    )

    assert selection.eligible == 0
    assert selection.excluded == 1
    assert len(selection.prepared_items) == 1
