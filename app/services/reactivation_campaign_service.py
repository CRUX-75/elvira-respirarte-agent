from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.models.reactivation_campaign import (
    ReactivationCampaignContact,
)
from app.services.reactivation_domain import decide_reactivation_response


@dataclass(frozen=True)
class ReactivationDeliveryClaim:
    contact: ReactivationCampaignContact
    token: str

    def __post_init__(self) -> None:
        token = str(self.token or "").strip()

        if not token:
            raise ValueError(
                "A delivery claim token is required."
            )

        persisted_token = str(
            self.contact.claim_token or ""
        ).strip()

        if persisted_token and persisted_token != token:
            raise ValueError(
                "Delivery claim token does not match the "
                "persisted contact claim token."
            )


class ReactivationCampaignContactService:
    """
    Coordinate reactivation contact persistence without knowing SQL.

    Atomicity, opt-out verification and lifecycle enforcement remain
    responsibilities of the repository.
    """

    def __init__(self, repository: Any):
        self.repository = repository

    def claim_for_delivery(
        self,
        *,
        contact_id: str,
        lease_seconds: int = 120,
    ) -> ReactivationDeliveryClaim | None:
        claim_token = str(uuid4())

        contact = self.repository.try_claim_delivery(
            contact_id=contact_id,
            claim_token=claim_token,
            lease_seconds=lease_seconds,
        )

        if contact is None:
            return None

        return ReactivationDeliveryClaim(
            contact=contact,
            token=claim_token,
        )

    def record_accepted(
        self,
        *,
        claim: ReactivationDeliveryClaim,
        provider_message_id: str,
    ) -> ReactivationCampaignContact | None:
        return self.repository.mark_accepted(
            contact_id=claim.contact.id,
            claim_token=claim.token,
            provider_message_id=provider_message_id,
        )

    def record_failed(
        self,
        *,
        claim: ReactivationDeliveryClaim,
        error_category: str,
        retryable: bool,
    ) -> ReactivationCampaignContact | None:
        return self.repository.mark_failed(
            contact_id=claim.contact.id,
            claim_token=claim.token,
            error_category=error_category,
            retryable=retryable,
        )

    def record_provider_status(
        self,
        *,
        provider_message_id: str,
        provider_status: str,
        occurred_at: datetime | None,
        error_category: str | None = None,
    ) -> ReactivationCampaignContact | None:
        return self.repository.apply_provider_status(
            provider_message_id=provider_message_id,
            provider_status=provider_status,
            occurred_at=occurred_at,
            error_category=error_category,
        )


class ReactivationCampaignResponseProcessingResult(BaseModel):
    contact_id: str
    response_event_id: str
    inbound_whatsapp_message_id: str
    response_classification: str
    response_safe_reason: str | None = None
    global_opt_out_requested: bool = False
    campaign_opt_out_requested: bool = False
    requires_human_escalation: bool = False
    received_at: datetime | None = None


class ReactivationCampaignResponseService:
    """
    Correlate, classify and persist inbound reactivation responses.

    The raw inbound message is used only for classification and is
    intentionally excluded from the persisted event and returned result.
    """

    def __init__(self, repository):
        self.repository = repository

    def process_inbound_response(
        self,
        *,
        phone_e164: str,
        inbound_whatsapp_message_id: str,
        message: str | None,
        received_at: datetime | None = None,
    ) -> ReactivationCampaignResponseProcessingResult | None:
        phone_e164 = str(phone_e164 or "").strip()
        inbound_whatsapp_message_id = str(
            inbound_whatsapp_message_id or ""
        ).strip()

        if not phone_e164:
            raise ValueError("phone_e164 is required.")

        if not inbound_whatsapp_message_id:
            raise ValueError(
                "inbound_whatsapp_message_id is required."
            )

        contact = (
            self.repository
            .find_latest_response_candidate_by_phone(
                phone_e164=phone_e164,
            )
        )

        if contact is None:
            return None

        decision = decide_reactivation_response(message)

        response_classification = getattr(
            decision.response_classification,
            "value",
            decision.response_classification,
        )

        response_safe_reason = decision.response_safe_reason

        if response_safe_reason is not None:
            response_safe_reason = getattr(
                response_safe_reason,
                "value",
                response_safe_reason,
            )

        event = self.repository.record_response_event(
            contact_id=contact.id,
            inbound_whatsapp_message_id=(
                inbound_whatsapp_message_id
            ),
            response_classification=response_classification,
            response_safe_reason=response_safe_reason,
            global_opt_out_requested=(
                decision.global_opt_out_requested
            ),
            campaign_opt_out_requested=(
                decision.campaign_opt_out_requested
            ),
            requires_human_escalation=(
                decision.requires_human_escalation
            ),
            received_at=received_at,
        )

        persisted_classification = getattr(
            event.response_classification,
            "value",
            event.response_classification,
        )

        persisted_safe_reason = event.response_safe_reason

        if persisted_safe_reason is not None:
            persisted_safe_reason = getattr(
                persisted_safe_reason,
                "value",
                persisted_safe_reason,
            )

        return ReactivationCampaignResponseProcessingResult(
            contact_id=event.contact_id,
            response_event_id=event.id,
            inbound_whatsapp_message_id=(
                event.inbound_whatsapp_message_id
            ),
            response_classification=persisted_classification,
            response_safe_reason=persisted_safe_reason,
            global_opt_out_requested=(
                event.global_opt_out_requested
            ),
            campaign_opt_out_requested=(
                event.campaign_opt_out_requested
            ),
            requires_human_escalation=(
                event.requires_human_escalation
            ),
            received_at=event.received_at,
        )
