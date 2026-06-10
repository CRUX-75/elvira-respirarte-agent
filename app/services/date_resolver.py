import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.calendar_service import CalendarService


BOGOTA_TIMEZONE = "America/Bogota"

WEEKDAY_NAMES_ES = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}

MONTH_NAMES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

WEEKDAY_WORDS_ES = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}

COLOMBIA_HOLIDAYS_2026 = {
    date(2026, 1, 1): "Año Nuevo",
    date(2026, 1, 12): "Día de los Reyes Magos",
    date(2026, 3, 23): "Día de San José",
    date(2026, 4, 2): "Jueves Santo",
    date(2026, 4, 3): "Viernes Santo",
    date(2026, 5, 1): "Día del Trabajo",
    date(2026, 5, 18): "Ascensión de Jesús",
    date(2026, 6, 8): "Corpus Christi",
    date(2026, 6, 15): "Sagrado Corazón de Jesús",
    date(2026, 6, 29): "San Pedro y San Pablo",
    date(2026, 7, 20): "Día de la Independencia",
    date(2026, 8, 7): "Batalla de Boyacá",
    date(2026, 8, 17): "Asunción de la Virgen",
    date(2026, 10, 12): "Día de la Raza",
    date(2026, 11, 2): "Todos los Santos",
    date(2026, 11, 16): "Independencia de Cartagena",
    date(2026, 12, 8): "Inmaculada Concepción",
    date(2026, 12, 25): "Navidad",
}


@dataclass(frozen=True)
class RelativeDateResolution:
    fecha_actual_colombia: date
    fecha_solicitada: date | None
    fecha_solicitada_texto: str | None
    dia_semana_solicitado: str | None
    es_dia_disponible: bool
    slots_candidatos: list[str]
    is_weekend: bool
    is_colombia_holiday: bool
    colombia_holiday_name: str | None
    source: str = "deterministic_relative_date_resolver"


def _normalize_text(text: str | None) -> str:
    normalized = (text or "").strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    return normalized


NEXT_WEEK_MARKERS = (
    "proximo",
    "proxima",
    "siguiente",
    "que viene",
)


def _has_explicit_next_week_marker(normalized_message: str) -> bool:
    return any(marker in normalized_message for marker in NEXT_WEEK_MARKERS)


def _resolve_weekday_reference(
    base_date: date,
    target_weekday: int,
    *,
    explicit_next_week: bool = False,
) -> date:
    days_ahead = (target_weekday - base_date.weekday()) % 7
    if days_ahead == 0 and explicit_next_week:
        days_ahead = 7

    return base_date + timedelta(days=days_ahead)


def _format_requested_date_text(requested_date: date) -> str:
    weekday = WEEKDAY_NAMES_ES[requested_date.weekday()]
    month = MONTH_NAMES_ES[requested_date.month]
    return f"{weekday} {requested_date.day} de {month}"


def get_today_colombia(now: datetime | None = None) -> date:
    if now is None:
        now = datetime.now(ZoneInfo(BOGOTA_TIMEZONE))

    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo(BOGOTA_TIMEZONE))
    else:
        now = now.astimezone(ZoneInfo(BOGOTA_TIMEZONE))

    return now.date()


def resolve_requested_date(
    message: str,
    *,
    now: datetime | None = None,
    calendar_service: CalendarService | None = None,
) -> RelativeDateResolution:
    normalized_message = _normalize_text(message)
    fecha_actual_colombia = get_today_colombia(now)

    requested_date: date | None = None

    if (
        "pasado mañana" in normalized_message
        or "pasado manana" in normalized_message
        or "pasado maniana" in normalized_message
    ):
        requested_date = fecha_actual_colombia + timedelta(days=2)
    elif (
        re.search(r"\bmanana\b", normalized_message)
        or (
            re.search(r"\bmaniana\b", normalized_message)
            and not re.fullmatch(r"(en|por) la maniana", normalized_message)
        )
    ):
        requested_date = fecha_actual_colombia + timedelta(days=1)
    elif "hoy" in normalized_message:
        requested_date = fecha_actual_colombia
    else:
        for weekday_word, weekday_index in WEEKDAY_WORDS_ES.items():
            if weekday_word in normalized_message:
                requested_date = _resolve_weekday_reference(
                    fecha_actual_colombia,
                    weekday_index,
                    explicit_next_week=_has_explicit_next_week_marker(normalized_message),
                )
                break

    if requested_date is None:
        return RelativeDateResolution(
            fecha_actual_colombia=fecha_actual_colombia,
            fecha_solicitada=None,
            fecha_solicitada_texto=None,
            dia_semana_solicitado=None,
            es_dia_disponible=False,
            slots_candidatos=[],
            is_weekend=False,
            is_colombia_holiday=False,
            colombia_holiday_name=None,
        )

    is_weekend = requested_date.weekday() in {5, 6}
    colombia_holiday_name = COLOMBIA_HOLIDAYS_2026.get(requested_date)
    is_colombia_holiday = colombia_holiday_name is not None

    service = calendar_service or CalendarService()
    slots = service.build_default_slots(requested_date)
    slot_labels = [slot.label for slot in slots]

    if is_weekend or is_colombia_holiday:
        slot_labels = []

    return RelativeDateResolution(
        fecha_actual_colombia=fecha_actual_colombia,
        fecha_solicitada=requested_date,
        fecha_solicitada_texto=_format_requested_date_text(requested_date),
        dia_semana_solicitado=WEEKDAY_NAMES_ES[requested_date.weekday()],
        es_dia_disponible=bool(slot_labels),
        slots_candidatos=slot_labels,
        is_weekend=is_weekend,
        is_colombia_holiday=is_colombia_holiday,
        colombia_holiday_name=colombia_holiday_name,
    )
