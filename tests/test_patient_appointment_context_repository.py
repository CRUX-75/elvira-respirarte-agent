import pytest

from app.repositories import patients


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append(
            {
                "sql": str(statement),
                "params": params or {},
            }
        )
        return FakeResult()


class FakeEngine:
    def __init__(self):
        self.conn = FakeConnection()

    def begin(self):
        return self

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


def test_update_patient_appointment_context_persists_json_context(monkeypatch):
    fake_engine = FakeEngine()
    monkeypatch.setattr(patients, "engine", fake_engine)

    context = {
        "fecha_solicitada": "2026-05-29",
        "fecha_solicitada_texto": "viernes 29 de mayo",
        "slots_candidatos": ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
    }

    patients.update_patient_appointment_context("573001119991", context)

    assert len(fake_engine.conn.calls) == 1

    call = fake_engine.conn.calls[0]

    assert "UPDATE patients" in call["sql"]
    assert "appointment_context = :appointment_context" in call["sql"]
    assert "updated_at = NOW()" in call["sql"]
    assert "telefono = :telefono" in call["sql"]

    assert call["params"]["telefono"] == "573001119991"
    assert call["params"]["appointment_context"] == context


def test_update_patient_appointment_context_requires_telefono():
    with pytest.raises(ValueError, match="telefono is required"):
        patients.update_patient_appointment_context("", {"fecha_solicitada": "2026-05-29"})


def test_update_patient_appointment_context_requires_context():
    with pytest.raises(ValueError, match="appointment_context is required"):
        patients.update_patient_appointment_context("573001119991", None)


def test_clear_patient_appointment_context_sets_context_to_null(monkeypatch):
    fake_engine = FakeEngine()
    monkeypatch.setattr(patients, "engine", fake_engine)

    patients.clear_patient_appointment_context("573001119991")

    assert len(fake_engine.conn.calls) == 1

    call = fake_engine.conn.calls[0]

    assert "UPDATE patients" in call["sql"]
    assert "appointment_context = NULL" in call["sql"]
    assert "updated_at = NOW()" in call["sql"]
    assert "telefono = :telefono" in call["sql"]

    assert call["params"]["telefono"] == "573001119991"


def test_clear_patient_appointment_context_requires_telefono():
    with pytest.raises(ValueError, match="telefono is required"):
        patients.clear_patient_appointment_context("")
