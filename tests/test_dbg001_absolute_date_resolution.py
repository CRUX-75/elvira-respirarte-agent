from datetime import datetime
from zoneinfo import ZoneInfo

import app.graph.nodes as nodes
from app.graph.state import ElviraState
from app.services.date_resolver import resolve_requested_date
from app.services.intent import classify_intent


BOGOTA = ZoneInfo("America/Bogota")
JULY_17_2026 = datetime(2026, 7, 17, 10, 0, tzinfo=BOGOTA)
JULY_18_2026 = datetime(2026, 7, 18, 10, 0, tzinfo=BOGOTA)


def run_date_flow(
    monkeypatch,
    *,
    message: str,
    current_state: str,
    now: datetime,
) -> ElviraState:
    monkeypatch.setattr(
        nodes,
        "_load_schedule_rows_for_date_resolution",
        lambda: None,
    )

    state = ElviraState(
        telefono="573000000001",
        mensaje_original=message,
        sanitized_input="",
        nombre="DBG-001",
        estado_actual=current_state,
        opt_out=False,
    )

    state = nodes.node_sanitize_input(state)
    state = nodes.node_classify_intent(state)
    state = nodes.node_resolve_date_context(state, now=now)
    state = nodes.node_transition_state(state)

    return state


def test_resolver_infers_current_year_for_textual_date_without_year():
    result = resolve_requested_date(
        "Necesito una cita el 23 de julio",
        now=JULY_18_2026,
    )

    assert result.fecha_solicitada is not None
    assert result.fecha_solicitada.isoformat() == "2026-07-23"
    assert result.fecha_solicitada_texto == "jueves 23 de julio"


def test_resolver_accepts_numeric_day_month_year():
    result = resolve_requested_date(
        "18/07/2026",
        now=JULY_17_2026,
    )

    assert result.fecha_solicitada is not None
    assert result.fecha_solicitada.isoformat() == "2026-07-18"
    assert result.is_weekend is True
    assert result.es_dia_disponible is False


def test_router_classifies_textual_absolute_date_in_date_state():
    assert (
        classify_intent("18 de julio", "ST_CITA_FECHA")
        == "fecha_cita"
    )


def test_router_classifies_numeric_absolute_date_in_date_state():
    assert (
        classify_intent("18/07/2026", "ST_CITA_FECHA")
        == "fecha_cita"
    )


def test_embedded_absolute_date_advances_appointment_to_slot_selection(
    monkeypatch,
):
    result = run_date_flow(
        monkeypatch,
        message="Necesito una cita el 23 de julio",
        current_state="ST_INIT",
        now=JULY_18_2026,
    )

    assert result.intent == "cita"
    assert result.fecha_solicitada == "2026-07-23"
    assert result.fecha_solicitada_texto == "jueves 23 de julio"
    assert result.es_dia_disponible is True
    assert result.nuevo_estado == "ST_CITA_FRANJA"
    assert result.next_action == "ask_preferred_time"


def test_standalone_numeric_weekend_date_is_recognized_and_rejected(
    monkeypatch,
):
    result = run_date_flow(
        monkeypatch,
        message="18/07/2026",
        current_state="ST_CITA_FECHA",
        now=JULY_17_2026,
    )

    assert result.intent == "fecha_cita"
    assert result.fecha_solicitada == "2026-07-18"
    assert result.is_weekend is True
    assert result.es_dia_disponible is False
    assert result.nuevo_estado == "ST_CITA_FECHA"
    assert result.next_action == "ask_preferred_date"
    assert result.state_reason == "unavailable_date_guard"
