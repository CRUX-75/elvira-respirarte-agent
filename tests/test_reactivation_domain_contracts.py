import pytest

from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationCampaign,
    ReactivationCampaignContact,
    ReactivationCampaignStatus,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
    ReactivationEligibilityInput,
    ReactivationExclusionReason,
)
from app.services.reactivation_domain import (
    InvalidReactivationCampaignTransition,
    InvalidReactivationContactTransition,
    build_reactivation_idempotency_key,
    can_attempt_commercial_send,
    evaluate_reactivation_eligibility,
    has_committed_commercial_send,
    is_valid_campaign_transition,
    is_valid_contact_transition,
    normalize_reactivation_phone_e164,
    reduce_reactivation_provider_status,
    validate_campaign_transition,
    validate_contact_transition,
)


def build_eligible_input(**overrides):
    values = {
        "phone_e164": "573000000001",
        "attended": True,
        "authorization_status": (
            ReactivationAuthorizationStatus.APPROVED
        ),
        "doctor_review_status": (
            ReactivationDoctorReviewStatus.APPROVED
        ),
        "duplicate_in_campaign": False,
        "patient_opt_out": False,
        "prior_complaint": False,
        "sensitive_case": False,
        "representative_number": False,
        "representative_confirmed": False,
        "already_processed": False,
    }
    values.update(overrides)
    return ReactivationEligibilityInput(**values)


def test_campaign_status_contract_is_explicit():
    assert {
        status.value for status in ReactivationCampaignStatus
    } == {
        "draft",
        "ready",
        "active",
        "paused",
        "completed",
        "cancelled",
    }


def test_contact_status_contract_is_explicit():
    assert {
        status.value for status in ReactivationContactStatus
    } == {
        "staged",
        "excluded",
        "eligible",
        "pending",
        "accepted",
        "sent",
        "delivered",
        "read",
        "failed",
        "opted_out",
    }


def test_campaign_defaults_to_draft_and_colombian_template():
    campaign = ReactivationCampaign(
        id="campaign-1",
        name="reactivacion_historica_2026",
        template_name="reactivacion_respirarte",
    )

    assert campaign.status == ReactivationCampaignStatus.DRAFT
    assert campaign.template_language == "es_CO"


def test_contact_defaults_to_staged_without_delivery_commitment():
    contact = ReactivationCampaignContact(
        id="contact-1",
        campaign_id="campaign-1",
        source_reference="historico-001",
        name="Paciente de prueba",
        phone_original="300 000 0001",
        phone_e164="573000000001",
    )

    assert contact.status == ReactivationContactStatus.STAGED
    assert contact.exclusion_reasons == ()
    assert contact.provider_message_id is None
    assert contact.retryable is False


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        ("draft", "ready"),
        ("draft", "cancelled"),
        ("ready", "active"),
        ("ready", "cancelled"),
        ("active", "paused"),
        ("active", "completed"),
        ("active", "cancelled"),
        ("paused", "active"),
        ("paused", "completed"),
        ("paused", "cancelled"),
    ],
)
def test_campaign_allows_valid_transitions(
    current_status,
    next_status,
):
    assert is_valid_campaign_transition(
        current_status,
        next_status,
    ) is True
    validate_campaign_transition(current_status, next_status)


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        ("draft", "active"),
        ("completed", "active"),
        ("completed", "ready"),
        ("cancelled", "active"),
        ("cancelled", "ready"),
    ],
)
def test_campaign_rejects_invalid_transitions(
    current_status,
    next_status,
):
    assert is_valid_campaign_transition(
        current_status,
        next_status,
    ) is False

    with pytest.raises(
        InvalidReactivationCampaignTransition
    ):
        validate_campaign_transition(
            current_status,
            next_status,
        )


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        ("staged", "eligible"),
        ("staged", "excluded"),
        ("eligible", "pending"),
        ("eligible", "excluded"),
        ("eligible", "opted_out"),
        ("pending", "accepted"),
        ("pending", "failed"),
        ("pending", "opted_out"),
        ("failed", "pending"),
        ("failed", "excluded"),
        ("failed", "opted_out"),
        ("accepted", "sent"),
        ("accepted", "delivered"),
        ("accepted", "read"),
        ("accepted", "failed"),
        ("accepted", "opted_out"),
        ("sent", "delivered"),
        ("sent", "read"),
        ("sent", "failed"),
        ("sent", "opted_out"),
        ("delivered", "read"),
        ("delivered", "opted_out"),
        ("read", "opted_out"),
        ("failed", "sent"),
        ("failed", "delivered"),
        ("failed", "read"),
    ],
)
def test_contact_allows_valid_transitions(
    current_status,
    next_status,
):
    assert is_valid_contact_transition(
        current_status,
        next_status,
    ) is True
    validate_contact_transition(current_status, next_status)


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        ("accepted", "pending"),
        ("sent", "pending"),
        ("delivered", "pending"),
        ("read", "pending"),
        ("excluded", "eligible"),
        ("opted_out", "eligible"),
        ("opted_out", "pending"),
    ],
)
def test_contact_rejects_duplicate_enabling_transitions(
    current_status,
    next_status,
):
    assert is_valid_contact_transition(
        current_status,
        next_status,
    ) is False

    with pytest.raises(
        InvalidReactivationContactTransition
    ):
        validate_contact_transition(
            current_status,
            next_status,
        )


@pytest.mark.parametrize(
    ("current_status", "provider_status", "expected"),
    [
        ("pending", "accepted", "accepted"),
        ("accepted", "sent", "sent"),
        ("accepted", "delivered", "delivered"),
        ("sent", "read", "read"),
        ("delivered", "sent", "delivered"),
        ("read", "delivered", "read"),
        ("delivered", "delivered", "delivered"),
        ("failed", "delivered", "delivered"),
        ("accepted", "failed", "failed"),
        ("read", "failed", "read"),
    ],
)
def test_provider_status_reducer_is_repeatable_and_monotonic(
    current_status,
    provider_status,
    expected,
):
    assert reduce_reactivation_provider_status(
        current_status=current_status,
        provider_status=provider_status,
    ) == ReactivationContactStatus(expected)


@pytest.mark.parametrize(
    "status",
    [
        ReactivationContactStatus.ACCEPTED,
        ReactivationContactStatus.SENT,
        ReactivationContactStatus.DELIVERED,
        ReactivationContactStatus.READ,
    ],
)
def test_provider_committed_statuses_block_second_message(status):
    assert has_committed_commercial_send(
        status=status,
        provider_message_id=None,
    ) is True

    assert can_attempt_commercial_send(
        status=status,
        retryable=True,
        provider_message_id=None,
    ) is False


def test_provider_message_id_blocks_retry_even_when_status_is_failed():
    assert has_committed_commercial_send(
        status=ReactivationContactStatus.FAILED,
        provider_message_id="wamid.reactivation.001",
    ) is True

    assert can_attempt_commercial_send(
        status=ReactivationContactStatus.FAILED,
        retryable=True,
        provider_message_id="wamid.reactivation.001",
    ) is False


def test_pre_acceptance_retryable_failure_can_retry_same_contact():
    assert has_committed_commercial_send(
        status=ReactivationContactStatus.FAILED,
        provider_message_id=None,
    ) is False

    assert can_attempt_commercial_send(
        status=ReactivationContactStatus.FAILED,
        retryable=True,
        provider_message_id=None,
    ) is True


def test_non_retryable_failure_cannot_retry():
    assert can_attempt_commercial_send(
        status=ReactivationContactStatus.FAILED,
        retryable=False,
        provider_message_id=None,
    ) is False


def test_only_eligible_contact_can_begin_first_attempt():
    assert can_attempt_commercial_send(
        status=ReactivationContactStatus.ELIGIBLE,
        retryable=False,
        provider_message_id=None,
    ) is True

    assert can_attempt_commercial_send(
        status=ReactivationContactStatus.PENDING,
        retryable=False,
        provider_message_id=None,
    ) is False

    assert can_attempt_commercial_send(
        status=ReactivationContactStatus.EXCLUDED,
        retryable=False,
        provider_message_id=None,
    ) is False

    assert can_attempt_commercial_send(
        status=ReactivationContactStatus.OPTED_OUT,
        retryable=False,
        provider_message_id=None,
    ) is False


def test_idempotency_key_is_stable_per_campaign_and_phone():
    first = build_reactivation_idempotency_key(
        campaign_id="campaign-1",
        phone_e164="573000000001",
    )
    repeated = build_reactivation_idempotency_key(
        campaign_id="campaign-1",
        phone_e164="573000000001",
    )
    another_campaign = build_reactivation_idempotency_key(
        campaign_id="campaign-2",
        phone_e164="573000000001",
    )
    another_phone = build_reactivation_idempotency_key(
        campaign_id="campaign-1",
        phone_e164="573000000002",
    )

    assert first == repeated
    assert first != another_campaign
    assert first != another_phone


@pytest.mark.parametrize(
    ("raw_phone", "expected"),
    [
        ("+57 300 000 0001", "573000000001"),
        ("00 57 300 000 0001", "573000000001"),
        ("57 300 000 0001", "573000000001"),
        ("3000000001", "573000000001"),
        ("(300) 000-0001", "573000000001"),
        ("+1 (202) 555-0110", "12025550110"),
        ("12025550110", "12025550110"),
    ],
)
def test_phone_normalization_returns_canonical_e164_digits(
    raw_phone,
    expected,
):
    assert normalize_reactivation_phone_e164(
        raw_phone,
        default_country_code="57",
    ) == expected


@pytest.mark.parametrize(
    "raw_phone",
    [
        None,
        "",
        "123",
        "300ABC0001",
        "3000000001 ext 4",
        "1234567890123456",
    ],
)
def test_phone_normalization_rejects_invalid_values(raw_phone):
    assert normalize_reactivation_phone_e164(
        raw_phone,
        default_country_code="57",
    ) is None


def test_local_number_requires_explicit_default_country():
    assert normalize_reactivation_phone_e164(
        "3000000001",
        default_country_code=None,
    ) is None


def test_phone_normalization_is_idempotent():
    canonical = "573000000001"

    assert normalize_reactivation_phone_e164(
        canonical,
        default_country_code="57",
    ) == canonical


def test_fully_approved_contact_is_eligible():
    decision = evaluate_reactivation_eligibility(
        build_eligible_input()
    )

    assert decision.eligible is True
    assert decision.exclusion_reasons == ()


@pytest.mark.parametrize(
    ("overrides", "expected_reason"),
    [
        (
            {"phone_e164": None},
            ReactivationExclusionReason.INVALID_PHONE,
        ),
        (
            {"duplicate_in_campaign": True},
            ReactivationExclusionReason.DUPLICATE_PHONE,
        ),
        (
            {"attended": False},
            ReactivationExclusionReason.NOT_ATTENDED,
        ),
        (
            {
                "authorization_status": (
                    ReactivationAuthorizationStatus.PENDING
                )
            },
            ReactivationExclusionReason.AUTHORIZATION_PENDING,
        ),
        (
            {
                "authorization_status": (
                    ReactivationAuthorizationStatus.DENIED
                )
            },
            ReactivationExclusionReason.AUTHORIZATION_DENIED,
        ),
        (
            {
                "doctor_review_status": (
                    ReactivationDoctorReviewStatus.PENDING
                )
            },
            ReactivationExclusionReason.DOCTOR_REVIEW_PENDING,
        ),
        (
            {
                "doctor_review_status": (
                    ReactivationDoctorReviewStatus.EXCLUDED
                )
            },
            ReactivationExclusionReason.DOCTOR_EXCLUDED,
        ),
        (
            {"patient_opt_out": True},
            ReactivationExclusionReason.EXISTING_OPT_OUT,
        ),
        (
            {"prior_complaint": True},
            ReactivationExclusionReason.PRIOR_COMPLAINT,
        ),
        (
            {"sensitive_case": True},
            ReactivationExclusionReason.SENSITIVE_CASE,
        ),
        (
            {
                "representative_number": True,
                "representative_confirmed": False,
            },
            (
                ReactivationExclusionReason
                .UNCONFIRMED_REPRESENTATIVE
            ),
        ),
        (
            {"already_processed": True},
            ReactivationExclusionReason.ALREADY_PROCESSED,
        ),
    ],
)
def test_each_safety_rule_excludes_contact(
    overrides,
    expected_reason,
):
    decision = evaluate_reactivation_eligibility(
        build_eligible_input(**overrides)
    )

    assert decision.eligible is False
    assert expected_reason in decision.exclusion_reasons


def test_eligibility_can_return_multiple_safe_reasons():
    decision = evaluate_reactivation_eligibility(
        build_eligible_input(
            patient_opt_out=True,
            prior_complaint=True,
            sensitive_case=True,
        )
    )

    assert decision.eligible is False
    assert set(decision.exclusion_reasons) == {
        ReactivationExclusionReason.EXISTING_OPT_OUT,
        ReactivationExclusionReason.PRIOR_COMPLAINT,
        ReactivationExclusionReason.SENSITIVE_CASE,
    }

    assert all(
        isinstance(reason, ReactivationExclusionReason)
        for reason in decision.exclusion_reasons
    )
