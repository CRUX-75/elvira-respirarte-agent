from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.date_resolver import resolve_requested_date


BOGOTA = ZoneInfo("America/Bogota")


def test_friday_colombia_tomorrow_resolves_to_saturday():
    result = resolve_requested_date(
        "Mañana en la tarde.",
        now=datetime(2026, 5, 8, 10, 0, tzinfo=BOGOTA),
    )

    assert result.fecha_actual_colombia.isoformat() == "2026-05-08"
    assert result.fecha_solicitada.isoformat() == "2026-05-09"
    assert result.dia_semana_solicitado == "sábado"


def test_saturday_does_not_offer_home_appointment_slots():
    result = resolve_requested_date(
        "Mañana en la tarde.",
        now=datetime(2026, 5, 8, 10, 0, tzinfo=BOGOTA),
    )

    assert result.dia_semana_solicitado == "sábado"
    assert result.es_dia_disponible is False
    assert result.slots_candidatos == []


def test_wednesday_returns_only_one_candidate_slot():
    result = resolve_requested_date(
        "El miércoles en la tarde.",
        now=datetime(2026, 5, 8, 10, 0, tzinfo=BOGOTA),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-13"
    assert result.dia_semana_solicitado == "miércoles"
    assert result.es_dia_disponible is True
    assert result.slots_candidatos == ["3:00 p. m.–5:00 p. m."]


def test_monday_returns_two_candidate_slots():
    result = resolve_requested_date(
        "El lunes en la tarde.",
        now=datetime(2026, 5, 8, 10, 0, tzinfo=BOGOTA),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-11"
    assert result.dia_semana_solicitado == "lunes"
    assert result.es_dia_disponible is True
    assert result.slots_candidatos == ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."]


def test_sunday_returns_no_candidate_slots():
    result = resolve_requested_date(
        "El domingo en la tarde.",
        now=datetime(2026, 5, 8, 10, 0, tzinfo=BOGOTA),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-10"
    assert result.dia_semana_solicitado == "domingo"
    assert result.es_dia_disponible is False
    assert result.slots_candidatos == []


def test_tomorrow_afternoon_does_not_depend_on_llm_interpretation():
    result = resolve_requested_date(
        "mañana en la tarde",
        now=datetime(2026, 5, 8, 23, 30, tzinfo=BOGOTA),
    )

    assert result.fecha_actual_colombia.isoformat() == "2026-05-08"
    assert result.fecha_solicitada.isoformat() == "2026-05-09"
    assert result.dia_semana_solicitado == "sábado"
    assert result.source == "deterministic_relative_date_resolver"
