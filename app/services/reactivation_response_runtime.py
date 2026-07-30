from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any, Callable


GlobalOptOutWriter = Callable[..., Any]
EscalationWriter = Callable[..., Any]


def _safe_value(value: object) -> str | None:
    if value is None:
        return None

    resolved = getattr(value, "value", value)
    normalized = str(resolved).strip()

    return normalized or None


async def _invoke_best_effort(
    writer: Callable[..., Any],
    **kwargs: Any,
) -> bool:
    """
    Run one injected side effect without exposing implementation errors.

    Returns True when the action failed and False when it succeeded.
    """

    try:
        result = writer(**kwargs)

        if inspect.isawaitable(result):
            await result

        return False
    except Exception:
        return True


def _escalation_action_for_result(result: Any) -> str:
    classification = _safe_value(
        result.response_classification
    )

    if classification == "positive_contact_request":
        return "escalate_reactivation_interest"

    return "escalate_reactivation_complaint"


def _summary(
    *,
    status: str,
    response_matched: bool,
    response_classification: str | None,
    global_opt_out_requested: bool,
    human_escalation_required: bool,
    actions_failed: int,
) -> dict[str, str | bool | int | None]:
    return {
        "status": status,
        "response_matched": response_matched,
        "response_classification": response_classification,
        "global_opt_out_requested": global_opt_out_requested,
        "human_escalation_required": human_escalation_required,
        "actions_failed": actions_failed,
    }


async def process_reactivation_response_best_effort(
    *,
    phone_e164: str,
    inbound_whatsapp_message_id: str,
    message: str | None,
    received_at: datetime | None = None,
    response_service: Any,
    global_opt_out_writer: GlobalOptOutWriter | None = None,
    escalation_writer: EscalationWriter | None = None,
) -> dict[str, str | bool | int | None]:
    """
    Process one inbound reactivation response with isolated side effects.

    The raw message is sent only to the semantic response service. It is
    intentionally excluded from writers and from the returned safe summary.
    """

    normalized_phone = str(phone_e164 or "").strip()
    normalized_message_id = str(
        inbound_whatsapp_message_id or ""
    ).strip()

    try:
        result = response_service.process_inbound_response(
            phone_e164=normalized_phone,
            inbound_whatsapp_message_id=normalized_message_id,
            message=message,
            received_at=received_at,
        )

        if inspect.isawaitable(result):
            result = await result
    except Exception:
        return _summary(
            status="reactivation_response_failed",
            response_matched=False,
            response_classification=None,
            global_opt_out_requested=False,
            human_escalation_required=False,
            actions_failed=1,
        )

    if result is None:
        return _summary(
            status="reactivation_response_ignored",
            response_matched=False,
            response_classification=None,
            global_opt_out_requested=False,
            human_escalation_required=False,
            actions_failed=0,
        )

    classification = _safe_value(
        result.response_classification
    )
    safe_reason = _safe_value(
        result.response_safe_reason
    )
    global_opt_out_requested = bool(
        result.global_opt_out_requested
    )
    human_escalation_required = bool(
        result.requires_human_escalation
    )

    actions_failed = 0

    if (
        global_opt_out_requested
        and global_opt_out_writer is not None
    ):
        action_failed = await _invoke_best_effort(
            global_opt_out_writer,
            phone_e164=normalized_phone,
            inbound_whatsapp_message_id=normalized_message_id,
            response_event_id=result.response_event_id,
            safe_reason=safe_reason,
        )
        actions_failed += int(action_failed)

    if (
        human_escalation_required
        and escalation_writer is not None
    ):
        action_failed = await _invoke_best_effort(
            escalation_writer,
            contact_id=result.contact_id,
            phone_e164=normalized_phone,
            inbound_whatsapp_message_id=normalized_message_id,
            response_event_id=result.response_event_id,
            escalation_action=(
                _escalation_action_for_result(result)
            ),
            response_classification=classification,
            response_safe_reason=safe_reason,
            occurred_at=result.received_at,
        )
        actions_failed += int(action_failed)

    status = (
        "reactivation_response_actions_failed"
        if actions_failed
        else "reactivation_response_processed"
    )

    return _summary(
        status=status,
        response_matched=True,
        response_classification=classification,
        global_opt_out_requested=global_opt_out_requested,
        human_escalation_required=(
            human_escalation_required
        ),
        actions_failed=actions_failed,
    )
