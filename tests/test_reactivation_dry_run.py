import pytest

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.models.reactivation_campaign import (
    ReactivationContactStatus,
    ReactivationExclusionReason,
)
from app.services.reactivation_dry_run import (
    ReactivationDryRunContext,
    ReactivationDryRunInputError,
    evaluate_reactivation_sheet_record,
)


def make_record(**overrides):
    values = {
        "row_number": 2,
        "source_reference": "hist-001",
        "name": "Paciente Control",
        "phone_original": "300 000 0001",
        "attended": "SI",
        "authorization_status": "SI",
        "phone_e164": "",
        "doctor_review_status": "APROBADO",
        "exclusion_reason": "",
        "reactivation_status": "",
        "observations": "",
    }
    values.update(overrides)
    return ReactivationSheetRecord(**values)


def test_fully_approved_sheet_record_is_eligible_and_phone_is_normalized():
    decision = evaluate_reactivation_sheet_record(
        make_record(),
        context=ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert decision.row_number == 2
    assert decision.source_reference == "hist-001"
    assert decision.phone_e164 == "573000000001"
    assert decision.status == ReactivationContactStatus.ELIGIBLE
    assert decision.exclusion_reasons == ()


def test_pending_human_controls_remain_excluded_with_domain_reasons():
    decision = evaluate_reactivation_sheet_record(
        make_record(
            authorization_status="PENDIENTE",
            doctor_review_status="PENDIENTE",
        ),
        context=ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert decision.status == ReactivationContactStatus.EXCLUDED
    assert decision.exclusion_reasons == (
        ReactivationExclusionReason.AUTHORIZATION_PENDING,
        ReactivationExclusionReason.DOCTOR_REVIEW_PENDING,
    )


def test_invalid_phone_and_not_attended_return_multiple_safe_reasons():
    decision = evaluate_reactivation_sheet_record(
        make_record(
            phone_original="telefono-invalido",
            attended="NO",
        ),
        context=ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert decision.phone_e164 is None
    assert decision.status == ReactivationContactStatus.EXCLUDED
    assert decision.exclusion_reasons == (
        ReactivationExclusionReason.INVALID_PHONE,
        ReactivationExclusionReason.NOT_ATTENDED,
    )


def test_denied_authorization_and_doctor_exclusion_map_to_domain_contract():
    decision = evaluate_reactivation_sheet_record(
        make_record(
            authorization_status="NO",
            doctor_review_status="EXCLUIR",
        ),
        context=ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert decision.status == ReactivationContactStatus.EXCLUDED
    assert decision.exclusion_reasons == (
        ReactivationExclusionReason.AUTHORIZATION_DENIED,
        ReactivationExclusionReason.DOCTOR_EXCLUDED,
    )


def test_external_safety_context_is_delegated_to_domain_eligibility():
    decision = evaluate_reactivation_sheet_record(
        make_record(),
        context=ReactivationDryRunContext(
            duplicate_in_campaign=True,
            patient_opt_out=True,
            prior_complaint=True,
            sensitive_case=True,
            representative_number=True,
            representative_confirmed=False,
            already_processed=True,
        ),
        default_country_code="57",
    )

    assert decision.status == ReactivationContactStatus.EXCLUDED
    assert set(decision.exclusion_reasons) == {
        ReactivationExclusionReason.DUPLICATE_PHONE,
        ReactivationExclusionReason.EXISTING_OPT_OUT,
        ReactivationExclusionReason.PRIOR_COMPLAINT,
        ReactivationExclusionReason.SENSITIVE_CASE,
        ReactivationExclusionReason.UNCONFIRMED_REPRESENTATIVE,
        ReactivationExclusionReason.ALREADY_PROCESSED,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("attended", "QUIZA"),
        ("authorization_status", "AUTORIZADO"),
        ("doctor_review_status", "REVISADO"),
    ],
)
def test_unknown_controlled_sheet_values_fail_closed_without_sensitive_data(
    field,
    value,
):
    record = make_record(
        **{
            field: value,
            "name": "Nombre Sensible",
            "phone_original": "300 999 9999",
        }
    )

    with pytest.raises(
        ReactivationDryRunInputError,
        match="Invalid Reactivacion_Historica controlled value",
    ) as exc_info:
        evaluate_reactivation_sheet_record(
            record,
            context=ReactivationDryRunContext(),
            default_country_code="57",
        )

    error = str(exc_info.value)

    assert field in error
    assert "Nombre Sensible" not in error
    assert "300 999 9999" not in error


def test_controlled_sheet_values_are_trimmed_and_case_normalized():
    decision = evaluate_reactivation_sheet_record(
        make_record(
            attended=" si ",
            authorization_status=" si ",
            doctor_review_status=" aprobado ",
        ),
        context=ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert decision.status == ReactivationContactStatus.ELIGIBLE
    assert decision.exclusion_reasons == ()


def test_phone_projection_is_recomputed_from_historical_source():
    decision = evaluate_reactivation_sheet_record(
        make_record(
            phone_original="300 000 0002",
            phone_e164="573009999999",
        ),
        context=ReactivationDryRunContext(),
        default_country_code="57",
    )

    assert decision.phone_e164 == "573000000002"
    assert decision.status == ReactivationContactStatus.ELIGIBLE
