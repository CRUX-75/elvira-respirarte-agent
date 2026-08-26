from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.services.log_privacy import print_safe_event


_ALLOWED_PROVIDER_STATUSES = frozenset(
    {
        "sent",
        "delivered",
        "read",
        "failed",
    }
)


def _safe_provider_timestamp(
    value: object,
) -> datetime | None:
    if value is None:
        return None

    try:
        return datetime.fromtimestamp(
            int(str(value).strip()),
            tz=timezone.utc,
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _safe_provider_error_category(
    *,
    status: str,
    error_code: object,
) -> str | None:
    if status != "failed":
        return None

    if error_code is None:
        return "provider_status_failed"

    normalized = re.sub(
        r"[^A-Za-z0-9_-]+",
        "",
        str(error_code).strip(),
    )[:64]

    if not normalized:
        return "provider_status_failed"

    return f"provider_status_failed_{normalized}"


async def process_reactivation_status_updates_best_effort(
    status_updates: list[dict[str, Any]],
    *,
    contact_service: Any | None = None,
) -> dict[str, int | str]:
    """
    Persist Meta delivery callbacks for patient reactivation.

    Each callback is isolated. Unknown messages, malformed callbacks and
    repeated or out-of-order callbacks do not interrupt the batch.

    The returned summary contains only safe counters and categories.
    """

    callbacks = list(status_updates or [])
    received = len(callbacks)
    matched = 0
    ignored = 0
    failed = 0

    try:
        runtime_contact_service = contact_service

        if runtime_contact_service is None:
            from app.db.session import engine
            from app.repositories.reactivation_campaigns import (
                ReactivationCampaignContactRepository,
            )
            from app.services.reactivation_campaign_service import (
                ReactivationCampaignContactService,
            )

            repository = ReactivationCampaignContactRepository(
                engine
            )
            runtime_contact_service = (
                ReactivationCampaignContactService(repository)
            )

        for update in callbacks:
            if not isinstance(update, dict):
                ignored += 1
                continue

            provider_message_id = str(
                update.get("provider_message_id") or ""
            ).strip()

            provider_status = str(
                update.get("status") or ""
            ).strip().lower()

            if not provider_message_id:
                ignored += 1
                continue

            if provider_status not in _ALLOWED_PROVIDER_STATUSES:
                ignored += 1
                continue

            error_category = _safe_provider_error_category(
                status=provider_status,
                error_code=update.get("error_code"),
            )
            provider_error_code = None
            error_prefix = "provider_status_failed_"

            if (
                error_category is not None
                and error_category.startswith(error_prefix)
            ):
                provider_error_code = error_category[
                    len(error_prefix):
                ]

            try:
                contact = (
                    runtime_contact_service.record_provider_status(
                        provider_message_id=provider_message_id,
                        provider_status=provider_status,
                        occurred_at=_safe_provider_timestamp(
                            update.get("timestamp")
                        ),
                        error_category=error_category,
                    )
                )
            except Exception:
                print_safe_event(
                    {
                        "event": "whatsapp_status",
                        "domain": "reactivation",
                        "status": provider_status,
                        "correlation_outcome": (
                            "persistence_failed"
                        ),
                        "message_ref": None,
                        "provider_ref": provider_message_id,
                        "provider_error_code": (
                            provider_error_code
                        ),
                        "error_category": (
                            "status_persistence_error"
                        ),
                    }
                )
                failed += 1
                continue

            if contact is None:
                ignored += 1
                correlation_outcome = "not_applied"
                message_ref = None
            else:
                matched += 1
                correlation_outcome = "matched"
                message_ref = (
                    str(getattr(contact, "id", "") or "").strip()
                    or None
                )

            print_safe_event(
                {
                    "event": "whatsapp_status",
                    "domain": "reactivation",
                    "status": provider_status,
                    "correlation_outcome": correlation_outcome,
                    "message_ref": message_ref,
                    "provider_ref": provider_message_id,
                    "provider_error_code": provider_error_code,
                    "error_category": error_category,
                }
            )

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
