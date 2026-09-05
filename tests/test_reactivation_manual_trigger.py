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


class _FakeCampaignRepository:
    def __init__(self):
        self.by_id = {}
        self.create_calls = 0

    def create_or_get(self, campaign):
        self.create_calls += 1

        existing = self.by_id.get(campaign.id)

        if existing is not None:
            return existing

        self.by_id[campaign.id] = campaign
        return campaign


def _eligible_selection():
    from app.services.reactivation_manual_trigger import (
        ManualReactivationSelection,
    )

    return ManualReactivationSelection(
        source_references=("HIST-001",),
        eligible=1,
        excluded=0,
        prepared_items=(
            (
                _record(),
                _eligible_decision(),
            ),
        ),
    )


def test_persists_draft_campaign_and_explicit_eligible_contact():
    from app.models.reactivation_campaign import (
        ReactivationCampaignStatus,
    )
    from app.services.reactivation_manual_trigger import (
        persist_manual_reactivation_selection,
    )

    campaign_repository = _FakeCampaignRepository()
    contact_repository = _FakeContactRepository()

    result = persist_manual_reactivation_selection(
        campaign_id="p6-f-12-test-001",
        campaign_name="P6-F.12 controlled test",
        selection=_eligible_selection(),
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
    )

    assert result.campaign.id == "p6-f-12-test-001"
    assert (
        result.campaign.status
        == ReactivationCampaignStatus.DRAFT
    )
    assert result.campaign.template_name == "reactivacion_respirarte"
    assert result.campaign.template_language == "es_CO"

    assert len(result.contacts) == 1
    assert result.contacts[0].source_reference == "HIST-001"
    assert result.contacts[0].campaign_id == "p6-f-12-test-001"


def test_manual_campaign_persistence_is_idempotent():
    from app.services.reactivation_manual_trigger import (
        persist_manual_reactivation_selection,
    )

    campaign_repository = _FakeCampaignRepository()
    contact_repository = _FakeContactRepository()

    first = persist_manual_reactivation_selection(
        campaign_id="p6-f-12-test-001",
        campaign_name="P6-F.12 controlled test",
        selection=_eligible_selection(),
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
    )

    second = persist_manual_reactivation_selection(
        campaign_id="p6-f-12-test-001",
        campaign_name="P6-F.12 controlled test",
        selection=_eligible_selection(),
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
    )

    assert first.campaign.id == second.campaign.id
    assert first.contacts[0].id == second.contacts[0].id
    assert len(campaign_repository.by_id) == 1
    assert len(contact_repository.by_natural_key) == 1


def test_refuses_excluded_selection_before_campaign_persistence():
    from app.services.reactivation_manual_trigger import (
        ManualReactivationSelection,
        persist_manual_reactivation_selection,
    )

    excluded_decision = ReactivationDryRunDecision(
        row_number=2,
        source_reference="HIST-001",
        phone_e164="573204454568",
        status=ReactivationContactStatus.EXCLUDED,
        exclusion_reasons=(
            ReactivationExclusionReason.AUTHORIZATION_PENDING,
        ),
    )

    selection = ManualReactivationSelection(
        source_references=("HIST-001",),
        eligible=0,
        excluded=1,
        prepared_items=((_record(), excluded_decision),),
    )

    campaign_repository = _FakeCampaignRepository()
    contact_repository = _FakeContactRepository()

    with pytest.raises(
        ValueError,
        match="must be eligible",
    ):
        persist_manual_reactivation_selection(
            campaign_id="p6-f-12-test-001",
            campaign_name="P6-F.12 controlled test",
            selection=selection,
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
        )

    assert campaign_repository.create_calls == 0
    assert contact_repository.create_calls == 0


def test_refuses_adding_contacts_after_campaign_leaves_draft():
    from app.models.reactivation_campaign import (
        ReactivationCampaign,
        ReactivationCampaignStatus,
    )
    from app.services.reactivation_manual_trigger import (
        persist_manual_reactivation_selection,
    )

    campaign_repository = _FakeCampaignRepository()
    contact_repository = _FakeContactRepository()

    campaign_repository.by_id["p6-f-12-test-001"] = (
        ReactivationCampaign(
            id="p6-f-12-test-001",
            name="P6-F.12 controlled test",
            template_name="reactivacion_respirarte",
            template_language="es_CO",
            status=ReactivationCampaignStatus.ACTIVE,
        )
    )

    with pytest.raises(
        ValueError,
        match="only while campaign is draft",
    ):
        persist_manual_reactivation_selection(
            campaign_id="p6-f-12-test-001",
            campaign_name="P6-F.12 controlled test",
            selection=_eligible_selection(),
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
        )

    assert contact_repository.create_calls == 0


from app.models.reactivation_campaign import (
    ReactivationCampaign,
    ReactivationCampaignStatus,
)


class _FakeLifecycleCampaignRepository:
    def __init__(self, campaign):
        self.campaign = campaign
        self.transition_calls = []

    def get_by_id(self, campaign_id):
        if self.campaign is None:
            return None
        if self.campaign.id != campaign_id:
            return None
        return self.campaign

    def transition_status(
        self,
        *,
        campaign_id,
        expected_status,
        next_status,
    ):
        if self.campaign.id != campaign_id:
            raise AssertionError("campaign mismatch")

        if self.campaign.status != expected_status:
            raise AssertionError("unexpected current status")

        self.transition_calls.append(
            (
                expected_status,
                next_status,
            )
        )

        self.campaign = self.campaign.model_copy(
            update={
                "status": next_status,
            }
        )

        return self.campaign


def _lifecycle_campaign(status):
    return ReactivationCampaign(
        id="p6-f-12-test-001",
        name="P6-F.12 controlled test",
        template_name="reactivacion_respirarte",
        template_language="es_CO",
        status=status,
    )


def test_manual_campaign_activation_advances_draft_ready_active():
    from app.services.reactivation_manual_trigger import (
        activate_manual_reactivation_campaign,
    )

    repository = _FakeLifecycleCampaignRepository(
        _lifecycle_campaign(
            ReactivationCampaignStatus.DRAFT
        )
    )

    result = activate_manual_reactivation_campaign(
        campaign_id="p6-f-12-test-001",
        campaign_repository=repository,
    )

    assert result.status == ReactivationCampaignStatus.ACTIVE
    assert repository.transition_calls == [
        (
            ReactivationCampaignStatus.DRAFT,
            ReactivationCampaignStatus.READY,
        ),
        (
            ReactivationCampaignStatus.READY,
            ReactivationCampaignStatus.ACTIVE,
        ),
    ]


def test_manual_campaign_activation_advances_ready_to_active():
    from app.services.reactivation_manual_trigger import (
        activate_manual_reactivation_campaign,
    )

    repository = _FakeLifecycleCampaignRepository(
        _lifecycle_campaign(
            ReactivationCampaignStatus.READY
        )
    )

    result = activate_manual_reactivation_campaign(
        campaign_id="p6-f-12-test-001",
        campaign_repository=repository,
    )

    assert result.status == ReactivationCampaignStatus.ACTIVE
    assert repository.transition_calls == [
        (
            ReactivationCampaignStatus.READY,
            ReactivationCampaignStatus.ACTIVE,
        ),
    ]


def test_manual_campaign_activation_is_idempotent_when_active():
    from app.services.reactivation_manual_trigger import (
        activate_manual_reactivation_campaign,
    )

    repository = _FakeLifecycleCampaignRepository(
        _lifecycle_campaign(
            ReactivationCampaignStatus.ACTIVE
        )
    )

    result = activate_manual_reactivation_campaign(
        campaign_id="p6-f-12-test-001",
        campaign_repository=repository,
    )

    assert result.status == ReactivationCampaignStatus.ACTIVE
    assert repository.transition_calls == []


def test_manual_campaign_activation_refuses_terminal_state():
    from app.services.reactivation_manual_trigger import (
        activate_manual_reactivation_campaign,
    )

    repository = _FakeLifecycleCampaignRepository(
        _lifecycle_campaign(
            ReactivationCampaignStatus.CANCELLED
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot be activated",
    ):
        activate_manual_reactivation_campaign(
            campaign_id="p6-f-12-test-001",
            campaign_repository=repository,
        )

    assert repository.transition_calls == []
