from contextlib import contextmanager

import pytest

from app.repositories import patients


class FakeRow:
    def __init__(self, values):
        self._mapping = values


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return self.result


class FakeEngine:
    def __init__(self, result):
        self.connection = FakeConnection(result)
        self.connect_calls = 0
        self.begin_calls = 0

    @contextmanager
    def connect(self):
        self.connect_calls += 1
        yield self.connection

    @contextmanager
    def begin(self):
        self.begin_calls += 1
        yield self.connection


def test_find_patient_by_phone_read_only_returns_minimal_record(
    monkeypatch,
):
    fake_engine = FakeEngine(
        FakeResult(
            FakeRow(
                {
                    "id": "patient-1",
                    "telefono": "573000000001",
                    "opt_out": True,
                }
            )
        )
    )
    monkeypatch.setattr(patients, "engine", fake_engine)

    result = patients.find_patient_by_phone_read_only(
        " 573000000001 "
    )

    assert result == {
        "id": "patient-1",
        "telefono": "573000000001",
        "opt_out": True,
    }
    assert fake_engine.connect_calls == 1
    assert fake_engine.begin_calls == 0
    assert len(fake_engine.connection.calls) == 1

    sql, params = fake_engine.connection.calls[0]
    normalized_sql = " ".join(sql.upper().split())

    assert normalized_sql.startswith("SELECT")
    assert "FROM PATIENTS" in normalized_sql
    assert "WHERE TELEFONO = :TELEFONO" in normalized_sql
    assert "INSERT" not in normalized_sql
    assert "UPDATE" not in normalized_sql
    assert "DELETE" not in normalized_sql
    assert params == {"telefono": "573000000001"}


def test_find_patient_by_phone_read_only_returns_none_when_absent(
    monkeypatch,
):
    fake_engine = FakeEngine(FakeResult(None))
    monkeypatch.setattr(patients, "engine", fake_engine)

    result = patients.find_patient_by_phone_read_only(
        "573000000099"
    )

    assert result is None
    assert fake_engine.connect_calls == 1
    assert fake_engine.begin_calls == 0
    assert len(fake_engine.connection.calls) == 1

    sql, _ = fake_engine.connection.calls[0]
    normalized_sql = " ".join(sql.upper().split())

    assert normalized_sql.startswith("SELECT")
    assert "INSERT" not in normalized_sql
    assert "UPDATE" not in normalized_sql
    assert "DELETE" not in normalized_sql


def test_find_patient_by_phone_read_only_requires_phone(
    monkeypatch,
):
    fake_engine = FakeEngine(FakeResult(None))
    monkeypatch.setattr(patients, "engine", fake_engine)

    with pytest.raises(
        ValueError,
        match="telefono is required",
    ):
        patients.find_patient_by_phone_read_only("   ")

    assert fake_engine.connect_calls == 0
    assert fake_engine.begin_calls == 0
    assert fake_engine.connection.calls == []
