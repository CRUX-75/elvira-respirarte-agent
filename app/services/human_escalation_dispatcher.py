from __future__ import annotations

import inspect

from dataclasses import dataclass
from typing import Any

from app.models.human_escalation_event import (
    HumanEscalationEvent,
    HumanEscalationStatus,
)
from app.services.human_escalation_config import (
    HumanEscalationConfig,
)


@dataclass(frozen=True)
class HumanEscalationDispatchResult:
    outcome: str
    event_id: str | None = None
    provider_message_id: str | None = None
    error_category: str | None = None
    retryable: bool | None = None

    @property
    def accepted(self) -> bool:
        return self.outcome == "accepted"

    @property
    def delivered(self) -> bool:
        return self.outcome == "delivered"


@dataclass(frozen=True)
class DeliveryErrorDecision:
    category: str
    retryable: bool


def extract_provider_message_id(response: Any) -> str | None:
    """Extract only the provider message ID."""

    if response is None:
        return None

    if isinstance(response, str):
        value = response.strip()
        return value or None

    if not isinstance(response, dict):
        return None

    for key in (
        "message_id",
        "provider_message_id",
        "id",
    ):
        value = response.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    messages = response.get("messages")

    if isinstance(messages, list) and messages:
        first_message = messages[0]

        if isinstance(first_message, dict):
            value = first_message.get("id")

            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def classify_delivery_error(
    error: BaseException,
) -> DeliveryErrorDecision:
    """Convert transport failures into safe categories."""

    status_code = getattr(error, "status_code", None)

    if status_code is None:
        response = getattr(error, "response", None)
        status_code = getattr(
            response,
            "status_code",
            None,
        )

    if isinstance(status_code, int):
        if status_code == 429:
            return DeliveryErrorDecision(
                category="provider_rate_limited",
                retryable=True,
            )

        if status_code >= 500:
            return DeliveryErrorDecision(
                category="provider_server_error",
                retryable=True,
            )

        if status_code in {401, 403}:
            return DeliveryErrorDecision(
                category="provider_auth_error",
                retryable=False,
            )

        if 400 <= status_code < 500:
            return DeliveryErrorDecision(
                category="provider_request_rejected",
                retryable=False,
            )

    if isinstance(error, TimeoutError):
        return DeliveryErrorDecision(
            category="network_timeout",
            retryable=True,
        )

    if isinstance(error, ConnectionError):
        return DeliveryErrorDecision(
            category="network_error",
            retryable=True,
        )

    if isinstance(error, ValueError):
        return DeliveryErrorDecision(
            category="invalid_delivery_configuration",
            retryable=False,
        )

    error_type = error.__class__.__name__.lower()

    if "timeout" in error_type:
        return DeliveryErrorDecision(
            category="network_timeout",
            retryable=True,
        )

    if any(
        token in error_type
        for token in (
            "connection",
            "network",
            "transport",
        )
    ):
        return DeliveryErrorDecision(
            category="network_error",
            retryable=True,
        )

    return DeliveryErrorDecision(
        category="unexpected_delivery_error",
        retryable=True,
    )


class HumanEscalationDispatcher:
    """Best-effort template dispatcher isolated from patient processing."""

    def __init__(
        self,
        *,
        event_service: Any,
        config: HumanEscalationConfig,
        send_template: Any,
        lease_seconds: int = 120,
    ):
        if lease_seconds < 1:
            raise ValueError(
                "lease_seconds must be greater than zero."
            )

        self.event_service = event_service
        self.config = config
        self.send_template = send_template
        self.lease_seconds = lease_seconds

    def _record_delivery_failure(
        self,
        *,
        claim: Any,
        decision: DeliveryErrorDecision,
    ) -> HumanEscalationDispatchResult:
        try:
            failed_event = self.event_service.record_failed(
                claim=claim,
                error_category=decision.category,
                retryable=decision.retryable,
            )
        except Exception:
            return HumanEscalationDispatchResult(
                outcome="failure_state_persistence_failed",
                event_id=claim.event.id,
                error_category=decision.category,
                retryable=False,
            )

        return HumanEscalationDispatchResult(
            outcome="failed",
            event_id=claim.event.id,
            error_category=decision.category,
            retryable=(
                failed_event.retryable
                if failed_event is not None
                else decision.retryable
            ),
        )

    def _record_ambiguous_outcome(
        self,
        *,
        claim: Any,
        provider_message_id: str | None,
    ) -> HumanEscalationDispatchResult:
        try:
            self.event_service.record_failed(
                claim=claim,
                error_category="delivery_outcome_ambiguous",
                retryable=False,
            )
        except Exception:
            pass

        return HumanEscalationDispatchResult(
            outcome="delivery_outcome_ambiguous",
            event_id=claim.event.id,
            provider_message_id=provider_message_id,
            error_category="delivery_outcome_ambiguous",
            retryable=False,
        )

    async def dispatch(
        self,
        event: HumanEscalationEvent,
    ) -> HumanEscalationDispatchResult:
        if not self.config.enabled:
            return HumanEscalationDispatchResult(
                outcome="disabled",
                event_id=event.id,
            )

        if not self.config.ready:
            return HumanEscalationDispatchResult(
                outcome="configuration_missing",
                event_id=event.id,
                error_category="missing_template_delivery_configuration",
                retryable=False,
            )

        if len(event.template_parameters) != 10:
            return HumanEscalationDispatchResult(
                outcome="configuration_missing",
                event_id=event.id,
                error_category="invalid_template_parameter_count",
                retryable=False,
            )

        try:
            persisted_event = (
                self.event_service.create_or_reuse(event)
            )
        except Exception:
            return HumanEscalationDispatchResult(
                outcome="persistence_failed",
                event_id=event.id,
                error_category="event_persistence_error",
                retryable=True,
            )

        if persisted_event.status in {
            HumanEscalationStatus.ACCEPTED,
            HumanEscalationStatus.SENT,
            HumanEscalationStatus.DELIVERED,
            HumanEscalationStatus.READ,
        }:
            return HumanEscalationDispatchResult(
                outcome="already_submitted",
                event_id=persisted_event.id,
                provider_message_id=(
                    persisted_event.provider_message_id
                ),
                retryable=False,
            )

        try:
            claim = self.event_service.claim_for_delivery(
                event_id=persisted_event.id,
                lease_seconds=self.lease_seconds,
            )
        except Exception:
            return HumanEscalationDispatchResult(
                outcome="claim_failed",
                event_id=persisted_event.id,
                error_category="delivery_claim_error",
                retryable=True,
            )

        if claim is None:
            return HumanEscalationDispatchResult(
                outcome="already_claimed",
                event_id=persisted_event.id,
            )

        try:
            send_response = self.send_template(
                to=self.config.whatsapp_number,
                template_name=self.config.template_name,
                language_code=self.config.template_language,
                body_parameters=claim.event.template_parameters,
            )

            if inspect.isawaitable(send_response):
                send_response = await send_response

        except Exception as error:
            return self._record_delivery_failure(
                claim=claim,
                decision=classify_delivery_error(error),
            )

        provider_message_id = extract_provider_message_id(
            send_response
        )

        if not provider_message_id:
            return self._record_ambiguous_outcome(
                claim=claim,
                provider_message_id=None,
            )

        try:
            accepted_event = self.event_service.record_accepted(
                claim=claim,
                provider_message_id=provider_message_id,
            )
        except Exception:
            return self._record_ambiguous_outcome(
                claim=claim,
                provider_message_id=provider_message_id,
            )

        if accepted_event is None:
            return self._record_ambiguous_outcome(
                claim=claim,
                provider_message_id=provider_message_id,
            )

        return HumanEscalationDispatchResult(
            outcome="accepted",
            event_id=accepted_event.id,
            provider_message_id=provider_message_id,
            retryable=False,
        )
