from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Protocol


class CalendarServiceNotConfigured(RuntimeError):
    """Raised when CalendarService is used before external calendar config exists."""


@dataclass(frozen=True)
class CalendarSlot:
    """
    Represents one appointment slot candidate.

    This is an internal deterministic structure.
    It does not confirm availability by itself.
    """

    start_at: datetime
    end_at: datetime
    label: str
    available: bool = False


@dataclass(frozen=True)
class CalendarAvailabilityResult:
    """
    Result returned by CalendarService when checking appointment availability.

    For now this remains a scaffold. Real Google Calendar availability checks
    will be implemented in a later phase.
    """

    requested_date: date
    slots: list[CalendarSlot]
    source: str = "internal_scaffold"


class CalendarProvider(Protocol):
    """
    Provider interface for future calendar integrations.

    Google Calendar OAuth2 will later implement this protocol.
    """

    def get_busy_ranges(self, day: date) -> list[tuple[datetime, datetime]]:
        ...


def _format_patient_time(value: time) -> str:
    """
    Format slot times in natural Colombian patient-facing style.

    Examples:
    - 15:00 -> 3:00 p. m.
    - 17:00 -> 5:00 p. m.
    """
    hour_12 = value.hour % 12 or 12
    period = "a. m." if value.hour < 12 else "p. m."
    return f"{hour_12}:{value.minute:02d} {period}"


class CalendarService:
    """
    Internal deterministic calendar service.

    Responsibilities:
    - Keep appointment availability logic outside the LLM.
    - Prepare a clean boundary for future Google Calendar OAuth2 integration.
    - Never confirm appointments directly.
    """

    def __init__(self, provider: CalendarProvider | None = None) -> None:
        self.provider = provider

    def is_configured(self) -> bool:
        return self.provider is not None

    def build_default_slots(self, requested_date: date) -> list[CalendarSlot]:
        """
        Build default Respirarte appointment slots.

        Current policy:
        - Two-hour visible patient slots.
        - L/M/J/V: 3:00 p. m.–5:00 p. m. and 5:00 p. m.–7:00 p. m.
        - Wednesday: 3:00 p. m.–5:00 p. m. only.
        - Weekends are not handled here yet.

        This method only builds candidates. It does not confirm availability.
        """

        weekday = requested_date.weekday()

        # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
        if weekday == 2:
            ranges = [(time(15, 0), time(17, 0))]
        elif weekday in {0, 1, 3, 4}:
            ranges = [(time(15, 0), time(17, 0)), (time(17, 0), time(19, 0))]
        else:
            ranges = []

        return [
            CalendarSlot(
                start_at=datetime.combine(requested_date, start),
                end_at=datetime.combine(requested_date, end),
                label=f"{_format_patient_time(start)}–{_format_patient_time(end)}",
                available=False,
            )
            for start, end in ranges
        ]

    def check_availability(self, requested_date: date) -> CalendarAvailabilityResult:
        """
        Future availability entrypoint.

        For now, this returns deterministic candidate slots only.
        Real busy/free checks must be added later through CalendarProvider.
        """

        slots = self.build_default_slots(requested_date)

        return CalendarAvailabilityResult(
            requested_date=requested_date,
            slots=slots,
        )
