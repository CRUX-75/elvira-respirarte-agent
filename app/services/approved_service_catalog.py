from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any


SERVICES_CSV = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "kb"
    / "datakbKB_Servicios.csv"
)


def _normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", text)


def _to_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value

    return _normalize(str(value or "")) in {
        "1",
        "true",
        "yes",
        "si",
    }


@lru_cache(maxsize=1)
def _load_catalog() -> tuple[dict[str, Any], ...]:
    with SERVICES_CSV.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    catalog: list[dict[str, Any]] = []

    for source_row in rows:
        row: dict[str, Any] = dict(source_row)
        row["is_active"] = _to_bool(row.get("is_active"))
        row["escalation_required"] = _to_bool(
            row.get("escalation_required")
        )
        catalog.append(row)

    return tuple(catalog)


def get_approved_service_by_id(
    service_id: str,
) -> dict[str, Any] | None:
    for row in _load_catalog():
        if row.get("service_id") == service_id:
            return dict(row)

    return None


def get_active_approved_services() -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in _load_catalog()
        if row.get("is_active") is True
    ]


def unavailable_service_requires_escalation(
    message: str | None,
) -> bool:
    normalized = _normalize(message)

    return bool(
        re.search(
            r"\btraqueotom(?:ia|izad[oa]s?)\b"
            r"|\btraqueostom(?:ia|izad[oa]s?)\b",
            normalized,
        )
    )


def get_unavailable_service_response(message: str | None) -> str:
    normalized = _normalize(message)

    if re.search(
        r"\btraqueotom(?:ia|izad[oa]s?)\b"
        r"|\btraqueostom(?:ia|izad[oa]s?)\b",
        normalized,
    ):
        return (
            "Actualmente Respirarte no ofrece este servicio porque se "
            "encuentra temporalmente inactivo. Voy a remitir su solicitud "
            "al especialista para que pueda valorarla y confirmar si es "
            "posible prestar el servicio."
        )

    if (
        "oxigenoterapia" in normalized
        or "oxigeno domiciliario" in normalized
        or "terapia de oxigeno" in normalized
    ):
        return (
            "Actualmente Respirarte no ofrece oxigenoterapia domiciliaria. "
            "Este procedimiento solo se realiza en una institución que "
            "cuente con un punto de oxígeno adecuado."
        )

    if (
        "curso psicoprofilactico" in normalized
        or "curso profilactico materno" in normalized
        or "curso para gestantes" in normalized
    ):
        return (
            "Actualmente Respirarte no ofrece el curso psicoprofiláctico "
            "materno, porque requiere un equipo multidisciplinario que no "
            "se presta de forma integral."
        )

    return (
        "Actualmente ese servicio no está disponible. "
        "Puedo ayudarle con información sobre los servicios activos "
        "de Respirarte."
    )


def get_active_portfolio_response() -> str:
    return (
        "En Respirarte ofrecemos terapia respiratoria domiciliaria, "
        "oximetría dinámica, pruebas de función pulmonar, "
        "rehabilitación pulmonar y servicios de salud respiratoria "
        "para empresas. ¿Sobre cuál desea recibir más información?"
    )
