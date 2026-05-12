from datetime import date

from app.services.calendar_service import CalendarService


def test_calendar_service_is_not_configured_without_provider():
    service = CalendarService()

    assert service.is_configured() is False


def test_calendar_service_builds_two_slots_for_monday():
    service = CalendarService()

    slots = service.build_default_slots(date(2026, 5, 11))  # Monday

    assert len(slots) == 2
    assert slots[0].label == "3:00 p. m.–5:00 p. m."
    assert slots[1].label == "5:00 p. m.–7:00 p. m."
    assert all(slot.available is False for slot in slots)


def test_calendar_service_builds_one_slot_for_wednesday():
    service = CalendarService()

    slots = service.build_default_slots(date(2026, 5, 13))  # Wednesday

    assert len(slots) == 1
    assert slots[0].label == "3:00 p. m.–5:00 p. m."
    assert slots[0].available is False


def test_calendar_service_builds_no_slots_for_sunday():
    service = CalendarService()

    slots = service.build_default_slots(date(2026, 5, 10))  # Sunday

    assert slots == []


def test_calendar_service_check_availability_returns_scaffold_result():
    service = CalendarService()

    result = service.check_availability(date(2026, 5, 11))

    assert result.requested_date == date(2026, 5, 11)
    assert result.source == "internal_scaffold"
    assert len(result.slots) == 2
