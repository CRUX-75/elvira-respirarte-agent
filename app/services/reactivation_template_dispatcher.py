from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from app.services.human_escalation_dispatcher import (
    classify_delivery_error,
    extract_provider_message_id,
)
from app.services.reactivation_domain import (
    normalize_reactivation_phone_e164,
)


DEFAULT_REACTIVATION_TEMPLATE_NAME = "reactivacion_respirarte"
DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE = "es_CO"


@dataclass(frozen=True)
class ReactivationTemplateDispatchConfig:
    enabled: bool = False
    template_name: str = DEFAULT_REACTIVATION_TEMPLATE_NAME
    template_language: str = DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE


@dataclass(frozen=True)
class ReactivationTemplateDispatchRequest:
    contact_id: str

    def __post_init__(self) -> None:
        contact_id = str(self.contact_id or "").strip()

        if not contact_id:
            raise ValueError("contact_id is required.")

        object.__setattr__(
            self,
            "contact_id",
            contact_id,
        )


@dataclass(frozen=True)
class ReactivationTemplateDispatchResult:
    outcome: str
    contact_id: str | None = None
    provider_message_id: str | None = None
    error_category: str | None = None
    retryable: bool | None = None

    @property
    def accepted(self) -> bool:
        return self.outcome == "accepted"


class ReactivationTemplateDispatcher:
    """
    Dispatch one approved reactivation template after an atomic claim.

    The dispatcher has no database, HTTP or production wiring knowledge.
    Persistence and opt-out enforcement remain inside the injected
    contact service and repository.
    """

    def __init__(
        self,
        *,
        contact_service: Any,
        send_template: Any,
        config: ReactivationTemplateDispatchConfig | None = None,
        lease_seconds: int = 120,
    ):
        if lease_seconds < 1:
            raise ValueError(
                "lease_seconds must be greater than zero."
            )

        effective_config = (
            config
            if config is not None
            else ReactivationTemplateDispatchConfig()
        )

        template_name = str(
            effective_config.template_name or ""
        ).strip()
        template_language = str(
            effective_config.template_language or ""
        ).strip()

        if not template_name:
            raise ValueError("template_name is required.")

        if not template_language:
            raise ValueError("template_language is required.")

        if (
            template_name
            != DEFAULT_REACTIVATION_TEMPLATE_NAME
            or template_language
            != DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE
        ):
            raise ValueError(
                "The approved reactivation template contract "
                "requires reactivacion_respirarte with es_CO."
            )

        self.contact_service = contact_service
        self.send_template = send_template
        self.config = ReactivationTemplateDispatchConfig(
            enabled=bool(effective_config.enabled),
            template_name=template_name,
            template_language=template_language,
        )
        self.lease_seconds = lease_seconds
        self.template_name = template_name
        self.template_language = template_language

    def _record_failed(
        self,
        *,
        claim: Any,
        error_category: str,
        retryable: bool,
    ) -> ReactivationTemplateDispatchResult:
        contact_id = claim.contact.id

        try:
            failed_contact = self.contact_service.record_failed(
                claim=claim,
                error_category=error_category,
                retryable=retryable,
            )
        except Exception:
            return ReactivationTemplateDispatchResult(
                outcome="failure_state_persistence_failed",
                contact_id=contact_id,
                error_category=error_category,
                retryable=False,
            )

        if failed_contact is None:
            return ReactivationTemplateDispatchResult(
                outcome="failure_state_persistence_failed",
                contact_id=contact_id,
                error_category=error_category,
                retryable=False,
            )

        return ReactivationTemplateDispatchResult(
            outcome="failed",
            contact_id=contact_id,
            error_category=error_category,
            retryable=failed_contact.retryable,
        )

    def _attempt_terminal_failure_after_wamid(
        self,
        *,
        claim: Any,
        error_category: str,
    ) -> None:
        """
        Best-effort block against a second send after Meta returned a WAMID.

        Repository guards prevent overwriting an acceptance that may already
        have committed despite an ambiguous persistence result.
        """

        try:
            self.contact_service.record_failed(
                claim=claim,
                error_category=error_category,
                retryable=False,
            )
        except Exception:
            return

    async def dispatch(
        self,
        *,
        contact_id: str | None = None,
        request: ReactivationTemplateDispatchRequest | None = None,
    ) -> ReactivationTemplateDispatchResult:
        if request is not None and contact_id is not None:
            raise ValueError(
                "Provide request or contact_id, not both."
            )

        if request is not None:
            contact_id = request.contact_id
        else:
            contact_id = str(contact_id or "").strip()

            if not contact_id:
                raise ValueError("contact_id is required.")

        if not self.config.enabled:
            return ReactivationTemplateDispatchResult(
                outcome="disabled",
                contact_id=contact_id,
                retryable=False,
            )

        try:
            claim = self.contact_service.claim_for_delivery(
                contact_id=contact_id,
                lease_seconds=self.lease_seconds,
            )
        except Exception:
            return ReactivationTemplateDispatchResult(
                outcome="claim_failed",
                contact_id=contact_id,
                error_category="delivery_claim_error",
                retryable=True,
            )

        if claim is None:
            return ReactivationTemplateDispatchResult(
                outcome="already_claimed_or_ineligible",
                contact_id=contact_id,
                retryable=False,
            )

        contact = claim.contact
        phone_e164 = str(contact.phone_e164 or "").strip()
        contact_name = str(contact.name or "").strip()

        normalized_phone = normalize_reactivation_phone_e164(
            phone_e164,
            default_country_code=None,
        )

        if (
            not normalized_phone
            or normalized_phone != phone_e164
            or not contact_name
        ):
            return self._record_failed(
                claim=claim,
                error_category="invalid_template_contact_data",
                retryable=False,
            )

        try:
            send_response = self.send_template(
                to=normalized_phone,
                template_name=self.template_name,
                language_code=self.template_language,
                body_parameters=[contact_name],
            )

            if inspect.isawaitable(send_response):
                send_response = await send_response
        except Exception as error:
            decision = classify_delivery_error(error)

            return self._record_failed(
                claim=claim,
                error_category=decision.category,
                retryable=decision.retryable,
            )

        provider_message_id = extract_provider_message_id(
            send_response
        )

        if not provider_message_id:
            return self._record_failed(
                claim=claim,
                error_category="delivery_outcome_ambiguous",
                retryable=False,
            )

        try:
            accepted_contact = (
                self.contact_service.record_accepted(
                    claim=claim,
                    provider_message_id=provider_message_id,
                )
            )
        except Exception:
            error_category = "acceptance_persistence_error"

            self._attempt_terminal_failure_after_wamid(
                claim=claim,
                error_category=error_category,
            )

            return ReactivationTemplateDispatchResult(
                outcome="delivery_outcome_ambiguous",
                contact_id=contact_id,
                provider_message_id=provider_message_id,
                error_category=error_category,
                retryable=False,
            )

        if accepted_contact is None:
            error_category = "acceptance_persistence_conflict"

            self._attempt_terminal_failure_after_wamid(
                claim=claim,
                error_category=error_category,
            )

            return ReactivationTemplateDispatchResult(
                outcome="delivery_outcome_ambiguous",
                contact_id=contact_id,
                provider_message_id=provider_message_id,
                error_category=error_category,
                retryable=False,
            )

        return ReactivationTemplateDispatchResult(
            outcome="accepted",
            contact_id=accepted_contact.id,
            provider_message_id=provider_message_id,
            retryable=False,
        )
