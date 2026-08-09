from types import SimpleNamespace

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.models.reactivation_campaign import ReactivationContactStatus
from app.services.reactivation_dry_run_context import (
    ReactivationDryRunContextResolver,
)


def make_record(
    *,
    row_number=2,
    source_reference="hist-001",
    phone_original="300 000 0001",
):
    return ReactivationSheetRecord(
        row_number=row_number,
        source_reference=source_reference,
        name="Paciente Control",
        phone_original=phone_original,
        attended="SI",
        authorization_status="SI",
        phone_e164="",
        doctor_review_status="APROBADO",
        exclusion_reason="",
        reactivation_status="",
        observations="",
    )


class FakePatientLookup:
    def __init__(self, patients=None):
        self.patients = patients or {}
        self.calls = []

    def __call__(self, phone_e164):
        self.calls.append(phone_e164)
        return self.patients.get(phone_e164)


class FakeCampaignContactLookup:
    def __init__(self, contacts=None):
        self.contacts = contacts or {}
        self.calls = []

    def __call__(self, campaign_id, phone_e164):
        self.calls.append((campaign_id, phone_e164))
        return self.contacts.get((campaign_id, phone_e164))


def build_resolver(
    *,
    patient_lookup=None,
    contact_lookup=None,
):
    return ReactivationDryRunContextResolver(
        campaign_id="campaign-1",
        default_country_code="57",
        patient_lookup=patient_lookup or FakePatientLookup(),
        campaign_contact_lookup=(
            contact_lookup or FakeCampaignContactLookup()
        ),
    )


def test_resolves_clean_context_with_normalized_phone_read_only_lookups():
    patients = FakePatientLookup()
    contacts = FakeCampaignContactLookup()
    resolver = build_resolver(
        patient_lookup=patients,
        contact_lookup=contacts,
    )

    context = resolver(make_record())

    assert context.duplicate_in_campaign is False
    assert context.patient_opt_out is False
    assert context.prior_complaint is False
    assert context.sensitive_case is False
    assert context.representative_number is False
    assert context.representative_confirmed is False
    assert context.already_processed is False

    assert patients.calls == ["573000000001"]
    assert contacts.calls == [
        ("campaign-1", "573000000001"),
    ]


def test_existing_patient_opt_out_is_exposed_to_domain_context():
    patients = FakePatientLookup(
        {
            "573000000001": SimpleNamespace(
                opt_out=True,
            )
        }
    )
    resolver = build_resolver(
        patient_lookup=patients,
    )

    context = resolver(make_record())

    assert context.patient_opt_out is True


def test_second_occurrence_of_phone_in_same_batch_is_duplicate():
    resolver = build_resolver()

    first = resolver(
        make_record(
            row_number=2,
            source_reference="hist-001",
            phone_original="300 000 0001",
        )
    )
    second = resolver(
        make_record(
            row_number=3,
            source_reference="hist-002",
            phone_original="+57 300 000 0001",
        )
    )

    assert first.duplicate_in_campaign is False
    assert second.duplicate_in_campaign is True


def test_existing_different_source_reference_is_duplicate_in_campaign():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-other",
                status=ReactivationContactStatus.ELIGIBLE,
                provider_message_id=None,
            )
        }
    )
    resolver = build_resolver(
        contact_lookup=contacts,
    )

    context = resolver(
        make_record(
            source_reference="hist-001",
        )
    )

    assert context.duplicate_in_campaign is True
    assert context.already_processed is False


def test_same_source_reference_is_idempotent_reimport_not_duplicate():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-001",
                status=ReactivationContactStatus.ELIGIBLE,
                provider_message_id=None,
            )
        }
    )
    resolver = build_resolver(
        contact_lookup=contacts,
    )

    context = resolver(
        make_record(
            source_reference="hist-001",
        )
    )

    assert context.duplicate_in_campaign is False
    assert context.already_processed is False


def test_committed_existing_contact_is_already_processed():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-001",
                status=ReactivationContactStatus.SENT,
                provider_message_id="wamid.control",
            )
        }
    )
    resolver = build_resolver(
        contact_lookup=contacts,
    )

    context = resolver(make_record())

    assert context.duplicate_in_campaign is False
    assert context.already_processed is True


def test_provider_message_id_marks_processing_even_after_failed_status():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-001",
                status=ReactivationContactStatus.FAILED,
                provider_message_id="wamid.ambiguous",
            )
        }
    )
    resolver = build_resolver(
        contact_lookup=contacts,
    )

    context = resolver(make_record())

    assert context.already_processed is True


def test_invalid_phone_does_not_query_external_state():
    patients = FakePatientLookup()
    contacts = FakeCampaignContactLookup()
    resolver = build_resolver(
        patient_lookup=patients,
        contact_lookup=contacts,
    )

    context = resolver(
        make_record(
            phone_original="telefono-invalido",
        )
    )

    assert context.duplicate_in_campaign is False
    assert context.patient_opt_out is False
    assert context.already_processed is False

    assert patients.calls == []
    assert contacts.calls == []


def test_same_source_pending_contact_is_already_processed():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-001",
                status=ReactivationContactStatus.PENDING,
                provider_message_id=None,
                retryable=False,
            )
        }
    )
    resolver = build_resolver(contact_lookup=contacts)

    context = resolver(make_record())

    assert context.duplicate_in_campaign is False
    assert context.already_processed is True


def test_same_source_opted_out_contact_is_blocked():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-001",
                status=ReactivationContactStatus.OPTED_OUT,
                provider_message_id=None,
                retryable=False,
            )
        }
    )
    resolver = build_resolver(contact_lookup=contacts)

    context = resolver(make_record())

    assert context.duplicate_in_campaign is False
    assert context.already_processed is True


def test_same_source_non_retryable_failed_contact_is_already_processed():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-001",
                status=ReactivationContactStatus.FAILED,
                provider_message_id=None,
                retryable=False,
            )
        }
    )
    resolver = build_resolver(contact_lookup=contacts)

    context = resolver(make_record())

    assert context.duplicate_in_campaign is False
    assert context.already_processed is True


def test_same_source_retryable_failed_without_wamid_remains_retryable():
    contacts = FakeCampaignContactLookup(
        {
            (
                "campaign-1",
                "573000000001",
            ): SimpleNamespace(
                source_reference="hist-001",
                status=ReactivationContactStatus.FAILED,
                provider_message_id=None,
                retryable=True,
            )
        }
    )
    resolver = build_resolver(contact_lookup=contacts)

    context = resolver(make_record())

    assert context.duplicate_in_campaign is False
    assert context.already_processed is False
