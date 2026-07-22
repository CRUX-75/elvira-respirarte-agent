from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from app.models.human_escalation_event import (
    HumanEscalationEvent,
    HumanEscalationStatus,
)
from app.repositories.human_escalation_events import (
    HumanEscalationEventRepository,
)
from app.services.human_escalation_event_service import (
    HumanEscalationDeliveryClaim,
    HumanEscalationEventService,
)


NOW = datetime(
    2026,
    7,
    22,
    12,
    0,
    tzinfo=ZoneInfo("America/Bogota"),
)


class FakeMappings:
    def __init__(self, rows):
        self.rows = list(rows)

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class FakeResult:
    def __init__(self, rows=()):
        self.rows = rows

    def mappings(self):
        return FakeMappings(self.rows)


class FakeConnection:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), dict(params)))

        if not self.responses:
            raise AssertionError("Unexpected repository execute call.")

        return self.responses.pop(0)


class FakeBegin:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeEngine:
    def __init__(self, responses):
        self.connection = FakeConnection(responses)

    def begin(self):
        return FakeBegin(self.connection)


def event_row(**updates):
    row = {
        "id": "event-1",
        "idempotency_key": "a" * 64,
        "patient_id": "patient-1",
        "inbound_whatsapp_message_id": "wamid.test",
        "escalation_action": "escalate_unknown_service",
        "reason_code": "escalate_unknown_service",
        "notification_text": "Escalamiento de prueba",
        "status": "pending",
        "attempt_count": 0,
        "retryable": True,
        "provider_message_id": None,
        "last_error_category": None,
        "claim_token": None,
        "claim_expires_at": None,
        "created_at": NOW,
        "last_attempt_at": None,
        "sent_at": None,
    }
    row.update(updates)
    return row


def build_event():
    return HumanEscalationEvent(**event_row())


def test_create_or_get_returns_newly_inserted_event():
    engine = FakeEngine(
        [
            FakeResult([event_row()]),
        ]
    )
    repository = HumanEscalationEventRepository(engine)

    persisted = repository.create_or_get(build_event())

    assert persisted.id == "event-1"
    assert len(engine.connection.calls) == 1
    assert "ON CONFLICT" in engine.connection.calls[0][0]
    assert "DO NOTHING" in engine.connection.calls[0][0]


def test_create_or_get_reuses_existing_event_after_conflict():
    engine = FakeEngine(
        [
            FakeResult([]),
            FakeResult([event_row()]),
        ]
    )
    repository = HumanEscalationEventRepository(engine)

    persisted = repository.create_or_get(build_event())

    assert persisted.id == "event-1"
    assert len(engine.connection.calls) == 2
    assert "SELECT" in engine.connection.calls[1][0]


def test_create_or_get_raises_when_conflict_row_disappears():
    engine = FakeEngine(
        [
            FakeResult([]),
            FakeResult([]),
        ]
    )
    repository = HumanEscalationEventRepository(engine)

    with pytest.raises(
        RuntimeError,
        match="could not be loaded",
    ):
        repository.create_or_get(build_event())


def test_get_by_id_returns_none_when_missing():
    engine = FakeEngine([FakeResult([])])
    repository = HumanEscalationEventRepository(engine)

    assert repository.get_by_id("missing") is None


def test_try_claim_delivery_returns_claimed_event():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    event_row(
                        claim_token="claim-1",
                        attempt_count=1,
                        last_attempt_at=NOW,
                    )
                ]
            )
        ]
    )
    repository = HumanEscalationEventRepository(engine)

    claimed = repository.try_claim_delivery(
        event_id="event-1",
        claim_token="claim-1",
        lease_seconds=120,
    )

    assert claimed is not None
    assert claimed.claim_token == "claim-1"
    assert claimed.attempt_count == 1

    sql, params = engine.connection.calls[0]

    assert "status <> 'sent'" in sql
    assert "retryable = FALSE" in sql
    assert "claim_expires_at <= NOW()" in sql
    assert params["lease_seconds"] == 120


def test_try_claim_delivery_returns_none_when_locked():
    engine = FakeEngine([FakeResult([])])
    repository = HumanEscalationEventRepository(engine)

    claimed = repository.try_claim_delivery(
        event_id="event-1",
        claim_token="claim-2",
    )

    assert claimed is None


def test_mark_sent_requires_matching_claim():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    event_row(
                        status="sent",
                        retryable=False,
                        provider_message_id="wamid.doctor",
                        sent_at=NOW,
                    )
                ]
            )
        ]
    )
    repository = HumanEscalationEventRepository(engine)

    sent = repository.mark_sent(
        event_id="event-1",
        claim_token="claim-1",
        provider_message_id="wamid.doctor",
    )

    assert sent is not None
    assert sent.status == HumanEscalationStatus.SENT
    assert sent.retryable is False
    assert sent.provider_message_id == "wamid.doctor"
    assert "claim_token = :claim_token" in engine.connection.calls[0][0]


def test_mark_failed_preserves_retry_decision():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    event_row(
                        status="failed",
                        retryable=True,
                        last_error_category="network_error",
                    )
                ]
            )
        ]
    )
    repository = HumanEscalationEventRepository(engine)

    failed = repository.mark_failed(
        event_id="event-1",
        claim_token="claim-1",
        error_category="network_error",
        retryable=True,
    )

    assert failed is not None
    assert failed.status == HumanEscalationStatus.FAILED
    assert failed.retryable is True
    assert failed.last_error_category == "network_error"


def test_list_retryable_returns_oldest_available_events():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    event_row(id="event-1"),
                    event_row(
                        id="event-2",
                        inbound_whatsapp_message_id="wamid.test-2",
                    ),
                ]
            )
        ]
    )
    repository = HumanEscalationEventRepository(engine)

    events = repository.list_retryable(limit=25)

    assert [event.id for event in events] == [
        "event-1",
        "event-2",
    ]

    sql, params = engine.connection.calls[0]

    assert "ORDER BY created_at ASC" in sql
    assert params["limit"] == 25


def test_event_service_uses_atomic_repository_claim():
    repository = Mock()
    repository.try_claim_delivery.return_value = build_event()

    service = HumanEscalationEventService(repository)

    claim = service.claim_for_delivery(
        event_id="event-1",
        lease_seconds=90,
    )

    assert claim is not None
    assert claim.event.id == "event-1"
    assert claim.token

    repository.try_claim_delivery.assert_called_once_with(
        event_id="event-1",
        claim_token=claim.token,
        lease_seconds=90,
    )


def test_event_service_records_delivery_using_claim_token():
    repository = Mock()
    repository.mark_sent.return_value = HumanEscalationEvent(
        **event_row(
            status="sent",
            retryable=False,
            provider_message_id="wamid.doctor",
            sent_at=NOW,
        )
    )

    service = HumanEscalationEventService(repository)

    claim = HumanEscalationDeliveryClaim(
        event=build_event(),
        token="claim-1",
    )

    result = service.record_sent(
        claim=claim,
        provider_message_id="wamid.doctor",
    )

    assert result is not None
    assert result.status == HumanEscalationStatus.SENT

    repository.mark_sent.assert_called_once_with(
        event_id="event-1",
        claim_token="claim-1",
        provider_message_id="wamid.doctor",
    )


def test_repository_rejects_invalid_limits_and_lease():
    repository = HumanEscalationEventRepository(
        FakeEngine([])
    )

    with pytest.raises(ValueError, match="greater than zero"):
        repository.try_claim_delivery(
            event_id="event-1",
            claim_token="claim-1",
            lease_seconds=0,
        )

    with pytest.raises(ValueError, match="between 1 and 200"):
        repository.list_retryable(limit=0)
