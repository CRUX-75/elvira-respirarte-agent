from __future__ import annotations

import re
import unicodedata
from typing import Any


DYNAMIC_OXIMETRY_VALIDATION_STATE = (
    "ST_OXIMETRIA_DINAMICA_VALIDACION"
)

_WORD_NUMBERS = {
    "cero": 0,
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiun": 21,
    "veintiuno": 21,
    "veintidos": 22,
    "veintitres": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
    "treinta": 30,
}


def _normalize(value: str | None) -> str:
    text = unicodedata.normalize(
        "NFKD",
        (value or "").strip().lower(),
    )
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", text)


def _is_dynamic_oximetry_request(
    message: str,
) -> bool:
    patterns = (
        r"\bquiero (?:agendar|programar|solicitar)\b",
        r"\bnecesito (?:agendar|programar|solicitar)\b",
        r"\bquiero una cita\b",
        r"\bnecesito una cita\b",
        r"\bquiero hacerme\b",
        r"\bnecesito hacerme\b",
        r"\bme quiero hacer\b",
        r"\bpuedo agendar\b",
        r"\bcomo agendo\b",
        r"\bcomo solicito\b",
    )
    return any(
        re.search(pattern, message)
        for pattern in patterns
    )


def _order_status(message: str) -> bool | None:
    negative_patterns = (
        r"\bno tengo (?:la )?orden\b",
        r"\bno cuento con (?:la )?orden\b",
        r"\bsin (?:una )?orden(?: medica)?\b",
        r"\btodavia no tengo (?:la )?orden\b",
        r"\baun no tengo (?:la )?orden\b",
        r"\bno me han dado (?:la )?orden\b",
    )

    if any(
        re.search(pattern, message)
        for pattern in negative_patterns
    ):
        return False

    positive_patterns = (
        r"\bsi tengo (?:la )?orden\b",
        r"\btengo (?:la )?orden(?: medica)?\b",
        r"\bcuento con (?:la )?orden\b",
        r"\bya tengo (?:la )?orden\b",
        r"\bme dieron (?:la )?orden\b",
        r"\btengo formula medica\b",
    )

    if any(
        re.search(pattern, message)
        for pattern in positive_patterns
    ):
        return True

    return None


def _duration_days(message: str) -> int | None:
    numeric_days = re.search(
        r"\b(\d{1,3})\s+dias?\b",
        message,
    )
    if numeric_days:
        return int(numeric_days.group(1))

    word_days = re.search(
        r"\b("
        + "|".join(
            sorted(
                _WORD_NUMBERS,
                key=len,
                reverse=True,
            )
        )
        + r")\s+dias?\b",
        message,
    )
    if word_days:
        return _WORD_NUMBERS[word_days.group(1)]

    numeric_weeks = re.search(
        r"\b(\d{1,2})\s+semanas?\b",
        message,
    )
    if numeric_weeks:
        weeks = int(numeric_weeks.group(1))
        days = weeks * 7

        if "mas de" in message:
            days += 1

        return days

    word_weeks = re.search(
        r"\b("
        + "|".join(
            sorted(
                _WORD_NUMBERS,
                key=len,
                reverse=True,
            )
        )
        + r")\s+semanas?\b",
        message,
    )
    if word_weeks:
        weeks = _WORD_NUMBERS[word_weeks.group(1)]
        days = weeks * 7

        if "mas de" in message:
            days += 1

        return days

    return None


def _set_state_value(
    state: Any,
    field_name: str,
    value: Any,
) -> None:
    setattr(state, field_name, value)


def apply_dynamic_oximetry_policy(
    state: Any,
) -> Any | None:
    current_state = str(
        getattr(state, "estado_actual", "") or ""
    )
    matched_service_id = getattr(
        state,
        "matched_service_id",
        None,
    )

    is_dynamic_context = (
        matched_service_id == "SRV-07"
        or current_state
        == DYNAMIC_OXIMETRY_VALIDATION_STATE
    )

    if not is_dynamic_context:
        return None

    message = _normalize(
        getattr(state, "mensaje_original", "")
    )
    is_followup = (
        current_state
        == DYNAMIC_OXIMETRY_VALIDATION_STATE
    )
    is_request = (
        is_followup
        or _is_dynamic_oximetry_request(message)
    )

    if not is_request:
        _set_state_value(
            state,
            "next_action",
            "answer_dynamic_oximetry_information",
        )
        _set_state_value(
            state,
            "escalation_required",
            False,
        )
        _set_state_value(
            state,
            "state_reason",
            "dynamic_oximetry_information_grounded",
        )
        _set_state_value(
            state,
            "respuesta",
            (
                "La oximetría dinámica permite hacer seguimiento continuo "
                "de la saturación de oxígeno y la frecuencia cardiaca "
                "mientras el paciente realiza diferentes actividades. "
                "Se hace a domicilio y requiere orden médica y "
                "validación previa."
            ),
        )
        return state

    order_status = _order_status(message)
    duration_days = _duration_days(message)

    if order_status is False:
        _set_state_value(
            state,
            "next_action",
            "escalate_dynamic_oximetry_missing_order",
        )
        _set_state_value(
            state,
            "escalation_required",
            True,
        )
        _set_state_value(
            state,
            "nuevo_estado",
            "ST_GENERAL",
        )
        _set_state_value(
            state,
            "state_reason",
            "dynamic_oximetry_missing_medical_order",
        )
        _set_state_value(
            state,
            "respuesta",
            (
                "La oximetría dinámica requiere orden médica. "
                "Como todavía no cuenta con ella, voy a remitir "
                "la solicitud al profesional para que pueda "
                "indicarle cómo continuar."
            ),
        )
        return state

    if (
        duration_days is not None
        and duration_days >= 15
    ):
        _set_state_value(
            state,
            "next_action",
            "escalate_dynamic_oximetry_long_oxygen_support",
        )
        _set_state_value(
            state,
            "escalation_required",
            True,
        )
        _set_state_value(
            state,
            "nuevo_estado",
            "ST_GENERAL",
        )
        _set_state_value(
            state,
            "state_reason",
            "dynamic_oximetry_oxygen_support_15_days_or_more",
        )
        _set_state_value(
            state,
            "respuesta",
            (
                "Como lleva quince días o más con soporte de oxígeno, "
                "la solicitud debe ser revisada por el profesional "
                "antes de continuar. Voy a dejarla remitida para "
                "valoración."
            ),
        )
        return state

    if (
        order_status is True
        and duration_days is not None
        and duration_days < 15
    ):
        _set_state_value(
            state,
            "next_action",
            "ask_preferred_date",
        )
        _set_state_value(
            state,
            "escalation_required",
            False,
        )
        _set_state_value(
            state,
            "nuevo_estado",
            "ST_CITA_FECHA",
        )
        _set_state_value(
            state,
            "state_reason",
            "dynamic_oximetry_requirements_validated",
        )
        _set_state_value(
            state,
            "respuesta",
            (
                "Perfecto. Como cuenta con orden médica y lleva "
                "menos de quince días con soporte de oxígeno, "
                "podemos registrar la solicitud para validación. "
                "¿Para qué día le gustaría solicitarla?"
            ),
        )
        return state

    _set_state_value(
        state,
        "next_action",
        "ask_dynamic_oximetry_requirements",
    )
    _set_state_value(
        state,
        "escalation_required",
        False,
    )
    _set_state_value(
        state,
        "nuevo_estado",
        DYNAMIC_OXIMETRY_VALIDATION_STATE,
    )
    _set_state_value(
        state,
        "state_reason",
        "dynamic_oximetry_requirements_pending",
    )

    if order_status is True and duration_days is None:
        response = (
            "Perfecto, ya sé que cuenta con orden médica. "
            "¿Cuántos días lleva utilizando soporte de oxígeno?"
        )
    elif order_status is None and duration_days is not None:
        response = (
            "Gracias. Para continuar necesito confirmar si "
            "cuenta actualmente con una orden médica."
        )
    else:
        response = (
            "Para solicitar la oximetría dinámica necesito "
            "confirmar dos datos: si cuenta con orden médica "
            "y cuántos días lleva utilizando soporte de oxígeno."
        )

    _set_state_value(
        state,
        "respuesta",
        response,
    )
    return state
