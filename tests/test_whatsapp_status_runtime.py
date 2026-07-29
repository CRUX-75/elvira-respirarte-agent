import asyncio
from pathlib import Path

from app.services.whatsapp_status_runtime import (
    route_whatsapp_status_updates_best_effort,
)


def build_updates():
    return [
        {
            "provider_message_id": "wamid.status.001",
            "status": "delivered",
            "timestamp": "1790000001",
            "error_code": None,
        },
        {
            "provider_message_id": "wamid.status.002",
            "status": "read",
            "timestamp": "1790000002",
            "error_code": None,
        },
    ]


def test_router_forwards_equivalent_isolated_batches_to_both_domains():
    original = build_updates()
    calls = {}

    async def human_escalation_handler(status_updates):
        calls["human_escalation"] = status_updates
        return {
            "status": "status_updates_processed",
            "updates_received": 2,
            "updates_matched": 1,
            "updates_ignored": 1,
            "updates_failed": 0,
        }

    async def patient_reactivation_handler(status_updates):
        calls["patient_reactivation"] = status_updates
        return {
            "status": "status_updates_processed",
            "updates_received": 2,
            "updates_matched": 1,
            "updates_ignored": 1,
            "updates_failed": 0,
        }

    result = asyncio.run(
        route_whatsapp_status_updates_best_effort(
            original,
            human_escalation_handler=human_escalation_handler,
            patient_reactivation_handler=(
                patient_reactivation_handler
            ),
        )
    )

    assert calls["human_escalation"] == original
    assert calls["patient_reactivation"] == original

    assert calls["human_escalation"] is not original
    assert calls["patient_reactivation"] is not original
    assert (
        calls["human_escalation"]
        is not calls["patient_reactivation"]
    )

    assert calls["human_escalation"][0] is not original[0]
    assert calls["patient_reactivation"][0] is not original[0]

    assert result == {
        "status": "status_updates_routed",
        "updates_received": 2,
        "domains_attempted": 2,
        "domains_succeeded": 2,
        "domains_failed": 0,
        "domain_results": {
            "human_escalation": {
                "status": "status_updates_processed",
                "updates_received": 2,
                "updates_matched": 1,
                "updates_ignored": 1,
                "updates_failed": 0,
            },
            "patient_reactivation": {
                "status": "status_updates_processed",
                "updates_received": 2,
                "updates_matched": 1,
                "updates_ignored": 1,
                "updates_failed": 0,
            },
        },
    }


def test_empty_callback_batch_does_not_call_domains():
    async def exploding_handler(status_updates):
        raise AssertionError(
            "Handlers must not run for an empty callback batch."
        )

    result = asyncio.run(
        route_whatsapp_status_updates_best_effort(
            [],
            human_escalation_handler=exploding_handler,
            patient_reactivation_handler=exploding_handler,
        )
    )

    assert result == {
        "status": "no_status_updates",
        "updates_received": 0,
        "domains_attempted": 0,
        "domains_succeeded": 0,
        "domains_failed": 0,
        "domain_results": {},
    }


def test_failure_in_one_domain_does_not_block_the_other():
    calls = []

    async def failing_human_handler(status_updates):
        calls.append("human_escalation")
        raise RuntimeError(
            "secret raw provider or patient information"
        )

    async def successful_reactivation_handler(status_updates):
        calls.append("patient_reactivation")
        return {
            "status": "status_updates_processed",
            "updates_received": len(status_updates),
            "updates_matched": 1,
            "updates_ignored": 0,
            "updates_failed": 0,
        }

    result = asyncio.run(
        route_whatsapp_status_updates_best_effort(
            build_updates()[:1],
            human_escalation_handler=failing_human_handler,
            patient_reactivation_handler=(
                successful_reactivation_handler
            ),
        )
    )

    assert set(calls) == {
        "human_escalation",
        "patient_reactivation",
    }
    assert result["status"] == "status_updates_routed"
    assert result["updates_received"] == 1
    assert result["domains_attempted"] == 2
    assert result["domains_succeeded"] == 1
    assert result["domains_failed"] == 1

    assert result["domain_results"]["human_escalation"] == {
        "status": "handler_failed",
        "error_category": (
            "human_escalation_status_handler_error"
        ),
    }
    assert (
        result["domain_results"]["patient_reactivation"]
        ["status"]
        == "status_updates_processed"
    )

    assert (
        "secret raw provider or patient information"
        not in str(result)
    )


def test_first_domain_cannot_mutate_second_domain_batch():
    original = build_updates()[:1]
    observations = {}

    async def mutating_human_handler(status_updates):
        status_updates[0]["status"] = "failed"
        status_updates[0]["new_private_field"] = "must_not_leak"

        observations["human_status"] = (
            status_updates[0]["status"]
        )

        return {"status": "mutated_local_copy"}

    async def observing_reactivation_handler(status_updates):
        observations["reactivation_update"] = (
            status_updates[0].copy()
        )

        return {"status": "observed_original_copy"}

    asyncio.run(
        route_whatsapp_status_updates_best_effort(
            original,
            human_escalation_handler=mutating_human_handler,
            patient_reactivation_handler=(
                observing_reactivation_handler
            ),
        )
    )

    assert observations["human_status"] == "failed"
    assert observations["reactivation_update"] == original[0]
    assert "new_private_field" not in original[0]
    assert original[0]["status"] == "delivered"


def test_duplicate_callbacks_are_forwarded_without_router_deduplication():
    duplicate = {
        "provider_message_id": "wamid.duplicate",
        "status": "delivered",
        "timestamp": "1790000001",
        "error_code": None,
    }
    updates = [duplicate.copy(), duplicate.copy()]
    received = {}

    async def human_handler(status_updates):
        received["human"] = status_updates
        return {"status": "processed"}

    async def reactivation_handler(status_updates):
        received["reactivation"] = status_updates
        return {"status": "processed"}

    result = asyncio.run(
        route_whatsapp_status_updates_best_effort(
            updates,
            human_escalation_handler=human_handler,
            patient_reactivation_handler=reactivation_handler,
        )
    )

    assert len(received["human"]) == 2
    assert len(received["reactivation"]) == 2
    assert received["human"][0] == received["human"][1]
    assert (
        received["reactivation"][0]
        == received["reactivation"][1]
    )
    assert result["updates_received"] == 2

    # Domain repositories, not this router, own idempotency.
    assert result["domains_succeeded"] == 2


def test_router_module_is_persistence_agnostic():
    source = Path(
        "app/services/whatsapp_status_runtime.py"
    ).read_text(encoding="utf-8").lower()

    forbidden_fragments = [
        "sqlalchemy",
        "from app.repositories",
        "human_escalation_events",
        "reactivation_campaign_contacts",
        "engine.begin",
        "insert into",
        "update ",
        "delete from",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source
