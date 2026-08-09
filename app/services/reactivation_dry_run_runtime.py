"""
Best-effort runtime for P6-F.11.6 historical reactivation dry runs.

The runtime coordinates already isolated boundaries:

- read staging records through the reactivation Sheets adapter;
- resolve explicit external safety context per row;
- evaluate each row with the pure dry-run domain adapter;
- project only safe system-owned values back through the adapter;
- isolate row-level failures.

It does not persist campaign/contact records, activate campaigns or call
WhatsApp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from app.adapters.google_sheets_reactivation import ReactivationSheetRecord
from app.services.reactivation_dry_run import (
    ReactivationDryRunContext,
    ReactivationDryRunInputError,
    evaluate_reactivation_sheet_record,
)


class ReactivationDryRunAdapter(Protocol):
    def read_records(
        self,
    ) -> tuple[ReactivationSheetRecord, ...]:
        """Return the staging records to evaluate."""

    def update_system_projection(
        self,
        record: ReactivationSheetRecord,
        *,
        phone_e164: str,
        reactivation_status: str,
    ) -> str:
        """Project only the system-owned dry-run values."""


ContextResolver = Callable[
    [ReactivationSheetRecord],
    ReactivationDryRunContext,
]


@dataclass(frozen=True)
class ReactivationDryRunBatchItem:
    """Safe batch outcome for one staging row."""

    row_number: int
    source_reference: str
    outcome: str
    phone_e164: str | None = None
    exclusion_reasons: tuple[str, ...] = ()
    error_category: str | None = None


@dataclass(frozen=True)
class ReactivationDryRunBatchResult:
    """Aggregate best-effort dry-run result."""

    total: int
    eligible: int
    excluded: int
    invalid_input: int
    runtime_error: int
    items: tuple[ReactivationDryRunBatchItem, ...]


def _runtime_error_item(
    record: ReactivationSheetRecord,
    *,
    category: str,
) -> ReactivationDryRunBatchItem:
    return ReactivationDryRunBatchItem(
        row_number=record.row_number,
        source_reference=record.source_reference,
        outcome="runtime_error",
        error_category=category,
    )


def run_reactivation_dry_run_best_effort(
    *,
    adapter: ReactivationDryRunAdapter,
    context_resolver: ContextResolver,
    default_country_code: str | None,
) -> ReactivationDryRunBatchResult:
    """
    Evaluate and project staging records independently.

    Raw exception text is intentionally excluded from returned results.
    """

    records = adapter.read_records()
    items: list[ReactivationDryRunBatchItem] = []

    for record in records:
        try:
            context = context_resolver(record)
        except Exception:
            items.append(
                _runtime_error_item(
                    record,
                    category="context_resolution_failed",
                )
            )
            continue

        try:
            decision = evaluate_reactivation_sheet_record(
                record,
                context=context,
                default_country_code=default_country_code,
            )
        except ReactivationDryRunInputError:
            items.append(
                ReactivationDryRunBatchItem(
                    row_number=record.row_number,
                    source_reference=record.source_reference,
                    outcome="invalid_input",
                    error_category=(
                        "invalid_controlled_sheet_value"
                    ),
                )
            )
            continue
        except Exception:
            items.append(
                _runtime_error_item(
                    record,
                    category="evaluation_failed",
                )
            )
            continue

        outcome = decision.status.value

        try:
            adapter.update_system_projection(
                record,
                phone_e164=decision.phone_e164 or "",
                reactivation_status=outcome,
            )
        except Exception:
            items.append(
                _runtime_error_item(
                    record,
                    category="projection_failed",
                )
            )
            continue

        items.append(
            ReactivationDryRunBatchItem(
                row_number=decision.row_number,
                source_reference=decision.source_reference,
                outcome=outcome,
                phone_e164=decision.phone_e164,
                exclusion_reasons=tuple(
                    reason.value
                    for reason in decision.exclusion_reasons
                ),
            )
        )

    result_items = tuple(items)

    return ReactivationDryRunBatchResult(
        total=len(result_items),
        eligible=sum(
            item.outcome == "eligible"
            for item in result_items
        ),
        excluded=sum(
            item.outcome == "excluded"
            for item in result_items
        ),
        invalid_input=sum(
            item.outcome == "invalid_input"
            for item in result_items
        ),
        runtime_error=sum(
            item.outcome == "runtime_error"
            for item in result_items
        ),
        items=result_items,
    )
