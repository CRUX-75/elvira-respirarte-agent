"""
Read-only preflight for the minimal real historical reactivation pilot.

The caller must supply one existing campaign and 1-3 explicitly selected
persisted contact IDs.

This module performs no persistence, campaign activation, claiming,
dispatch or WhatsApp delivery.
"""

from __future__ import annotations

from typing import Any, Iterable

from app.models.reactivation_campaign import (
    ReactivationCampaignStatus,
    ReactivationContactStatus,
)
from app.services.reactivation_template_dispatcher import (
    DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
    DEFAULT_REACTIVATION_TEMPLATE_NAME,
)
from app.services.reactivation_template_runtime import (
    ReactivationTemplateBatchResult,
    dispatch_reactivation_contacts_best_effort,
)


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def preflight_reactivation_real_pilot(
    *,
    campaign_id: str,
    contact_ids: Iterable[str],
    campaign_repository: Any,
    contact_repository: Any,
) -> tuple[Any, ...]:
    """
    Validate one explicit persisted pilot batch without side effects.
    """

    normalized_campaign_id = str(campaign_id or "").strip()

    if not normalized_campaign_id:
        raise ValueError("campaign_id is required.")

    normalized_contact_ids = tuple(
        str(contact_id or "").strip()
        for contact_id in contact_ids
    )

    if not 1 <= len(normalized_contact_ids) <= 3:
        raise ValueError(
            "Real pilot requires between 1 and 3 explicit contacts."
        )

    if any(not contact_id for contact_id in normalized_contact_ids):
        raise ValueError(
            "Real pilot contact IDs must be explicit and non-empty."
        )

    if len(set(normalized_contact_ids)) != len(
        normalized_contact_ids
    ):
        raise ValueError(
            "Real pilot contact IDs must be unique."
        )

    campaign = campaign_repository.get_by_id(
        normalized_campaign_id
    )

    if campaign is None:
        raise ValueError(
            "Reactivation campaign was not found."
        )

    try:
        campaign_status = ReactivationCampaignStatus(
            _enum_value(getattr(campaign, "status", None))
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Reactivation campaign status is invalid."
        ) from exc

    if campaign_status != ReactivationCampaignStatus.ACTIVE:
        raise ValueError(
            "Reactivation campaign must be active."
        )

    template_name = str(
        getattr(campaign, "template_name", "") or ""
    ).strip()
    template_language = str(
        getattr(campaign, "template_language", "") or ""
    ).strip()

    if (
        template_name != DEFAULT_REACTIVATION_TEMPLATE_NAME
        or template_language
        != DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE
    ):
        raise ValueError(
            "The approved reactivation template contract "
            "requires reactivacion_respirarte with es_CO."
        )

    contacts: list[Any] = []

    for contact_id in normalized_contact_ids:
        contact = contact_repository.get_by_id(contact_id)

        if contact is None:
            raise ValueError(
                f"Reactivation contact {contact_id!r} was not found."
            )

        persisted_campaign_id = str(
            getattr(contact, "campaign_id", "") or ""
        ).strip()

        if persisted_campaign_id != normalized_campaign_id:
            raise ValueError(
                "Pilot contact does not belong to the requested "
                "campaign."
            )

        provider_message_id = str(
            getattr(contact, "provider_message_id", "") or ""
        ).strip()

        if provider_message_id:
            raise ValueError(
                "Pilot contact already has provider_message_id."
            )

        try:
            contact_status = ReactivationContactStatus(
                _enum_value(getattr(contact, "status", None))
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Pilot contact is not dispatchable."
            ) from exc

        retryable = bool(
            getattr(contact, "retryable", False)
        )

        dispatchable = (
            contact_status == ReactivationContactStatus.ELIGIBLE
            or (
                contact_status
                == ReactivationContactStatus.FAILED
                and retryable
            )
        )

        if not dispatchable:
            raise ValueError(
                "Pilot contact is not dispatchable."
            )

        contacts.append(contact)

    return tuple(contacts)


async def run_reactivation_real_pilot(
    *,
    campaign_id: str,
    contact_ids: Iterable[str],
    campaign_repository: Any,
    contact_repository: Any,
    dispatcher: Any,
    send_authorized: bool = False,
) -> ReactivationTemplateBatchResult:
    """
    Run one explicitly authorized minimal real pilot batch.

    Preflight remains read-only. Dispatch is possible only when the
    caller passes the literal boolean True as explicit authorization.
    """

    contacts = preflight_reactivation_real_pilot(
        campaign_id=campaign_id,
        contact_ids=contact_ids,
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
    )

    if send_authorized is not True:
        raise ValueError(
            "Real pilot requires explicit send authorization."
        )

    validated_contact_ids = tuple(
        str(contact.id).strip()
        for contact in contacts
    )

    return await dispatch_reactivation_contacts_best_effort(
        contact_ids=validated_contact_ids,
        dispatcher=dispatcher,
    )

