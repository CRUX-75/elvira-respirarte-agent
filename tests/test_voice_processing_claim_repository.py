from contextlib import contextmanager
from datetime import datetime, timezone

import app.repositories.processed_messages as processed_repository
import app.repositories.voice_processing_claims as claim_repository


class FakeMappings:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return FakeMappings(self.row)

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, statement, params):
        self.calls.append(
            {
                "sql": str(statement),
                "params": params,
            }
        )

        if self.results:
            return self.results.pop(0)

        return FakeResult()


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        yield self.connection


def test_try_claim_voice_processing_creates_atomic_lease(monkeypatch):
    expires_at = datetime(2026, 7, 17, 12, 5, tzinfo=timezone.utc)
    connection = FakeConnection(
        [
            FakeResult(
                {
                    "whatsapp_message_id": "wamid.voice.claim.001",
                    "claim_token": "claim-token-001",
                    "lease_expires_at": expires_at,
                }
            )
        ]
    )

    monkeypatch.setattr(
        claim_repository,
        "engine",
        FakeEngine(connection),
    )
    monkeypatch.setattr(
        claim_repository.settings,
        "voice_processing_lease_seconds",
        300,
    )

    claim = claim_repository.try_claim_voice_processing(
        whatsapp_message_id="wamid.voice.claim.001",
        telefono="573009450001",
    )

    assert claim is not None
    assert claim.claim_token == "claim-token-001"
    assert claim.lease_expires_at == expires_at

    call = connection.calls[0]

    assert "ON CONFLICT (whatsapp_message_id) DO UPDATE" in call["sql"]
    assert "lease_expires_at <= NOW()" in call["sql"]
    assert call["params"] == {
        "whatsapp_message_id": "wamid.voice.claim.001",
        "telefono": "573009450001",
        "lease_seconds": 300,
    }


def test_try_claim_voice_processing_returns_none_for_active_lease(
    monkeypatch,
):
    connection = FakeConnection([FakeResult(None)])

    monkeypatch.setattr(
        claim_repository,
        "engine",
        FakeEngine(connection),
    )

    claim = claim_repository.try_claim_voice_processing(
        whatsapp_message_id="wamid.voice.claim.002",
        telefono="573009450001",
    )

    assert claim is None


def test_mark_processed_removes_voice_claim_in_same_transaction(
    monkeypatch,
):
    connection = FakeConnection([FakeResult(), FakeResult()])

    monkeypatch.setattr(
        processed_repository,
        "engine",
        FakeEngine(connection),
    )

    processed_repository.mark_message_processed(
        whatsapp_message_id="wamid.voice.claim.003",
        telefono="573009450001",
    )

    assert len(connection.calls) == 2
    assert "INSERT INTO processed_messages" in connection.calls[0]["sql"]
    assert "DELETE FROM voice_processing_claims" in connection.calls[1]["sql"]
    assert connection.calls[1]["params"] == {
        "whatsapp_message_id": "wamid.voice.claim.003",
    }
