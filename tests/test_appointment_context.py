from types import SimpleNamespace

from app.services.appointment_context import (
    apply_appointment_context_to_state,
    capture_appointment_context_from_state,
    should_clear_appointment_context,
)


def test_capture_appointment_context_from_fecha_cita_state():
    state = SimpleNamespace(
        intent="fecha_cita",
        nuevo_estado="ST_CITA_FRANJA",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
        colombia_holiday_name=None,
    )

    context = capture_appointment_context_from_state(state)

    assert context == {
        "fecha_solicitada": "2026-05-29",
        "fecha_solicitada_texto": "viernes 29 de mayo",
        "slots_candidatos": ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
    }


def test_capture_returns_none_when_not_fecha_cita():
    state = SimpleNamespace(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        fecha_solicitada="2026-05-29",
    )

    assert capture_appointment_context_from_state(state) is None


def test_capture_returns_none_when_fecha_missing():
    state = SimpleNamespace(
        intent="fecha_cita",
        nuevo_estado="ST_CITA_FRANJA",
        fecha_solicitada=None,
    )

    assert capture_appointment_context_from_state(state) is None


def test_apply_appointment_context_to_state_restores_missing_fecha_context():
    state = SimpleNamespace(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        fecha_solicitada=None,
        fecha_solicitada_texto=None,
        slots_candidatos=[],
        es_dia_disponible=None,
        is_weekend=None,
        is_colombia_holiday=None,
        colombia_holiday_name=None,
    )

    context = {
        "fecha_solicitada": "2026-05-29",
        "fecha_solicitada_texto": "viernes 29 de mayo",
        "slots_candidatos": ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
    }

    result = apply_appointment_context_to_state(state, context)

    assert result.fecha_solicitada == "2026-05-29"
    assert result.fecha_solicitada_texto == "viernes 29 de mayo"
    assert result.slots_candidatos == ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."]
    assert result.es_dia_disponible is True
    assert result.is_weekend is False
    assert result.is_colombia_holiday is False
    assert result.colombia_holiday_name is None


def test_apply_appointment_context_does_not_override_existing_fecha():
    state = SimpleNamespace(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        fecha_solicitada="2026-05-30",
        fecha_solicitada_texto="sábado 30 de mayo",
        slots_candidatos=["existing"],
        es_dia_disponible=False,
        is_weekend=True,
        is_colombia_holiday=False,
        colombia_holiday_name=None,
    )

    context = {
        "fecha_solicitada": "2026-05-29",
        "fecha_solicitada_texto": "viernes 29 de mayo",
        "slots_candidatos": ["3:00 p. m.–5:00 p. m."],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
    }

    result = apply_appointment_context_to_state(state, context)

    assert result.fecha_solicitada == "2026-05-30"
    assert result.fecha_solicitada_texto == "sábado 30 de mayo"
    assert result.slots_candidatos == ["existing"]


def test_apply_appointment_context_ignores_invalid_context_without_fecha():
    state = SimpleNamespace(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        fecha_solicitada=None,
    )

    result = apply_appointment_context_to_state(state, {"slots_candidatos": ["3:00 p. m.–5:00 p. m."]})

    assert result.fecha_solicitada is None


def test_should_clear_appointment_context_after_successful_persistence():
    state = SimpleNamespace(opt_out=False)

    assert should_clear_appointment_context(state, persisted=True) is True


def test_should_clear_appointment_context_when_opt_out_true():
    state = SimpleNamespace(opt_out=True)

    assert should_clear_appointment_context(state, persisted=False) is True


def test_should_not_clear_appointment_context_without_persistence_or_opt_out():
    state = SimpleNamespace(opt_out=False)

    assert should_clear_appointment_context(state, persisted=False) is False
