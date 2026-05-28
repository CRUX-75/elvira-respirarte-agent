from app.graph.state import ElviraState
from app.services.appointment_request_runtime import (
    decide_appointment_request_persistence,
)


def make_state(
    *,
    intent: str = "general",
    nuevo_estado: str = "ST_GENERAL",
    next_action: str = "answer_general",
    fecha_solicitada: str | None = None,
    slots_candidatos: list[str] | None = None,
    mensaje_original: str = "Hola",
    is_weekend: bool = False,
    is_colombia_holiday: bool = False,
    es_dia_disponible: bool | None = True,
) -> ElviraState:
    return ElviraState(
        telefono="573001112233",
        mensaje_original=mensaje_original,
        sanitized_input=mensaje_original.lower(),
        nombre="Paciente Test",
        estado_actual="ST_INIT",
        intent=intent,
        nuevo_estado=nuevo_estado,
        next_action=next_action,
        respuesta="Respuesta de prueba",
        fecha_solicitada=fecha_solicitada,
        slots_candidatos=slots_candidatos or [],
        is_weekend=is_weekend,
        is_colombia_holiday=is_colombia_holiday,
        es_dia_disponible=es_dia_disponible,
    )


def test_skips_general_message():
    decision = decide_appointment_request_persistence(
        state=make_state(intent="general"),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-001",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_non_appointment_intent"


def test_skips_servicios_message():
    decision = decide_appointment_request_persistence(
        state=make_state(intent="servicios"),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-002",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_non_appointment_intent"


def test_skips_horarios_message():
    decision = decide_appointment_request_persistence(
        state=make_state(intent="horarios"),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-003",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_non_appointment_intent"


def test_skips_pago_message():
    decision = decide_appointment_request_persistence(
        state=make_state(intent="pago"),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-004",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_non_appointment_intent"


def test_skips_urgencia_message():
    decision = decide_appointment_request_persistence(
        state=make_state(intent="urgencia"),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-005",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_non_appointment_intent"


def test_skips_optout_message():
    decision = decide_appointment_request_persistence(
        state=make_state(intent="optout"),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-006",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_non_appointment_intent"


def test_skips_initial_cita_intent():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="cita",
            nuevo_estado="ST_CITA_FECHA",
            next_action="ask_preferred_date",
            mensaje_original="Quiero una cita",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-007",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_initial_cita_intent"


def test_skips_fecha_cita_waiting_for_time():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="fecha_cita",
            nuevo_estado="ST_CITA_FRANJA",
            next_action="ask_preferred_time",
            fecha_solicitada="2026-05-29",
            mensaje_original="Mañana",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-008",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_fecha_cita_waiting_for_time"


def test_skips_hora_cita_without_fecha_solicitada():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada=None,
            slots_candidatos=["14:00-16:00"],
            mensaje_original="En la tarde",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-009",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_missing_fecha_solicitada"


def test_skips_weekend_date():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-31",
            slots_candidatos=["14:00-16:00"],
            mensaje_original="En la tarde",
            is_weekend=True,
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-010",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_weekend"


def test_skips_colombia_holiday():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-07-20",
            slots_candidatos=["14:00-16:00"],
            mensaje_original="En la tarde",
            is_colombia_holiday=True,
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-011",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_colombia_holiday"


def test_skips_unavailable_date():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=["14:00-16:00"],
            mensaje_original="En la tarde",
            es_dia_disponible=False,
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-012",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_unavailable_date"


def test_allows_hora_cita_ready_for_human_review():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="A las 3",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-013",
    )

    assert decision.should_persist is True
    assert decision.reason == "allowed_hora_cita_ready_for_human_review"
    assert decision.telefono == "573001112233"
    assert decision.nombre_paciente == "Paciente Test"
    assert decision.intent_origen == "hora_cita"
    assert decision.canal_origen == "whatsapp"
    assert decision.estado_solicitud == "pendiente_confirmacion"
    assert decision.fecha_solicitada == "2026-05-29"
    assert decision.franja_solicitada == "3:00 p. m.–5:00 p. m."
    assert decision.hora_solicitada_texto == "A las 3"
    assert decision.source_interaction_id == "wamid.test-013"


def test_allows_hora_cita_without_nombre():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="A las 5",
        ),
        telefono="573001112233",
        nombre=None,
        source_interaction_id="wamid.test-014",
    )

    assert decision.should_persist is True
    assert decision.nombre_paciente is None
    assert decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_skips_blank_telefono():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=["14:00-16:00"],
            mensaje_original="En la tarde",
        ),
        telefono="   ",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-015",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_missing_telefono"


def test_skips_wrong_state_or_action():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_FRANJA",
            next_action="ask_preferred_time",
            fecha_solicitada="2026-05-29",
            slots_candidatos=["14:00-16:00"],
            mensaje_original="En la tarde",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-016",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_wrong_state_or_action"


def test_p6f91425_maps_concrete_three_oclock_to_first_slot():
    decision = decide_appointment_request_persistence(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
        mensaje_original="se puede a las 3?",
    )

    assert decision.should_persist is True
    assert decision.franja_solicitada == "3:00 p. m.–5:00 p. m."


def test_p6f91425_maps_concrete_five_oclock_to_second_slot():
    decision = decide_appointment_request_persistence(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
        mensaje_original="se puede a las 5?",
    )

    assert decision.should_persist is True
    assert decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_p6f91425_maps_ordinal_selection_to_expected_slot():
    first_decision = decide_appointment_request_persistence(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
        mensaje_original="la primera franja",
    )

    second_decision = decide_appointment_request_persistence(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
        mensaje_original="el segundo horario",
    )

    assert first_decision.should_persist is True
    assert first_decision.franja_solicitada == "3:00 p. m.–5:00 p. m."

    assert second_decision.should_persist is True
    assert second_decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_p6f91425_blocks_unsupported_loose_hour_inside_slot():
    decision = decide_appointment_request_persistence(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
        mensaje_original="se puede a las 4?",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_unsupported_slot_selection"
    assert decision.franja_solicitada is None


def test_p6f91425_blocks_unsupported_loose_hour_and_does_not_fallback_to_first_slot():
    decision = decide_appointment_request_persistence(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        es_dia_disponible=True,
        is_weekend=False,
        is_colombia_holiday=False,
        mensaje_original="a las 6",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_unsupported_slot_selection"
    assert decision.franja_solicitada is None


def test_p6f91425_maps_concrete_three_oclock_to_first_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="se puede a las 3?",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-001",
    )

    assert decision.should_persist is True
    assert decision.franja_solicitada == "3:00 p. m.–5:00 p. m."


def test_p6f91425_maps_concrete_five_oclock_to_second_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="se puede a las 5?",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-002",
    )

    assert decision.should_persist is True
    assert decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_p6f91425_maps_ordinal_selection_to_expected_slot():
    first_decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="la primera franja",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-003",
    )

    second_decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="el segundo horario",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-004",
    )

    assert first_decision.should_persist is True
    assert first_decision.franja_solicitada == "3:00 p. m.–5:00 p. m."

    assert second_decision.should_persist is True
    assert second_decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_p6f91425_blocks_unsupported_loose_hour_inside_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="se puede a las 4?",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-005",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_unsupported_slot_selection"
    assert decision.franja_solicitada is None


def test_p6f91425_blocks_unsupported_loose_hour_and_does_not_fallback_to_first_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="a las 6",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-006",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_unsupported_slot_selection"
    assert decision.franja_solicitada is None


def test_p6f91425_maps_concrete_three_oclock_to_first_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="se puede a las 3?",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-001",
    )

    assert decision.should_persist is True
    assert decision.franja_solicitada == "3:00 p. m.–5:00 p. m."


def test_p6f91425_maps_concrete_five_oclock_to_second_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="se puede a las 5?",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-002",
    )

    assert decision.should_persist is True
    assert decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_p6f91425_maps_ordinal_selection_to_expected_slot():
    first_decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="la primera franja",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-003",
    )

    second_decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="el segundo horario",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-004",
    )

    assert first_decision.should_persist is True
    assert first_decision.franja_solicitada == "3:00 p. m.–5:00 p. m."

    assert second_decision.should_persist is True
    assert second_decision.franja_solicitada == "5:00 p. m.–7:00 p. m."


def test_p6f91425_blocks_unsupported_loose_hour_inside_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="se puede a las 4?",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-005",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_unsupported_slot_selection"
    assert decision.franja_solicitada is None


def test_p6f91425_blocks_unsupported_loose_hour_and_does_not_fallback_to_first_slot():
    decision = decide_appointment_request_persistence(
        state=make_state(
            intent="hora_cita",
            nuevo_estado="ST_CITA_PENDIENTE",
            next_action="confirm_appointment_request",
            fecha_solicitada="2026-05-29",
            slots_candidatos=[
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            mensaje_original="a las 6",
        ),
        telefono="573001112233",
        nombre="Paciente Test",
        source_interaction_id="wamid.test-p6f91425-006",
    )

    assert decision.should_persist is False
    assert decision.reason == "skipped_unsupported_slot_selection"
    assert decision.franja_solicitada is None
