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


@dataclass(frozen=True)
class RelativeDateResolution:
    fecha_actual_colombia: date
    fecha_solicitada: date | None
    dia_semana_solicitado: str | None
    es_dia_disponible: bool
    slots_candidatos: list[str]
    source: str = "deterministic_relative_date_resolver"


def _normalize_text(text: str | None) -> str:
    return (text or "").strip().lower()


def _resolve_weekday_reference(base_date: date, target_weekday: int) -> date:
    days_ahead = (target_weekday - base_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7

    return base_date + timedelta(days=days_ahead)


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

    if "pasado mañana" in normalized_message or "pasado manana" in normalized_message:
        requested_date = fecha_actual_colombia + timedelta(days=2)
    elif "mañana" in normalized_message or "manana" in normalized_message:
        requested_date = fecha_actual_colombia + timedelta(days=1)
    elif "hoy" in normalized_message:
        requested_date = fecha_actual_colombia
    else:
        for weekday_word, weekday_index in WEEKDAY_WORDS_ES.items():
            if weekday_word in normalized_message:
                requested_date = _resolve_weekday_reference(
                    fecha_actual_colombia,
                    weekday_index,
                )
                break

    if requested_date is None:
        return RelativeDateResolution(
            fecha_actual_colombia=fecha_actual_colombia,
            fecha_solicitada=None,
            dia_semana_solicitado=None,
            es_dia_disponible=False,
            slots_candidatos=[],
        )

    service = calendar_service or CalendarService()
    slots = service.build_default_slots(requested_date)
    slot_labels = [slot.label for slot in slots]

    return RelativeDateResolution(
        fecha_actual_colombia=fecha_actual_colombia,
        fecha_solicitada=requested_date,
        dia_semana_solicitado=WEEKDAY_NAMES_ES[requested_date.weekday()],
        es_dia_disponible=bool(slot_labels),
        slots_candidatos=slot_labels,
    )
