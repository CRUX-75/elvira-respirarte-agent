from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.services.reactivation_status_runtime import (
    process_reactivation_status_updates_best_effort,
)


class FakeContactService:
    def __init__(
        self,
        *,
        unmatched_ids=(),
        exploding_ids=(),
    ):
        self.unmatched_ids = set(unmatched_ids)
        self.exploding_ids = set(exploding_ids)
        self.status_calls = []

    def record_provider_status(
        self,
        *,
        provider_message_id,
        provider_status,
        occurred_at,
        error_category,
    ):
        self.status_calls.append(
            {
                "provider_message_id": provider_message_id,
                "provider_status": provider_status,
                "occurred_at": occurred_at,
                "error_category": error_category,
            }
        )

        if provider_message_id in self.exploding_ids:
            raise RuntimeError(
                "secret raw provider and patient information"
            )

        if provider_message_id in self.unmatched_ids:
            return None

        return SimpleNamespace(
            id="contact-status",
            provider_message_id=provider_message_id,
        )


def build_update(
    *,
    provider_message_id="wamid.reactivation.001",
    status="delivered",
    timestamp="1790000001",
    error_code=None,
):
    return {
        "provider_message_id": provider_message_id,
        "status": status,
        "timestamp": timestamp,
        "error_code": error_code,
    }


def test_matching_callback_is_persisted_with_safe_summary():
    service = FakeContactService()

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [build_update()],
            contact_service=service,
        )
    )

    assert result == {
        "status": "status_updates_processed",
        "updates_received": 1,
        "updates_matched": 1,
        "updates_ignored": 0,
        "updates_failed": 0,
    }

    assert service.status_calls == [
        {
            "provider_message_id": (
                "wamid.reactivation.001"
            ),
            "provider_status": "delivered",
            "occurred_at": datetime.fromtimestamp(
                1790000001,
                tz=timezone.utc,
            ),
            "error_category": None,
        }
    ]


def test_unknown_wamid_is_counted_as_ignored():
    service = FakeContactService(
        unmatched_ids={"wamid.unknown"},
    )

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [
                build_update(
                    provider_message_id="wamid.unknown",
                    status="read",
                )
            ],
            contact_service=service,
        )
    )

    assert result == {
        "status": "status_updates_processed",
        "updates_received": 1,
        "updates_matched": 0,
        "updates_ignored": 1,
        "updates_failed": 0,
    }


def test_failed_callback_persists_only_safe_error_category():
    service = FakeContactService()

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [
                build_update(
                    status="failed",
                    error_code="131026",
                )
            ],
            contact_service=service,
        )
    )

    assert result["updates_matched"] == 1
    assert service.status_calls[0]["error_category"] == (
        "provider_status_failed_131026"
    )

    assert "131026" not in result


def test_missing_provider_id_is_ignored_without_service_call():
    service = FakeContactService()

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [
                {
                    "status": "delivered",
                    "timestamp": "1790000001",
                    "error_code": None,
                }
            ],
            contact_service=service,
        )
    )

    assert result["updates_received"] == 1
    assert result["updates_ignored"] == 1
    assert result["updates_failed"] == 0
    assert service.status_calls == []


def test_unsupported_provider_status_is_ignored():
    service = FakeContactService()

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [
                build_update(
                    status="deleted",
                )
            ],
            contact_service=service,
        )
    )

    assert result["updates_ignored"] == 1
    assert result["updates_failed"] == 0
    assert service.status_calls == []


def test_invalid_timestamp_becomes_none_without_losing_callback():
    service = FakeContactService()

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [
                build_update(
                    timestamp="not-a-timestamp",
                )
            ],
            contact_service=service,
        )
    )

    assert result["updates_matched"] == 1
    assert service.status_calls[0]["occurred_at"] is None


def test_one_repository_failure_does_not_block_later_callback():
    service = FakeContactService(
        exploding_ids={"wamid.exploding"},
    )

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [
                build_update(
                    provider_message_id="wamid.exploding",
                ),
                build_update(
                    provider_message_id="wamid.working",
                    status="read",
                ),
            ],
            contact_service=service,
        )
    )

    assert result == {
        "status": "status_updates_processed",
        "updates_received": 2,
        "updates_matched": 1,
        "updates_ignored": 0,
        "updates_failed": 1,
    }

    assert (
        "secret raw provider and patient information"
        not in str(result)
    )


def test_duplicate_callbacks_are_forwarded_to_repository():
    service = FakeContactService()
    duplicate = build_update()

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [
                duplicate.copy(),
                duplicate.copy(),
            ],
            contact_service=service,
        )
    )

    assert len(service.status_calls) == 2
    assert service.status_calls[0] == service.status_calls[1]
    assert result["updates_received"] == 2
    assert result["updates_matched"] == 2


def test_empty_batch_returns_safe_zero_summary():
    service = FakeContactService()

    result = asyncio.run(
        process_reactivation_status_updates_best_effort(
            [],
            contact_service=service,
        )
    )

    assert result == {
        "status": "status_updates_processed",
        "updates_received": 0,
        "updates_matched": 0,
        "updates_ignored": 0,
        "updates_failed": 0,
    }

    assert service.status_calls == []


def test_handler_is_connected_to_productive_webhook_through_router():
    main_source = Path("app/main.py").read_text(
        encoding="utf-8"
    )

    assert (
        "process_reactivation_status_updates_best_effort"
        in main_source
    )
    assert (
        "route_whatsapp_status_updates_best_effort"
        in main_source
    )
    assert (
        "patient_reactivation_handler=("
        in main_source
    )


def test_generic_router_remains_persistence_agnostic():
    router_source = Path(
        "app/services/whatsapp_status_runtime.py"
    ).read_text(encoding="utf-8").lower()

    assert "reactivation_campaign_contacts" not in router_source
    assert "reactivationcampaigncontactrepository" not in (
        router_source
    )
    assert "engine.begin" not in router_source
