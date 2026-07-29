from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.models.reactivation_campaign import (
    ReactivationCampaignContact,
)


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
