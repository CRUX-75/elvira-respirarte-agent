"""
Pure dry-run evaluation for historical reactivation staging records.

This module translates the approved Reactivacion_Historica controlled
values into the existing reactivation domain contracts.

It does not read or write Google Sheets, persist campaign data, activate
campaigns or call WhatsApp.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
    ReactivationEligibilityInput,
    ReactivationExclusionReason,
)
from app.services.reactivation_domain import (
    evaluate_reactivation_eligibility,
    normalize_reactivation_phone_e164,
)


class ReactivationDryRunInputError(ValueError):
    """Raised when a controlled Sheets value is outside the approved contract."""


@dataclass(frozen=True)
class ReactivationDryRunContext:
    """
    External safety facts required by the existing eligibility domain.

    P6-F.11.6 keeps these inputs explicit so the pure row evaluator does
    not perform database access or infer safety state.
    """

    duplicate_in_campaign: bool = False
    patient_opt_out: bool = False
    prior_complaint: bool = False
    sensitive_case: bool = False
    representative_number: bool = False
    representative_confirmed: bool = False
    already_processed: bool = False


@dataclass(frozen=True)
class ReactivationDryRunDecision:
    """Safe deterministic projection produced for one staging row."""

    row_number: int
    source_reference: str
    phone_e164: str | None
    status: ReactivationContactStatus
    exclusion_reasons: tuple[ReactivationExclusionReason, ...]


def _controlled_value(value: str | None) -> str:
    return str(value or "").strip().upper()


def _invalid_controlled_value(field: str) -> ReactivationDryRunInputError:
    return ReactivationDryRunInputError(
        "Invalid Reactivacion_Historica controlled value "
        f"for field {field}."
    )


def _parse_attended(value: str | None) -> bool:
    normalized = _controlled_value(value)

    if normalized == "SI":
        return True

    if normalized == "NO":
        return False

    raise _invalid_controlled_value("attended")


def _parse_authorization_status(
    value: str | None,
) -> ReactivationAuthorizationStatus:
    normalized = _controlled_value(value)

    mapping = {
        "PENDIENTE": ReactivationAuthorizationStatus.PENDING,
        "SI": ReactivationAuthorizationStatus.APPROVED,
        "NO": ReactivationAuthorizationStatus.DENIED,
    }

    try:
        return mapping[normalized]
    except KeyError as exc:
        raise _invalid_controlled_value(
            "authorization_status"
        ) from exc


def _parse_doctor_review_status(
    value: str | None,
) -> ReactivationDoctorReviewStatus:
    normalized = _controlled_value(value)

    mapping = {
        "PENDIENTE": ReactivationDoctorReviewStatus.PENDING,
        "APROBADO": ReactivationDoctorReviewStatus.APPROVED,
        "EXCLUIR": ReactivationDoctorReviewStatus.EXCLUDED,
    }

    try:
        return mapping[normalized]
    except KeyError as exc:
        raise _invalid_controlled_value(
            "doctor_review_status"
        ) from exc


def evaluate_reactivation_sheet_record(
    record: ReactivationSheetRecord,
    *,
    context: ReactivationDryRunContext,
    default_country_code: str | None,
) -> ReactivationDryRunDecision:
    """
    Evaluate one historical staging row without side effects.

    telefono_e164 is always recalculated from telefono_original. The
    existing system projection in Sheets is never trusted as an input
    to eligibility.
    """

    phone_e164 = normalize_reactivation_phone_e164(
        record.phone_original,
        default_country_code=default_country_code,
    )

    eligibility = ReactivationEligibilityInput(
        phone_e164=phone_e164,
        attended=_parse_attended(record.attended),
        authorization_status=_parse_authorization_status(
            record.authorization_status
        ),
        doctor_review_status=_parse_doctor_review_status(
            record.doctor_review_status
        ),
        duplicate_in_campaign=context.duplicate_in_campaign,
        patient_opt_out=context.patient_opt_out,
        prior_complaint=context.prior_complaint,
        sensitive_case=context.sensitive_case,
        representative_number=context.representative_number,
        representative_confirmed=context.representative_confirmed,
        already_processed=context.already_processed,
    )

    domain_decision = evaluate_reactivation_eligibility(
        eligibility
    )

    status = (
        ReactivationContactStatus.ELIGIBLE
        if domain_decision.eligible
        else ReactivationContactStatus.EXCLUDED
    )

    return ReactivationDryRunDecision(
        row_number=record.row_number,
        source_reference=record.source_reference,
        phone_e164=phone_e164,
        status=status,
        exclusion_reasons=domain_decision.exclusion_reasons,
    )
