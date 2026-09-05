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
