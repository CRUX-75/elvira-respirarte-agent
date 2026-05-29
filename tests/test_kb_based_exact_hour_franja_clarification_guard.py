from app.graph.state import ElviraState
from app.services.appointment_request_runtime import (
    decide_appointment_request_persistence,
    resolve_requested_slot_from_message,
)


def test_exact_hour_inside_kb_slot_is_detected_as_slot_but_must_not_persist_yet():
    """
    P6-F.9.14.27 RED

    Current behavior resolves "a las 5" to the KB franja 5:00 p. m.–7:00 p. m.
    New required behavior: exact-hour messages inside a KB franja must trigger
    clarification first, not AppointmentRequest persistence.
    """
    state = ElviraState(
        telefono="+573001112233",
        sanitized_input="se puede a las 5?",
        mensaje_original="se puede a las 5?",
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        is_weekend=False,
        is_colombia_holiday=False,
        es_dia_disponible=True,
    )

    decision = decide_appointment_request_persistence(
        state=state,
        telefono="+573001112233",
        nombre="Paciente Test",
        source_interaction_id="test-interaction-001",
    )

    assert decision.should_persist is False
    assert decision.reason == "requires_exact_hour_franja_confirmation"
    assert decision.franja_solicitada == "5:00 p. m.–7:00 p. m."
    assert decision.hora_solicitada_texto == "se puede a las 5?"


def test_confirmed_visible_kb_franja_can_persist():
    """
    If the patient explicitly confirms/selects the KB franja, persistence is allowed.
    """
    state = ElviraState(
        telefono="+573001112233",
        sanitized_input="sí, la franja de 5 a 7 está bien",
        mensaje_original="sí, la franja de 5 a 7 está bien",
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        is_weekend=False,
        is_colombia_holiday=False,
        es_dia_disponible=True,
    )

    decision = decide_appointment_request_persistence(
        state=state,
        telefono="+573001112233",
        nombre="Paciente Test",
        source_interaction_id="test-interaction-002",
    )

    assert decision.should_persist is True
    assert decision.reason == "allowed_hora_cita_ready_for_human_review"
    assert decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_exact_hour_outside_visible_kb_slots_does_not_resolve_to_slot():
    """
    Exact hour outside visible KB slots must not resolve to any franja.
    Runtime should therefore avoid persistence.
    """
    resolved = resolve_requested_slot_from_message(
        "Puede ser a las 8 de la noche?",
        [
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
    )

    assert resolved is None
