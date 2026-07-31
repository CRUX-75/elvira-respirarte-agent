from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Iterable

from app.services.reactivation_template_dispatcher import (
    ReactivationTemplateDispatchResult,
)


_FAILED_OUTCOMES = {
    "failed",
    "claim_failed",
    "runtime_error",
    "delivery_outcome_ambiguous",
    "failure_state_persistence_failed",
}


@dataclass(frozen=True)
class ReactivationTemplateBatchResult:
    results: tuple[ReactivationTemplateDispatchResult, ...]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def accepted(self) -> int:
        return sum(
            item.outcome == "accepted"
            for item in self.results
        )

    @property
    def failed(self) -> int:
        return sum(
            item.outcome in _FAILED_OUTCOMES
            for item in self.results
        )

    @property
    def ignored(self) -> int:
        return self.total - self.accepted - self.failed


async def dispatch_reactivation_contacts_best_effort(
    *,
    contact_ids: Iterable[str],
    dispatcher: Any,
) -> ReactivationTemplateBatchResult:
    """
    Dispatch contacts independently and return only safe summaries.

    An unexpected failure for one contact never blocks later contacts.
    Exception messages and provider details are intentionally discarded.
    """

    results: list[ReactivationTemplateDispatchResult] = []

    for raw_contact_id in contact_ids:
        contact_id = str(raw_contact_id or "").strip()

        try:
            dispatch_result = dispatcher.dispatch(
                contact_id=contact_id,
            )

            if inspect.isawaitable(dispatch_result):
                dispatch_result = await dispatch_result

            if not isinstance(
                dispatch_result,
                ReactivationTemplateDispatchResult,
            ):
                raise TypeError(
                    "Dispatcher returned an unsupported result."
                )

            results.append(dispatch_result)
        except Exception:
            results.append(
                ReactivationTemplateDispatchResult(
                    outcome="runtime_error",
                    contact_id=contact_id or None,
                    error_category="dispatch_runtime_error",
                    retryable=True,
                )
            )

    return ReactivationTemplateBatchResult(
        results=tuple(results),
    )
