from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.models.human_escalation_event import HumanEscalationEvent
from app.repositories.human_escalation_events import (
    HumanEscalationEventRepository,
)


@dataclass(frozen=True)
class HumanEscalationDeliveryClaim:
    event: HumanEscalationEvent
    token: str


class HumanEscalationEventService:
    """Lifecycle service for idempotent notification delivery."""

    def __init__(
        self,
        repository: HumanEscalationEventRepository,
    ):
        self.repository = repository

    def create_or_reuse(
        self,
        event: HumanEscalationEvent,
    ) -> HumanEscalationEvent:
        return self.repository.create_or_get(event)

    def claim_for_delivery(
        self,
        *,
        event_id: str,
        lease_seconds: int = 120,
    ) -> HumanEscalationDeliveryClaim | None:
        token = str(uuid4())

        event = self.repository.try_claim_delivery(
            event_id=event_id,
            claim_token=token,
            lease_seconds=lease_seconds,
        )

        if event is None:
            return None

        return HumanEscalationDeliveryClaim(
            event=event,
            token=token,
        )

    def record_sent(
        self,
        *,
        claim: HumanEscalationDeliveryClaim,
        provider_message_id: str | None,
    ) -> HumanEscalationEvent | None:
        return self.repository.mark_sent(
            event_id=claim.event.id,
            claim_token=claim.token,
            provider_message_id=provider_message_id,
        )

    def record_failed(
        self,
        *,
        claim: HumanEscalationDeliveryClaim,
        error_category: str,
        retryable: bool,
    ) -> HumanEscalationEvent | None:
        return self.repository.mark_failed(
            event_id=claim.event.id,
            claim_token=claim.token,
            error_category=error_category,
            retryable=retryable,
        )
