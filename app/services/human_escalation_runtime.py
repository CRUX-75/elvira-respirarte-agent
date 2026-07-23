from __future__ import annotations

from datetime import datetime, timezone
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
from app.services.whatsapp import send_whatsapp_template_message


async def send_human_escalation_whatsapp(
    *,
    to: str,
    template_name: str,
    language_code: str,
    body_parameters: list[str],
) -> dict:
    """Adapt the approved template transport to the escalation dispatcher."""

    return await send_whatsapp_template_message(
        telefono=to,
        template_name=template_name,
        language_code=language_code,
        body_parameters=body_parameters,
    )


def _parse_provider_timestamp(value: object) -> datetime | None:
    try:
        timestamp = int(str(value or "").strip())
    except (TypeError, ValueError):
        return None

    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _safe_provider_error_category(
    *,
    status: str,
    error_code: object,
) -> str | None:
    if status != "failed":
        return None

    code = str(error_code or "").strip()

    if code and code.isdigit() and len(code) <= 12:
        return f"provider_status_failed_{code}"

    return "provider_status_failed"


async def process_human_escalation_status_updates_best_effort(
    status_updates: list[dict],
    *,
    event_service: Any | None = None,
) -> dict:
    """Apply Meta status callbacks without exposing recipient data/payloads."""
    received = len(status_updates)
    matched = 0
    ignored = 0
    failed = 0

    try:
        runtime_event_service = event_service

        if runtime_event_service is None:
            runtime_event_service = HumanEscalationEventService(
                HumanEscalationEventRepository(engine)
            )

        for update in status_updates:
            provider_message_id = str(
                update.get("provider_message_id") or ""
            ).strip()
            provider_status = str(
                update.get("status") or ""
            ).strip()

            if not provider_message_id or provider_status not in {
                "sent",
                "delivered",
                "read",
                "failed",
            }:
                ignored += 1
                continue

            try:
                event = runtime_event_service.record_provider_status(
                    provider_message_id=provider_message_id,
                    provider_status=provider_status,
                    occurred_at=_parse_provider_timestamp(
                        update.get("timestamp")
                    ),
                    error_category=_safe_provider_error_category(
                        status=provider_status,
                        error_code=update.get("error_code"),
                    ),
                )
            except Exception:
                failed += 1
                continue

            if event is None:
                ignored += 1
            else:
                matched += 1

        return {
            "status": "status_updates_processed",
            "updates_received": received,
            "updates_matched": matched,
            "updates_ignored": ignored,
            "updates_failed": failed,
        }

    except Exception:
        return {
            "status": "status_updates_failed",
            "updates_received": received,
            "updates_matched": matched,
            "updates_ignored": ignored,
            "updates_failed": failed + 1,
        }


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
    send_template: Any | None = None,
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
            send_template=(
                send_template
                if send_template is not None
                else send_text
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
