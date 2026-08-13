"""
Productive dependency composition for historical reactivation dispatch.

This module only builds the existing repository, service, dispatcher and
approved WhatsApp transport dependencies.

Building the dispatcher performs no database access, contact selection,
campaign activation, dispatch or sending. Productive dispatch remains
disabled unless explicitly enabled by the caller.
"""

from __future__ import annotations

from typing import Any

from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
)
from app.services.reactivation_campaign_service import (
    ReactivationCampaignContactService,
)
from app.services.reactivation_template_dispatcher import (
    DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
    DEFAULT_REACTIVATION_TEMPLATE_NAME,
    ReactivationTemplateDispatchConfig,
    ReactivationTemplateDispatcher,
)
from app.services.reactivation_template_transport import (
    send_reactivation_whatsapp_template,
)


def build_reactivation_template_dispatcher(
    *,
    engine: Any,
    enabled: bool = False,
    lease_seconds: int = 120,
) -> ReactivationTemplateDispatcher:
    """
    Build the productive reactivation dispatcher without executing it.
    """

    repository = ReactivationCampaignContactRepository(engine)
    contact_service = ReactivationCampaignContactService(repository)

    config = ReactivationTemplateDispatchConfig(
        enabled=bool(enabled),
        template_name=DEFAULT_REACTIVATION_TEMPLATE_NAME,
        template_language=DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
    )

    return ReactivationTemplateDispatcher(
        contact_service=contact_service,
        send_template=send_reactivation_whatsapp_template,
        config=config,
        lease_seconds=lease_seconds,
    )
