from __future__ import annotations

import hashlib
import re
import unicodedata
from enum import Enum

from pydantic import BaseModel, field_serializer

from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationCampaignStatus,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
    ReactivationEligibilityDecision,
    ReactivationEligibilityInput,
    ReactivationExclusionReason,
)


class InvalidReactivationCampaignTransition(ValueError):
    pass


class InvalidReactivationContactTransition(ValueError):
    pass


_CAMPAIGN_TRANSITIONS: dict[
    ReactivationCampaignStatus,
    frozenset[ReactivationCampaignStatus],
] = {
    ReactivationCampaignStatus.DRAFT: frozenset(
        {
            ReactivationCampaignStatus.READY,
            ReactivationCampaignStatus.CANCELLED,
        }
    ),
    ReactivationCampaignStatus.READY: frozenset(
        {
            ReactivationCampaignStatus.ACTIVE,
            ReactivationCampaignStatus.CANCELLED,
        }
    ),
    ReactivationCampaignStatus.ACTIVE: frozenset(
        {
            ReactivationCampaignStatus.PAUSED,
            ReactivationCampaignStatus.COMPLETED,
            ReactivationCampaignStatus.CANCELLED,
        }
    ),
    ReactivationCampaignStatus.PAUSED: frozenset(
        {
            ReactivationCampaignStatus.ACTIVE,
            ReactivationCampaignStatus.COMPLETED,
            ReactivationCampaignStatus.CANCELLED,
        }
    ),
    ReactivationCampaignStatus.COMPLETED: frozenset(),
    ReactivationCampaignStatus.CANCELLED: frozenset(),
}


_CONTACT_TRANSITIONS: dict[
    ReactivationContactStatus,
    frozenset[ReactivationContactStatus],
] = {
    ReactivationContactStatus.STAGED: frozenset(
        {
            ReactivationContactStatus.ELIGIBLE,
            ReactivationContactStatus.EXCLUDED,
        }
    ),
    ReactivationContactStatus.EXCLUDED: frozenset(),
    ReactivationContactStatus.ELIGIBLE: frozenset(
        {
            ReactivationContactStatus.PENDING,
            ReactivationContactStatus.EXCLUDED,
            ReactivationContactStatus.OPTED_OUT,
        }
    ),
    ReactivationContactStatus.PENDING: frozenset(
        {
            ReactivationContactStatus.ACCEPTED,
            ReactivationContactStatus.FAILED,
            ReactivationContactStatus.OPTED_OUT,
        }
    ),
    ReactivationContactStatus.ACCEPTED: frozenset(
        {
            ReactivationContactStatus.SENT,
            ReactivationContactStatus.DELIVERED,
            ReactivationContactStatus.READ,
            ReactivationContactStatus.FAILED,
            ReactivationContactStatus.OPTED_OUT,
        }
    ),
    ReactivationContactStatus.SENT: frozenset(
        {
            ReactivationContactStatus.DELIVERED,
            ReactivationContactStatus.READ,
            ReactivationContactStatus.FAILED,
            ReactivationContactStatus.OPTED_OUT,
        }
    ),
    ReactivationContactStatus.DELIVERED: frozenset(
        {
            ReactivationContactStatus.READ,
            ReactivationContactStatus.OPTED_OUT,
        }
    ),
    ReactivationContactStatus.READ: frozenset(
        {
            ReactivationContactStatus.OPTED_OUT,
        }
    ),
    ReactivationContactStatus.FAILED: frozenset(
        {
            ReactivationContactStatus.PENDING,
            ReactivationContactStatus.ACCEPTED,
            ReactivationContactStatus.SENT,
            ReactivationContactStatus.DELIVERED,
            ReactivationContactStatus.READ,
            ReactivationContactStatus.EXCLUDED,
            ReactivationContactStatus.OPTED_OUT,
        }
    ),
    ReactivationContactStatus.OPTED_OUT: frozenset(),
}


_PROVIDER_PROGRESS_RANK: dict[ReactivationContactStatus, int] = {
    ReactivationContactStatus.PENDING: 0,
    ReactivationContactStatus.ACCEPTED: 1,
    ReactivationContactStatus.SENT: 2,
    ReactivationContactStatus.DELIVERED: 3,
    ReactivationContactStatus.READ: 4,
}


_COMMITTED_SEND_STATUSES = frozenset(
    {
        ReactivationContactStatus.ACCEPTED,
        ReactivationContactStatus.SENT,
        ReactivationContactStatus.DELIVERED,
        ReactivationContactStatus.READ,
    }
)


_ALLOWED_PHONE_CHARACTERS = re.compile(r"^[0-9+()\s.\-]+$")


def _campaign_status(
    value: ReactivationCampaignStatus | str,
) -> ReactivationCampaignStatus:
    return ReactivationCampaignStatus(value)


def _contact_status(
    value: ReactivationContactStatus | str,
) -> ReactivationContactStatus:
    return ReactivationContactStatus(value)


def is_valid_campaign_transition(
    current_status: ReactivationCampaignStatus | str,
    next_status: ReactivationCampaignStatus | str,
) -> bool:
    try:
        current = _campaign_status(current_status)
        target = _campaign_status(next_status)
    except ValueError:
        return False

    return target in _CAMPAIGN_TRANSITIONS[current]


def validate_campaign_transition(
    current_status: ReactivationCampaignStatus | str,
    next_status: ReactivationCampaignStatus | str,
) -> None:
    if is_valid_campaign_transition(current_status, next_status):
        return

    raise InvalidReactivationCampaignTransition(
        "Invalid reactivation campaign transition: "
        f"{current_status!s} -> {next_status!s}"
    )


def is_valid_contact_transition(
    current_status: ReactivationContactStatus | str,
    next_status: ReactivationContactStatus | str,
) -> bool:
    try:
        current = _contact_status(current_status)
        target = _contact_status(next_status)
    except ValueError:
        return False

    return target in _CONTACT_TRANSITIONS[current]


def validate_contact_transition(
    current_status: ReactivationContactStatus | str,
    next_status: ReactivationContactStatus | str,
) -> None:
    if is_valid_contact_transition(current_status, next_status):
        return

    raise InvalidReactivationContactTransition(
        "Invalid reactivation contact transition: "
        f"{current_status!s} -> {next_status!s}"
    )


def reduce_reactivation_provider_status(
    *,
    current_status: ReactivationContactStatus | str,
    provider_status: ReactivationContactStatus | str,
) -> ReactivationContactStatus:
    current = _contact_status(current_status)
    incoming = _contact_status(provider_status)

    supported_provider_statuses = {
        ReactivationContactStatus.ACCEPTED,
        ReactivationContactStatus.SENT,
        ReactivationContactStatus.DELIVERED,
        ReactivationContactStatus.READ,
        ReactivationContactStatus.FAILED,
    }
    if incoming not in supported_provider_statuses:
        raise ValueError(
            f"Unsupported provider status: {provider_status!s}"
        )

    if current in {
        ReactivationContactStatus.EXCLUDED,
        ReactivationContactStatus.OPTED_OUT,
    }:
        return current

    if incoming == ReactivationContactStatus.FAILED:
        if current in {
            ReactivationContactStatus.DELIVERED,
            ReactivationContactStatus.READ,
        }:
            return current
        return ReactivationContactStatus.FAILED

    current_rank = _PROVIDER_PROGRESS_RANK.get(current)
    incoming_rank = _PROVIDER_PROGRESS_RANK[incoming]

    if current_rank is not None and current_rank > incoming_rank:
        return current

    return incoming


def has_committed_commercial_send(
    *,
    status: ReactivationContactStatus | str,
    provider_message_id: str | None,
) -> bool:
    current = _contact_status(status)

    if provider_message_id and provider_message_id.strip():
        return True

    return current in _COMMITTED_SEND_STATUSES


def can_attempt_commercial_send(
    *,
    status: ReactivationContactStatus | str,
    retryable: bool,
    provider_message_id: str | None,
) -> bool:
    current = _contact_status(status)

    if has_committed_commercial_send(
        status=current,
        provider_message_id=provider_message_id,
    ):
        return False

    if current == ReactivationContactStatus.ELIGIBLE:
        return True

    return (
        current == ReactivationContactStatus.FAILED
        and retryable is True
    )


def build_reactivation_idempotency_key(
    *,
    campaign_id: str,
    phone_e164: str,
) -> str:
    normalized_campaign_id = campaign_id.strip()
    normalized_phone = phone_e164.strip()

    if not normalized_campaign_id:
        raise ValueError("campaign_id is required")

    if not re.fullmatch(r"\d{8,15}", normalized_phone):
        raise ValueError("phone_e164 must contain 8 to 15 digits")

    source = f"{normalized_campaign_id}:{normalized_phone}"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()

    return f"reactivation:{digest}"


def _normalize_country_code(
    default_country_code: str | None,
) -> str | None:
    if default_country_code is None:
        return None

    value = default_country_code.strip()
    if not value:
        return None

    if value.startswith("+"):
        value = value[1:]
    elif value.startswith("00"):
        value = value[2:]

    if not value.isdigit():
        return None

    if not 1 <= len(value) <= 3:
        return None

    if value.startswith("0"):
        return None

    return value


def normalize_reactivation_phone_e164(
    raw_phone: str | None,
    *,
    default_country_code: str | None,
) -> str | None:
    if raw_phone is None:
        return None

    value = str(raw_phone).strip()
    if not value:
        return None

    if not _ALLOWED_PHONE_CHARACTERS.fullmatch(value):
        return None

    if value.count("+") > 1:
        return None

    if "+" in value and not value.startswith("+"):
        return None

    explicitly_international = value.startswith("+") or value.startswith(
        "00"
    )

    digits = re.sub(r"\D", "", value)

    if value.startswith("00"):
        if not digits.startswith("00"):
            return None
        digits = digits[2:]

    if not explicitly_international and len(digits) == 10:
        country_code = _normalize_country_code(default_country_code)
        if country_code is None:
            return None
        digits = f"{country_code}{digits}"

    if not digits.isdigit():
        return None

    if not 8 <= len(digits) <= 15:
        return None

    if digits.startswith("0"):
        return None

    return digits


def evaluate_reactivation_eligibility(
    eligibility: ReactivationEligibilityInput,
) -> ReactivationEligibilityDecision:
    reasons: list[ReactivationExclusionReason] = []

    if not eligibility.phone_e164:
        reasons.append(
            ReactivationExclusionReason.INVALID_PHONE
        )

    if eligibility.duplicate_in_campaign:
        reasons.append(
            ReactivationExclusionReason.DUPLICATE_PHONE
        )

    if not eligibility.attended:
        reasons.append(
            ReactivationExclusionReason.NOT_ATTENDED
        )

    if (
        eligibility.authorization_status
        == ReactivationAuthorizationStatus.PENDING
    ):
        reasons.append(
            ReactivationExclusionReason.AUTHORIZATION_PENDING
        )
    elif (
        eligibility.authorization_status
        == ReactivationAuthorizationStatus.DENIED
    ):
        reasons.append(
            ReactivationExclusionReason.AUTHORIZATION_DENIED
        )

    if (
        eligibility.doctor_review_status
        == ReactivationDoctorReviewStatus.PENDING
    ):
        reasons.append(
            ReactivationExclusionReason.DOCTOR_REVIEW_PENDING
        )
    elif (
        eligibility.doctor_review_status
        == ReactivationDoctorReviewStatus.EXCLUDED
    ):
        reasons.append(
            ReactivationExclusionReason.DOCTOR_EXCLUDED
        )

    if eligibility.patient_opt_out:
        reasons.append(
            ReactivationExclusionReason.EXISTING_OPT_OUT
        )

    if eligibility.prior_complaint:
        reasons.append(
            ReactivationExclusionReason.PRIOR_COMPLAINT
        )

    if eligibility.sensitive_case:
        reasons.append(
            ReactivationExclusionReason.SENSITIVE_CASE
        )

    if (
        eligibility.representative_number
        and not eligibility.representative_confirmed
    ):
        reasons.append(
            ReactivationExclusionReason.UNCONFIRMED_REPRESENTATIVE
        )

    if eligibility.already_processed:
        reasons.append(
            ReactivationExclusionReason.ALREADY_PROCESSED
        )

    return ReactivationEligibilityDecision(
        eligible=not reasons,
        exclusion_reasons=tuple(reasons),
    )


class ReactivationResponseSafeReason(str, Enum):
    EXPLICIT_REFUSAL = "explicit_refusal"
    STOP_CONTACT_REQUEST = "stop_contact_request"
    HOSTILE_REJECTION = "hostile_rejection"
    PRIVACY_OBJECTION = "privacy_objection"


class ReactivationResponseSemanticDecision(BaseModel):
    is_opt_out: bool
    safe_reason: ReactivationResponseSafeReason | None = None
    complaint_detected: bool = False
    requires_human_escalation: bool = False

    @field_serializer("safe_reason")
    def serialize_safe_reason(
        self,
        value: ReactivationResponseSafeReason | None,
    ) -> str | None:
        return value.value if value is not None else None


def _normalize_reactivation_response_text(
    message: str | None,
) -> str:
    if not message:
        return ""

    normalized = unicodedata.normalize("NFKD", str(message))
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    normalized = normalized.lower()

    normalized = re.sub(
        r"[^a-z0-9\s]",
        " ",
        normalized,
    )
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def _matches_any_pattern(
    message: str,
    patterns: tuple[str, ...],
) -> bool:
    return any(
        re.search(pattern, message)
        for pattern in patterns
    )


def classify_reactivation_response_semantics(
    message: str | None,
    *,
    reactivation_context: bool,
) -> ReactivationResponseSemanticDecision:
    """
    Classify only safe commercial-response semantics.

    The raw message is intentionally not copied into the returned model.
    Soft refusals become opt-out only when the caller confirms that the
    message is a response to a reactivation campaign.
    """

    normalized = _normalize_reactivation_response_text(message)

    complaint_patterns = (
        r"\bservicio fue malo\b",
        r"\btengo una queja\b",
        r"\bqueja\b",
        r"\bme cobraron\b",
        r"\bcobro incorrecto\b",
        r"\binconformidad\b",
        r"\bhablar con la doctora\b",
        r"\bhablar con un humano\b",
    )

    privacy_patterns = (
        r"\bno (?:autorizo|autirizo) estos mensajes\b",
        r"\bno (?:autorizo|autirizo) mensajes\b",
        r"\bno (?:autorizo|autirizo) el contacto\b",
        r"\bde donde sacaron mis datos\b",
        r"\bno autorice\b.*\bmensajes\b",
        r"\bno tienen autorizacion\b",
    )

    hostile_patterns = (
        r"\bdejen de molestar\b",
        r"\bdejenme quiet[oa]\b",
        r"\bno jodan\b",
        r"\bque fastidio\b",
        r"\bfastidio\b.*\bno vuelvan\b",
        r"\bvayanse al carajo\b",
    )

    stop_contact_patterns = (
        r"\bno me escri(?:ban|van)\b",
        r"\bno me contacten\b",
        r"\bno vuelvan a escribir(?:me)?\b",
        r"\bno vuelvan a contactar(?:me)?\b",
        r"\bno me vuelvan a escribir\b",
        r"\bno me vuelvan a contactar\b",
        r"\bno quiero que me escriban\b",
        r"\bno quiero que me contacten\b",
        r"\bdejenme en paz\b",
        r"\b(?:eliminen|eliminar|borren|borrenme)\b.*\bnumero\b",
        r"\b(?:eliminen|eliminar|borren|borrenme)\b.*\blista\b",
        r"\bborrenme d la lista\b",
        r"\bsaquenme de (?:su|la) lista\b",
        r"\bno msj(?:s)?(?: porfa)?\b",
        r"\bno mas msj(?:s)?\b",
    )

    explicit_refusal_patterns = (
        r"\bno quiero recibir\b",
        r"\bno deseo mas mensajes\b",
        r"\bno quiero mas mensajes\b",
        r"\bno mas mensajes\b",
        r"\bno quiero recibir publicidad\b",
        r"\bno deseo recibir publicidad\b",
        r"\bcancelar mensajes\b",
        r"\bdarme de baja\b",
        r"\bdejar de recibir\b",
        r"\bopt ?out\b",
    )

    soft_refusal_patterns = (
        r"^no gracias$",
        r"^no me interesa$",
        r"^gracias pero no$",
        r"^paso$",
        r"^no deseo el servicio$",
        r"\bno gracias\b.*\bno me interesa\b",
    )

    complaint_detected = _matches_any_pattern(
        normalized,
        complaint_patterns,
    )
    privacy_objection = _matches_any_pattern(
        normalized,
        privacy_patterns,
    )
    hostile_rejection = _matches_any_pattern(
        normalized,
        hostile_patterns,
    )
    stop_contact_request = _matches_any_pattern(
        normalized,
        stop_contact_patterns,
    )
    explicit_refusal = _matches_any_pattern(
        normalized,
        explicit_refusal_patterns,
    )
    soft_refusal = (
        reactivation_context
        and _matches_any_pattern(
            normalized,
            soft_refusal_patterns,
        )
    )

    safe_reason: ReactivationResponseSafeReason | None = None

    if hostile_rejection:
        safe_reason = (
            ReactivationResponseSafeReason.HOSTILE_REJECTION
        )
    elif privacy_objection:
        safe_reason = (
            ReactivationResponseSafeReason.PRIVACY_OBJECTION
        )
    elif stop_contact_request:
        safe_reason = (
            ReactivationResponseSafeReason.STOP_CONTACT_REQUEST
        )
    elif explicit_refusal or soft_refusal:
        safe_reason = (
            ReactivationResponseSafeReason.EXPLICIT_REFUSAL
        )

    return ReactivationResponseSemanticDecision(
        is_opt_out=safe_reason is not None,
        safe_reason=safe_reason,
        complaint_detected=complaint_detected,
        requires_human_escalation=complaint_detected,
    )
