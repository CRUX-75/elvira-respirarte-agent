from __future__ import annotations

from typing import Any

from app.config import settings
from app.db.session import engine
from app.repositories.human_escalation_events import (
    HumanEscalationEventRepository,
)
from app.services.human_escalation import (
    build_human_escalation_event,
    should_dispatch_human_escalation,
)
from app.services.human_escalation_config import (
    HumanEscalationConfig,
    load_human_escalation_config,
)
from app.services.human_escalation_dispatcher import (
    HumanEscalationDispatcher,
    HumanEscalationDispatchResult,
)
from app.services.human_escalation_event_service import (
    HumanEscalationEventService,
)
from app.services.whatsapp import send_whatsapp_message


async def send_human_escalation_whatsapp(
    *,
    to: str,
    message: str,
) -> dict:
    """Adapt the existing patient transport to an explicit recipient."""

    return await send_whatsapp_message(
        telefono=to,
        mensaje=message,
    )


async def dispatch_human_escalation_best_effort(
    *,
    patient_id: str | None,
    patient_name: str | None,
    patient_phone: str | None,
    inbound_whatsapp_message_id: str,
    result: Any,
    conversation_state: str | None,
    config: HumanEscalationConfig | None = None,
    event_service: Any | None = None,
    send_text: Any | None = None,
) -> HumanEscalationDispatchResult:
    """
    Dispatch a human escalation without altering patient processing.

    Raw audio, transcript, inbound message text and complete conversation
    history are intentionally absent.
    """

    try:
        runtime_config = (
            config
            if config is not None
            else load_human_escalation_config(
                settings_obj=settings
            )
        )

        if not runtime_config.enabled:
            return HumanEscalationDispatchResult(
                outcome="disabled"
            )

        escalation_required = bool(
            getattr(
                result,
                "escalation_required",
                False,
            )
        )

        escalation_action = getattr(
            result,
            "next_action",
            None,
        )

        if not should_dispatch_human_escalation(
            escalation_required=escalation_required,
            next_action=escalation_action,
        ):
            return HumanEscalationDispatchResult(
                outcome="not_required"
            )

        event = build_human_escalation_event(
            patient_id=patient_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            inbound_whatsapp_message_id=(
                inbound_whatsapp_message_id
            ),
            escalation_required=escalation_required,
            escalation_action=escalation_action,
            conversation_state=conversation_state,
        )

        runtime_event_service = event_service

        if runtime_event_service is None:
            repository = HumanEscalationEventRepository(
                engine
            )
            runtime_event_service = (
                HumanEscalationEventService(repository)
            )

        dispatcher = HumanEscalationDispatcher(
            event_service=runtime_event_service,
            config=runtime_config,
            send_text=(
                send_text
                if send_text is not None
                else send_human_escalation_whatsapp
            ),
            lease_seconds=getattr(
                settings,
                "human_escalation_delivery_lease_seconds",
                120,
            ),
        )

        return await dispatcher.dispatch(event)

    except Exception:
        return HumanEscalationDispatchResult(
            outcome="orchestration_failed",
            error_category="human_escalation_runtime_error",
            retryable=False,
        )
