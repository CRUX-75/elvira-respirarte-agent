from __future__ import annotations

from collections.abc import Awaitable, Callable
from copy import deepcopy
from inspect import isawaitable
from typing import Any


StatusHandler = Callable[
    [list[dict[str, Any]]],
    Awaitable[dict[str, Any] | None]
    | dict[str, Any]
    | None,
]


_SAFE_RESULT_FIELDS = frozenset(
    {
        "status",
        "updates_received",
        "updates_matched",
        "updates_ignored",
        "updates_failed",
        "error_category",
    }
)


def _safe_domain_result(
    result: object,
) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"status": "handler_completed"}

    safe_result: dict[str, Any] = {}

    for key in _SAFE_RESULT_FIELDS:
        value = result.get(key)

        if isinstance(value, (str, int, bool)) or value is None:
            if key in result:
                safe_result[key] = value

    safe_result.setdefault(
        "status",
        "handler_completed",
    )

    return safe_result


async def route_whatsapp_status_updates_best_effort(
    status_updates: list[dict[str, Any]],
    *,
    human_escalation_handler: StatusHandler,
    patient_reactivation_handler: StatusHandler,
) -> dict[str, Any]:
    """
    Route Meta status callbacks to independent domain handlers.

    Each handler receives an isolated copy. Domain persistence,
    idempotency and lifecycle rules remain outside this coordinator.
    """

    callbacks = list(status_updates or [])
    received = len(callbacks)

    if not callbacks:
        return {
            "status": "no_status_updates",
            "updates_received": 0,
            "domains_attempted": 0,
            "domains_succeeded": 0,
            "domains_failed": 0,
            "domain_results": {},
        }

    handlers: tuple[
        tuple[str, StatusHandler],
        ...,
    ] = (
        (
            "human_escalation",
            human_escalation_handler,
        ),
        (
            "patient_reactivation",
            patient_reactivation_handler,
        ),
    )

    domain_results: dict[str, dict[str, Any]] = {}
    succeeded = 0
    failed = 0

    for domain_name, handler in handlers:
        isolated_callbacks = deepcopy(callbacks)

        try:
            handler_result = handler(isolated_callbacks)

            if isawaitable(handler_result):
                handler_result = await handler_result

            domain_results[domain_name] = (
                _safe_domain_result(handler_result)
            )
            succeeded += 1

        except Exception:
            domain_results[domain_name] = {
                "status": "handler_failed",
                "error_category": (
                    f"{domain_name}_status_handler_error"
                ),
            }
            failed += 1

    return {
        "status": "status_updates_routed",
        "updates_received": received,
        "domains_attempted": len(handlers),
        "domains_succeeded": succeeded,
        "domains_failed": failed,
        "domain_results": domain_results,
    }
