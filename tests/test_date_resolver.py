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


def test_resolver_adds_human_readable_requested_date_text_for_tomorrow():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    result = resolve_requested_date(
        "Quiero cita mañana",
        now=datetime(2026, 5, 13, 10, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-14"
    assert result.fecha_solicitada_texto == "jueves 14 de mayo"
    assert result.is_weekend is False
    assert result.is_colombia_holiday is False
    assert result.colombia_holiday_name is None


def test_resolver_marks_sunday_as_weekend_and_clears_slots():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    result = resolve_requested_date(
        "Quiero cita mañana",
        now=datetime(2026, 5, 16, 10, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-17"
    assert result.fecha_solicitada_texto == "domingo 17 de mayo"
    assert result.is_weekend is True
    assert result.is_colombia_holiday is False
    assert result.es_dia_disponible is False
    assert result.slots_candidatos == []


def test_resolver_marks_colombian_holiday_and_clears_slots():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    result = resolve_requested_date(
        "Quiero cita el lunes",
        now=datetime(2026, 5, 17, 10, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-18"
    assert result.fecha_solicitada_texto == "lunes 18 de mayo"
    assert result.is_weekend is False
    assert result.is_colombia_holiday is True
    assert result.colombia_holiday_name == "Ascensión de Jesús"
    assert result.es_dia_disponible is False
    assert result.slots_candidatos == []

def test_p6f91419_resolver_supports_maniana_variant_for_tomorrow_afternoon():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    result = resolve_requested_date(
        "Maniana en la tarde",
        now=datetime(2026, 5, 13, 10, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-14"
    assert result.fecha_solicitada_texto == "jueves 14 de mayo"
    assert result.es_dia_disponible is True
    assert result.slots_candidatos == [
        "3:00 p. m.–5:00 p. m.",
        "5:00 p. m.–7:00 p. m.",
    ]


def test_p6f91419_resolver_supports_maniana_variant_for_tomorrow_morning():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    result = resolve_requested_date(
        "Maniana en la maniana",
        now=datetime(2026, 5, 13, 10, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert result.fecha_solicitada.isoformat() == "2026-05-14"
    assert result.fecha_solicitada_texto == "jueves 14 de mayo"
    assert result.es_dia_disponible is True
    assert result.slots_candidatos == [
        "3:00 p. m.–5:00 p. m.",
        "5:00 p. m.–7:00 p. m.",
    ]


def test_p6f91419_time_window_without_date_does_not_resolve_requested_date():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    result = resolve_requested_date(
        "En la maniana",
        now=datetime(2026, 5, 13, 10, 0, tzinfo=ZoneInfo("America/Bogota")),
    )

    assert result.fecha_solicitada is None
    assert result.fecha_solicitada_texto is None
    assert result.es_dia_disponible is False
    assert result.slots_candidatos == []
