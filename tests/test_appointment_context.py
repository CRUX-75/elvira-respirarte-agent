from types import SimpleNamespace

from app.services.appointment_context import (
    apply_appointment_context_to_state,
    apply_pending_exact_hour_confirmation_to_state,
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


def test_apply_appointment_context_overrides_contradictory_hora_cita_state():
    state = SimpleNamespace(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        fecha_solicitada="2026-05-30",
        fecha_solicitada_texto="sábado 30 de mayo",
        slots_candidatos=["existing"],
        es_dia_disponible=False,
        is_weekend=True,
        is_colombia_holiday=True,
        colombia_holiday_name="Corpus Christi",
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
    assert result.slots_candidatos == [
        "3:00 p. m.–5:00 p. m.",
        "5:00 p. m.–7:00 p. m.",
    ]
    assert result.es_dia_disponible is True
    assert result.is_weekend is False
    assert result.is_colombia_holiday is False
    assert result.colombia_holiday_name is None


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


def test_capture_pending_exact_hour_confirmation_context():
    class State:
        intent = "hora_cita"
        nuevo_estado = "ST_CITA_FRANJA"
        next_action = "ask_confirm_exact_hour_as_slot"
        fecha_solicitada = "2026-06-01"
        fecha_solicitada_texto = "lunes 1 de junio"
        slots_candidatos = [
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ]
        es_dia_disponible = True
        is_weekend = False
        is_colombia_holiday = False
        colombia_holiday_name = None
        mensaje_original = "se puede a las 5?"

    class Decision:
        reason = "requires_exact_hour_franja_confirmation"
        franja_solicitada = "5:00 p. m.–7:00 p. m."

    from app.services.appointment_context import (
        capture_pending_exact_hour_confirmation_context,
    )

    context = capture_pending_exact_hour_confirmation_context(
        State(),
        Decision(),
    )

    assert context == {
        "fecha_solicitada": "2026-06-01",
        "fecha_solicitada_texto": "lunes 1 de junio",
        "slots_candidatos": [
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
        "pending_exact_hour_franja": "5:00 p. m.–7:00 p. m.",
        "pending_exact_hour_text": "se puede a las 5?",
        "pending_exact_hour_requires_confirmation": True,
    }


def test_apply_pending_exact_hour_confirmation_ignores_affirmative_state():
    class State:
        intent = "general"
        nuevo_estado = "ST_CITA_FRANJA"
        next_action = "answer_general"
        mensaje_original = "si"
        fecha_solicitada = None
        fecha_solicitada_texto = None
        slots_candidatos = []
        es_dia_disponible = False
        is_weekend = False
        is_colombia_holiday = False
        colombia_holiday_name = None

    context = {
        "fecha_solicitada": "2026-06-01",
        "fecha_solicitada_texto": "lunes 1 de junio",
        "slots_candidatos": [
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
        "pending_exact_hour_franja": "5:00 p. m.–7:00 p. m.",
        "pending_exact_hour_text": "se puede a las 5?",
        "pending_exact_hour_requires_confirmation": True,
    }

    from app.services.appointment_context import (
        apply_pending_exact_hour_confirmation_to_state,
    )

    state = apply_pending_exact_hour_confirmation_to_state(State(), context)

    assert state.intent == "general"
    assert state.nuevo_estado == "ST_CITA_FRANJA"
    assert state.next_action == "answer_general"
    assert state.fecha_solicitada is None

def test_apply_pending_exact_hour_confirmation_ignores_non_affirmative_message():
    class State:
        intent = "general"
        nuevo_estado = "ST_CITA_FRANJA"
        next_action = "answer_general"
        mensaje_original = "no"
        fecha_solicitada = None

    context = {
        "fecha_solicitada": "2026-06-01",
        "pending_exact_hour_franja": "5:00 p. m.–7:00 p. m.",
        "pending_exact_hour_requires_confirmation": True,
    }

    from app.services.appointment_context import (
        apply_pending_exact_hour_confirmation_to_state,
    )

    state = apply_pending_exact_hour_confirmation_to_state(State(), context)

    assert state.intent == "general"
    assert state.nuevo_estado == "ST_CITA_FRANJA"
    assert state.next_action == "answer_general"


def test_apply_pending_exact_hour_confirmation_ignores_real_elvira_state():
    from app.graph.state import ElviraState
    from app.services.appointment_context import (
        apply_pending_exact_hour_confirmation_to_state,
    )

    state = ElviraState(
        telefono="573001112233",
        nombre="Paciente Test",
        mensaje_original="si",
        sanitized_input="si",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="general",
        next_action="answer_general",
    )

    context = {
        "fecha_solicitada": "2026-06-01",
        "fecha_solicitada_texto": "lunes 1 de junio",
        "slots_candidatos": [
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
        "pending_exact_hour_franja": "5:00 p. m.–7:00 p. m.",
        "pending_exact_hour_text": "se puede a las 5?",
        "pending_exact_hour_requires_confirmation": True,
    }

    result = apply_pending_exact_hour_confirmation_to_state(state, context)

    assert result.intent == "general"
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "answer_general"
    assert result.fecha_solicitada is None
    assert getattr(result, "franja_solicitada", None) is None
    assert getattr(result, "state_reason", None) != "confirmed_pending_exact_hour_franja"

def test_apply_pending_exact_hour_confirmation_ignores_vague_registered_franja_when_state_already_pending():
    class State:
        intent = "hora_cita"
        nuevo_estado = "ST_CITA_PENDIENTE"
        next_action = "confirm_appointment_request"
        mensaje_original = "Sí, registre esa franja"
        fecha_solicitada = None
        fecha_solicitada_texto = None
        slots_candidatos = []
        es_dia_disponible = None
        is_weekend = None
        is_colombia_holiday = None
        colombia_holiday_name = None
        franja_solicitada = None
        state_reason = None

    context = {
        "fecha_solicitada": "2026-06-09",
        "fecha_solicitada_texto": "martes 9 de junio",
        "slots_candidatos": [
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
        "pending_exact_hour_franja": "3:00 p. m.–5:00 p. m.",
        "pending_exact_hour_text": "A las 3",
        "pending_exact_hour_requires_confirmation": True,
    }

    state = apply_pending_exact_hour_confirmation_to_state(State(), context)

    assert state.intent == "hora_cita"
    assert state.nuevo_estado == "ST_CITA_PENDIENTE"
    assert state.next_action == "confirm_appointment_request"
    assert state.state_reason is None
    assert state.fecha_solicitada is None
    assert state.franja_solicitada is None



def test_apply_appointment_context_restores_missing_slots_when_fecha_already_present():
    state = SimpleNamespace(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=[],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
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
    assert result.slots_candidatos == [
        "3:00 p. m.–5:00 p. m.",
        "5:00 p. m.–7:00 p. m.",
    ]
