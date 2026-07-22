from __future__ import annotations

import asyncio

from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from app.models.human_escalation_event import (
    HumanEscalationEvent,
    HumanEscalationStatus,
)
from app.services.human_escalation_config import (
    HumanEscalationConfig,
)
from app.services.human_escalation_dispatcher import (
    HumanEscalationDispatcher,
    classify_delivery_error,
    extract_provider_message_id,
)
from app.services.human_escalation_event_service import (
    HumanEscalationDeliveryClaim,
)


NOW = datetime(
    2026,
    7,
    22,
    12,
    0,
    tzinfo=ZoneInfo("America/Bogota"),
)


def build_event(**updates) -> HumanEscalationEvent:
    values = {
        "id": "event-1",
        "idempotency_key": "a" * 64,
        "patient_id": "patient-1",
        "inbound_whatsapp_message_id": "wamid.patient",
        "escalation_action": "escalate_unknown_service",
        "reason_code": "escalate_unknown_service",
        "notification_text": "Escalamiento de prueba",
        "status": HumanEscalationStatus.PENDING,
        "attempt_count": 0,
        "retryable": True,
        "created_at": NOW,
    }
    values.update(updates)
    return HumanEscalationEvent(**values)


def ready_config() -> HumanEscalationConfig:
    return HumanEscalationConfig(
        enabled=True,
        whatsapp_number="573000000001",
    )


def test_extracts_meta_message_id():
    response = {
        "messaging_product": "whatsapp",
        "messages": [
            {
                "id": "wamid.doctor",
            }
        ],
    }

    assert (
        extract_provider_message_id(response)
        == "wamid.doctor"
    )


def test_extracts_direct_id_and_handles_unknown_response():
    assert (
        extract_provider_message_id(
            {"message_id": "wamid.direct"}
        )
        == "wamid.direct"
    )

    assert extract_provider_message_id(None) is None
    assert extract_provider_message_id({}) is None
    assert extract_provider_message_id(object()) is None


def test_disabled_dispatcher_does_nothing():
    event_service = Mock()
    sender = Mock()

    dispatcher = HumanEscalationDispatcher(
        event_service=event_service,
        config=HumanEscalationConfig(
            enabled=False,
            whatsapp_number=None,
        ),
        send_text=sender,
    )

    result = asyncio.run(
        dispatcher.dispatch(build_event())
    )

    assert result.outcome == "disabled"
    event_service.create_or_reuse.assert_not_called()
    sender.assert_not_called()


def test_missing_destination_does_not_persist_or_send():
    event_service = Mock()
    sender = Mock()

    dispatcher = HumanEscalationDispatcher(
        event_service=event_service,
        config=HumanEscalationConfig(
            enabled=True,
            whatsapp_number=None,
        ),
        send_text=sender,
    )

    result = asyncio.run(
        dispatcher.dispatch(build_event())
    )

    assert result.outcome == "configuration_missing"
    assert result.retryable is False
    event_service.create_or_reuse.assert_not_called()
    sender.assert_not_called()


def test_already_sent_event_is_not_sent_twice():
    event_service = Mock()
    sender = Mock()

    event_service.create_or_reuse.return_value = build_event(
        status=HumanEscalationStatus.SENT,
        retryable=False,
        provider_message_id="wamid.previous",
        sent_at=NOW,
    )

    dispatcher = HumanEscalationDispatcher(
        event_service=event_service,
        config=ready_config(),
        send_text=sender,
    )

    result = asyncio.run(
        dispatcher.dispatch(build_event())
    )

    assert result.outcome == "already_sent"
    assert result.provider_message_id == "wamid.previous"
    event_service.claim_for_delivery.assert_not_called()
    sender.assert_not_called()


def test_active_claim_prevents_duplicate_send():
    event_service = Mock()
    sender = Mock()

    event_service.create_or_reuse.return_value = build_event()
    event_service.claim_for_delivery.return_value = None

    dispatcher = HumanEscalationDispatcher(
        event_service=event_service,
        config=ready_config(),
        send_text=sender,
    )

    result = asyncio.run(
        dispatcher.dispatch(build_event())
    )

    assert result.outcome == "already_claimed"
    sender.assert_not_called()


def test_successful_send_records_provider_message_id():
    event_service = Mock()
    sender = Mock(
        return_value={
            "messages": [
                {
                    "id": "wamid.doctor",
                }
            ]
        }
    )

    event = build_event()

    claim = HumanEscalationDeliveryClaim(
        event=event,
        token="claim-1",
    )

    event_service.create_or_reuse.return_value = event
    event_service.claim_for_delivery.return_value = claim
    event_service.record_sent.return_value = build_event(
        status=HumanEscalationStatus.SENT,
        retryable=False,
        provider_message_id="wamid.doctor",
        sent_at=NOW,
    )

    dispatcher = HumanEscalationDispatcher(
        event_service=event_service,
        config=ready_config(),
        send_text=sender,
    )

    result = asyncio.run(
        dispatcher.dispatch(event)
    )

    assert result.outcome == "sent"
    assert result.delivered is True
    assert result.provider_message_id == "wamid.doctor"

    sender.assert_called_once_with(
        to="573000000001",
        message="Escalamiento de prueba",
    )

    event_service.record_sent.assert_called_once_with(
        claim=claim,
        provider_message_id="wamid.doctor",
    )


def test_timeout_is_recorded_as_retryable():
    event_service = Mock()
    sender = Mock(
        side_effect=TimeoutError("timeout detail")
    )

    event = build_event()

    claim = HumanEscalationDeliveryClaim(
        event=event,
        token="claim-1",
    )

    event_service.create_or_reuse.return_value = event
    event_service.claim_for_delivery.return_value = claim
    event_service.record_failed.return_value = build_event(
        status=HumanEscalationStatus.FAILED,
        retryable=True,
        last_error_category="network_timeout",
    )

    dispatcher = HumanEscalationDispatcher(
        event_service=event_service,
        config=ready_config(),
        send_text=sender,
    )

    result = asyncio.run(
        dispatcher.dispatch(event)
    )

    assert result.outcome == "failed"
    assert result.error_category == "network_timeout"
    assert result.retryable is True

    event_service.record_failed.assert_called_once_with(
        claim=claim,
        error_category="network_timeout",
        retryable=True,
    )


@pytest.mark.parametrize(
    (
        "status_code",
        "expected_category",
        "expected_retryable",
    ),
    [
        (400, "provider_request_rejected", False),
        (401, "provider_auth_error", False),
        (429, "provider_rate_limited", True),
        (503, "provider_server_error", True),
    ],
)
def test_http_error_classification(
    status_code,
    expected_category,
    expected_retryable,
):
    class ProviderError(Exception):
        pass

    error = ProviderError("provider detail")
    error.status_code = status_code

    decision = classify_delivery_error(error)

    assert decision.category == expected_category
    assert decision.retryable is expected_retryable


def test_persistence_failure_never_calls_sender():
    event_service = Mock()
    sender = Mock()

    event_service.create_or_reuse.side_effect = RuntimeError(
        "database unavailable"
    )

    dispatcher = HumanEscalationDispatcher(
        event_service=event_service,
        config=ready_config(),
        send_text=sender,
    )

    result = asyncio.run(
        dispatcher.dispatch(build_event())
    )

    assert result.outcome == "persistence_failed"
    assert result.retryable is True
    sender.assert_not_called()


def test_invalid_lease_is_rejected():
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        HumanEscalationDispatcher(
            event_service=Mock(),
            config=ready_config(),
            send_text=Mock(),
            lease_seconds=0,
        )
