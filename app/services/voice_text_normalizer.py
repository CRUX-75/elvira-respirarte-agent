from __future__ import annotations

import re


_SMALL_NUMBERS = {
    0: "cero",
    1: "uno",
    2: "dos",
    3: "tres",
    4: "cuatro",
    5: "cinco",
    6: "seis",
    7: "siete",
    8: "ocho",
    9: "nueve",
    10: "diez",
    11: "once",
    12: "doce",
    13: "trece",
    14: "catorce",
    15: "quince",
    16: "dieciséis",
    17: "diecisiete",
    18: "dieciocho",
    19: "diecinueve",
    20: "veinte",
    21: "veintiuno",
    22: "veintidós",
    23: "veintitrés",
    24: "veinticuatro",
    25: "veinticinco",
    26: "veintiséis",
    27: "veintisiete",
    28: "veintiocho",
    29: "veintinueve",
}

_TENS = {
    30: "treinta",
    40: "cuarenta",
    50: "cincuenta",
    60: "sesenta",
    70: "setenta",
    80: "ochenta",
    90: "noventa",
}

_BETWEEN_RANGE_WITH_UNIT_PATTERN = re.compile(
    r"\bentre\s+(\d{1,3})\s+y\s+(\d{1,3})\s+"
    r"(horas?|minutos?|días?|dias?|pacientes?|mensajes?)\b",
    flags=re.IGNORECASE,
)

_RANGE_WITH_UNIT_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(?:a|–|—|-)\s*(\d{1,3})\s+"
    r"(horas?|minutos?|días?|dias?|pacientes?|mensajes?)\b",
    flags=re.IGNORECASE,
)

_UNIT_PATTERN = re.compile(
    r"\b(\d{1,3})\s+"
    r"(horas?|minutos?|días?|dias?|pacientes?|mensajes?)\b",
    flags=re.IGNORECASE,
)

_COLON_TIME_PATTERN = re.compile(
    r"\b(?P<hour>\d{1,2}):(?P<minute>\d{2})"
    r"\s*(?P<period>a\.?\s*m\.?|p\.?\s*m\.?)?",
    flags=re.IGNORECASE,
)

_PERIOD_TIME_PATTERN = re.compile(
    r"\b(?P<hour>\d{1,2})\s*"
    r"(?P<period>a\.?\s*m\.?|p\.?\s*m\.?)\b",
    flags=re.IGNORECASE,
)

_ABBREVIATIONS = (
    (re.compile(r"\bDra\.", flags=re.IGNORECASE), "doctora"),
    (re.compile(r"\bDr\.", flags=re.IGNORECASE), "doctor"),
    (re.compile(r"\bSra\.", flags=re.IGNORECASE), "señora"),
    (re.compile(r"\bSr\.", flags=re.IGNORECASE), "señor"),
)


def _number_to_words(value: int) -> str:
    if value in _SMALL_NUMBERS:
        return _SMALL_NUMBERS[value]

    if value in _TENS:
        return _TENS[value]

    if 30 < value < 100:
        tens = value // 10 * 10
        units = value % 10
        return f"{_TENS[tens]} y {_SMALL_NUMBERS[units]}"

    if value == 100:
        return "cien"

    return str(value)


def _normalize_period(period: str | None) -> str | None:
    if not period:
        return None

    compact = re.sub(r"[\s.]", "", period.lower())

    if compact == "am":
        return "am"

    if compact == "pm":
        return "pm"

    return None


def _spoken_time(
    hour: int,
    minute: int,
    period: str | None,
) -> str:
    normalized_period = _normalize_period(period)
    hour_24 = hour

    if normalized_period == "am":
        hour_24 = 0 if hour == 12 else hour
    elif normalized_period == "pm":
        hour_24 = hour if hour == 12 else hour + 12

    if hour_24 > 23 or minute > 59:
        raw = f"{hour:02d}:{minute:02d}"
        return raw

    if hour_24 == 0:
        hour_words = "doce"
        daypart = "de la noche"
    elif hour_24 == 12:
        hour_words = "doce"
        daypart = "del mediodía"
    elif hour_24 > 12:
        hour_12 = hour_24 - 12
        hour_words = _number_to_words(hour_12)
        daypart = (
            "de la tarde"
            if hour_24 < 19
            else "de la noche"
        )
    else:
        hour_words = _number_to_words(hour_24)
        daypart = (
            "de la mañana"
            if normalized_period == "am"
            else ""
        )

    if minute == 0:
        minute_words = ""
    elif minute == 15:
        minute_words = " y cuarto"
    elif minute == 30:
        minute_words = " y media"
    else:
        minute_words = f" y {_number_to_words(minute)}"

    return " ".join(
        part
        for part in (
            f"{hour_words}{minute_words}",
            daypart,
        )
        if part
    )


def _sentence_stop_after_time(
    match: re.Match[str],
) -> str:
    matched_text = match.group(0).rstrip()

    if not matched_text.endswith("."):
        return ""

    remaining = match.string[match.end():]

    if not remaining:
        return "."

    if re.match(
        r"\s+[A-ZÁÉÍÓÚÑ¿¡]",
        remaining,
    ):
        return "."

    return ""


def _replace_colon_time(match: re.Match[str]) -> str:
    spoken = _spoken_time(
        int(match.group("hour")),
        int(match.group("minute")),
        match.group("period"),
    )
    return spoken + _sentence_stop_after_time(match)


def _replace_period_time(match: re.Match[str]) -> str:
    spoken = _spoken_time(
        int(match.group("hour")),
        0,
        match.group("period"),
    )
    return spoken + _sentence_stop_after_time(match)


def _replace_between_number_range_with_unit(
    match: re.Match[str],
) -> str:
    start_value = int(match.group(1))
    end_value = int(match.group(2))
    unit = match.group(3)

    return (
        f"entre {_number_to_words(start_value)} y "
        f"{_number_to_words(end_value)} {unit}"
    )


def _replace_number_range_with_unit(
    match: re.Match[str],
) -> str:
    start_value = int(match.group(1))
    end_value = int(match.group(2))
    unit = match.group(3)

    return (
        f"{_number_to_words(start_value)} a "
        f"{_number_to_words(end_value)} {unit}"
    )


def _replace_number_with_unit(
    match: re.Match[str],
) -> str:
    value = int(match.group(1))
    unit = match.group(2)

    return f"{_number_to_words(value)} {unit}"


def normalize_text_for_speech(text: str) -> str:
    """
    Prepare deterministic response text for spoken delivery.

    This function may alter pronunciation-oriented formatting, but it
    must not remove facts, add clinical claims, change state or change
    the original written response.
    """
    spoken = text.strip()

    if not spoken:
        return ""

    spoken = _COLON_TIME_PATTERN.sub(
        _replace_colon_time,
        spoken,
    )
    spoken = _PERIOD_TIME_PATTERN.sub(
        _replace_period_time,
        spoken,
    )

    for pattern, replacement in _ABBREVIATIONS:
        spoken = pattern.sub(replacement, spoken)

    spoken = _BETWEEN_RANGE_WITH_UNIT_PATTERN.sub(
        _replace_between_number_range_with_unit,
        spoken,
    )
    spoken = _RANGE_WITH_UNIT_PATTERN.sub(
        _replace_number_range_with_unit,
        spoken,
    )
    spoken = _UNIT_PATTERN.sub(
        _replace_number_with_unit,
        spoken,
    )

    spoken = re.sub(
        r"(?m)^\s*[-•]\s*",
        "",
        spoken,
    )
    spoken = re.sub(
        r"\s*[–—]\s*",
        " a ",
        spoken,
    )
    spoken = re.sub(
        r";\s*",
        ". ",
        spoken,
    )
    spoken = re.sub(
        r":\s*\n+",
        ". ",
        spoken,
    )
    spoken = re.sub(
        r"\s*\n+\s*",
        ". ",
        spoken,
    )
    spoken = re.sub(
        r"\.{2,}",
        ".",
        spoken,
    )
    spoken = re.sub(
        r"\s+([,.;:!?])",
        r"\1",
        spoken,
    )
    spoken = re.sub(
        r"([.!?])(?=[^\s])",
        r"\1 ",
        spoken,
    )
    spoken = re.sub(
        r"\s+",
        " ",
        spoken,
    )

    return spoken.strip()
