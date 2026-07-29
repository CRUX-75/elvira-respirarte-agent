from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReactivationCampaignStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReactivationContactStatus(str, Enum):
    STAGED = "staged"
    EXCLUDED = "excluded"
    ELIGIBLE = "eligible"
    PENDING = "pending"
    ACCEPTED = "accepted"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    OPTED_OUT = "opted_out"


class ReactivationAuthorizationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class ReactivationDoctorReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXCLUDED = "excluded"


class ReactivationExclusionReason(str, Enum):
    INVALID_PHONE = "invalid_phone"
    DUPLICATE_PHONE = "duplicate_phone"
    NOT_ATTENDED = "not_attended"
    AUTHORIZATION_PENDING = "authorization_pending"
    AUTHORIZATION_DENIED = "authorization_denied"
    DOCTOR_REVIEW_PENDING = "doctor_review_pending"
    DOCTOR_EXCLUDED = "doctor_excluded"
    EXISTING_OPT_OUT = "existing_opt_out"
    PRIOR_COMPLAINT = "prior_complaint"
    SENSITIVE_CASE = "sensitive_case"
    UNCONFIRMED_REPRESENTATIVE = "unconfirmed_representative"
    ALREADY_PROCESSED = "already_processed"


class ReactivationCampaign(BaseModel):
    id: str
    name: str
    template_name: str
    template_language: str = "es_CO"
    status: ReactivationCampaignStatus = ReactivationCampaignStatus.DRAFT
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReactivationCampaignContact(BaseModel):
    id: str
    campaign_id: str
    source_reference: str
    name: str | None = None
    phone_original: str | None = None
    phone_e164: str | None = None
    attended: bool | None = None
    authorization_status: ReactivationAuthorizationStatus = (
        ReactivationAuthorizationStatus.PENDING
    )
    doctor_review_status: ReactivationDoctorReviewStatus = (
        ReactivationDoctorReviewStatus.PENDING
    )
    status: ReactivationContactStatus = ReactivationContactStatus.STAGED
    exclusion_reasons: tuple[ReactivationExclusionReason, ...] = Field(
        default_factory=tuple
    )
    idempotency_key: str | None = None
    provider_message_id: str | None = None
    retryable: bool = False
    attempt_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReactivationEligibilityInput(BaseModel):
    phone_e164: str | None
    attended: bool
    authorization_status: ReactivationAuthorizationStatus
    doctor_review_status: ReactivationDoctorReviewStatus
    duplicate_in_campaign: bool
    patient_opt_out: bool
    prior_complaint: bool
    sensitive_case: bool
    representative_number: bool
    representative_confirmed: bool
    already_processed: bool


class ReactivationEligibilityDecision(BaseModel):
    eligible: bool
    exclusion_reasons: tuple[ReactivationExclusionReason, ...] = Field(
        default_factory=tuple
    )
