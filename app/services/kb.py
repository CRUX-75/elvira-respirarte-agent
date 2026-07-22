from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy.engine import Engine

from app.repositories.kb_rules import get_active_rules, get_rules_by_type, search_rules
from app.repositories.kb_schedules import get_all_schedules, search_schedules
from app.repositories.kb_services import get_active_services, search_services
from app.services.approved_service_catalog import (
    get_active_approved_services,
    get_approved_service_by_id,
)


SERVICE_KEYWORDS = {
    "servicio",
    "servicios",
    "terapia",
    "terapias",
    "respiratoria",
    "respiratorio",
    "rehabilitación",
    "rehabilitacion",
    "pulmonar",
    "espirometría",
    "espirometria",
    "prueba",
    "pruebas",
    "traqueostomía",
    "traqueostomia",
    "traqueotomía",
    "traqueotomia",
    "curso",
    "materno",
    "gestante",
    "embarazo",
    "empresa",
    "empresarial",
    "sst",
}

SCHEDULE_KEYWORDS = {
    "horario",
    "horarios",
    "atienden",
    "atiende",
    "atención",
    "atencion",
    "sábado",
    "sabado",
    "domingo",
    "lunes",
    "martes",
    "miércoles",
    "miercoles",
    "jueves",
    "viernes",
    "mañana",
    "tarde",
    "noche",
    "disponible",
    "disponibilidad",
    "agenda",
    "cita",
}

RULE_KEYWORDS = {
    "precio",
    "precios",
    "costo",
    "costos",
    "valor",
    "urgencia",
    "urgente",
    "emergencia",
    "cancelar",
    "cancelación",
    "cancelacion",
    "reagendar",
    "fuera de horario",
}

APPOINTMENT_RULE_STATES = {
    "st_cita_confirmada",
    "st_cita_pendiente",
    "st_cita_franja",
}


SIMPLE_GREETING_MESSAGES = {
    "hola",
    "buen dia",
    "buen día",
    "buenos dias",
    "buenos días",
    "buenas",
    "buenas tardes",
    "buenas noches",
    "hola buen dia",
    "hola buen día",
    "hola buenos dias",
    "hola buenos días",
    "hola buenas",
    "hola buenas tardes",
    "hola buenas noches",
}


def _normalize(text: str | None) -> str:
    """
    Normalize patient-facing WhatsApp text for deterministic KB matching.

    This intentionally removes accents so common Colombian/WhatsApp variants like
    "oxígeno/oxigeno", "cánula/canula" and "respiración/respiracion" match the
    same service search terms.
    """
    cleaned = (text or "").strip().lower()
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(char for char in cleaned if not unicodedata.combining(char))
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _split_search_terms(search_terms: str | None) -> list[str]:
    if not search_terms:
        return []

    normalized_terms = _normalize(search_terms)
    return [
        term.strip()
        for term in re.split(r"[,;|\n]+", normalized_terms)
        if len(term.strip()) >= 3
    ]


_SERVICE_MATCH_FIELDS = (
    "service_name",
    "category",
    "objective",
    "techniques",
    "patient_scope",
    "modality",
    "public_answer_short",
    "public_answer_long",
    "search_terms",
)


_GENERIC_PROCEDURE_TOKENS = {
    "acerca",
    "algun",
    "alguna",
    "algunos",
    "algunas",
    "como",
    "con",
    "cual",
    "cuales",
    "de",
    "del",
    "doctora",
    "doctor",
    "el",
    "en",
    "este",
    "esta",
    "esto",
    "favor",
    "hacen",
    "hacer",
    "informacion",
    "info",
    "la",
    "las",
    "le",
    "los",
    "mas",
    "me",
    "necesito",
    "ofrece",
    "ofrecen",
    "para",
    "podria",
    "podrian",
    "por",
    "procedimiento",
    "procedimientos",
    "que",
    "quiero",
    "quisiera",
    "realiza",
    "realizan",
    "respirarte",
    "saber",
    "se",
    "servicio",
    "servicios",
    "sobre",
    "tienen",
    "tiene",
    "toma",
    "una",
    "uno",
    "ustedes",
    "y",
}


_GENERIC_SERVICE_PORTFOLIO_MARKERS = {
    "que servicios",
    "cuales servicios",
    "servicios ofrecen",
    "servicios ofrece",
    "servicios tienen",
    "servicios tiene",
    "portafolio",
}


def _split_match_fragments(value: str) -> list[str]:
    fragments: list[str] = []

    for line in value.splitlines():
        fragments.extend(re.split(r"[,;|]+", line))

    return [
        fragment.strip()
        for fragment in fragments
        if len(fragment.strip()) >= 3
    ]


def _iter_service_match_terms(
    row: dict[str, Any],
) -> list[tuple[str, str]]:
    terms: list[tuple[str, str]] = []

    for field_name in _SERVICE_MATCH_FIELDS:
        raw_value = row.get(field_name)

        if raw_value is None:
            continue

        normalized_value = _normalize(str(raw_value))

        if not normalized_value:
            continue

        if field_name in {"techniques", "search_terms"}:
            fragments = _split_match_fragments(normalized_value)
        else:
            fragments = [normalized_value]

        for fragment in fragments:
            terms.append((field_name, fragment))

    return sorted(
        terms,
        key=lambda item: len(item[1]),
        reverse=True,
    )


def _significant_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", _normalize(text))
        if len(token) >= 3
    }


def _technique_match_status(
    row: dict[str, Any],
    term: str,
    normalized_message: str,
) -> str:
    """
    Distinguish a confirmed KB procedure from an unvalidated variant.

    Examples:
    - "información sobre oximetría" -> exact
    - "oximetría domiciliaria" -> exact when modality is Domiciliaria
    - "oximetría dinámica" -> partial when "dinámica" is absent from the KB row
    """
    known_tokens = _significant_tokens(term)

    for field_name in (
        "service_name",
        "category",
        "modality",
    ):
        known_tokens.update(
            _significant_tokens(str(row.get(field_name) or ""))
        )

    message_tokens = _significant_tokens(normalized_message)

    unknown_tokens = (
        message_tokens
        - known_tokens
        - _GENERIC_PROCEDURE_TOKENS
    )

    return "partial" if unknown_tokens else "exact"


def _build_service_match(
    row: dict[str, Any],
    *,
    field_name: str,
    term: str,
    normalized_message: str,
) -> dict[str, Any]:
    if field_name == "techniques":
        status = _technique_match_status(
            row,
            term,
            normalized_message,
        )
    else:
        status = "exact"

    return {
        "matched_service_id": row.get("service_id"),
        "matched_service_term": term,
        "matched_service_field": field_name,
        "service_grounding_status": status,
    }


def _match_service_row(
    row: dict[str, Any],
    normalized_message: str,
) -> dict[str, Any] | None:
    for field_name, term in _iter_service_match_terms(row):
        if term in normalized_message:
            return _build_service_match(
                row,
                field_name=field_name,
                term=term,
                normalized_message=normalized_message,
            )

        if field_name not in {
            "service_name",
            "category",
            "techniques",
            "search_terms",
        }:
            continue

        term_tokens = _significant_tokens(term)

        if not term_tokens:
            continue

        message_tokens = _significant_tokens(normalized_message)

        if term_tokens.issubset(message_tokens):
            return _build_service_match(
                row,
                field_name=field_name,
                term=term,
                normalized_message=normalized_message,
            )

    return None


def _find_service_matches(
    rows: list[dict[str, Any]],
    normalized_message: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    exact_rows: list[dict[str, Any]] = []
    partial_rows: list[dict[str, Any]] = []
    exact_metadata: dict[str, Any] | None = None
    partial_metadata: dict[str, Any] | None = None

    for row in rows:
        match = _match_service_row(
            row,
            normalized_message,
        )

        if not match:
            continue

        if match["service_grounding_status"] == "exact":
            exact_rows.append(row)

            if exact_metadata is None:
                exact_metadata = match
        else:
            partial_rows.append(row)

            if partial_metadata is None:
                partial_metadata = match

    if exact_rows:
        return exact_rows, exact_metadata

    if partial_rows:
        return partial_rows, partial_metadata

    return [], None


def _filter_services_by_search_terms(
    rows: list[dict[str, Any]],
    normalized_message: str,
) -> list[dict[str, Any]]:
    matched_rows, _ = _find_service_matches(
        rows,
        normalized_message,
    )
    return matched_rows


def _is_generic_service_portfolio_question(
    normalized_message: str,
) -> bool:
    return any(
        marker in normalized_message
        for marker in _GENERIC_SERVICE_PORTFOLIO_MARKERS
    )


def _is_simple_greeting(text: str) -> bool:
    cleaned = text.strip().lower()
    cleaned = cleaned.strip(" .,;:!¡¿?")
    return cleaned in SIMPLE_GREETING_MESSAGES


def _compact_rows(rows: list[dict[str, Any]], max_rows: int = 5) -> list[dict[str, Any]]:
    """
    Keep KB context small and predictable before sending it to the LLM.
    """
    return rows[:max_rows]


def _build_services_context(
    rows: list[dict[str, Any]],
) -> str:
    if not rows:
        return ""

    lines = ["Servicios activos de Respirarte:"]
    seen_service_ids: set[str] = set()

    for source_row in rows:
        row = dict(source_row)
        service_id = str(row.get("service_id") or "")

        approved_row = (
            get_approved_service_by_id(service_id)
            if service_id
            else None
        )

        if approved_row is not None:
            if approved_row.get("is_active") is not True:
                continue

            row = approved_row

        if service_id and service_id in seen_service_ids:
            continue

        if service_id:
            seen_service_ids.add(service_id)

        service_name = row.get("service_name") or "Servicio"
        short_answer = (
            row.get("public_answer_short")
            or row.get("objective")
            or ""
        )
        modality = row.get("modality") or ""
        procedures = row.get("techniques") or ""
        escalation_required = row.get("escalation_required")

        line = f"- {service_name}"

        if modality:
            line += f" ({modality})"

        if short_answer:
            line += f": {short_answer}"

        if procedures:
            line += f" | procedimientos: {procedures}"

        if escalation_required:
            line += " Requiere revisión o escalamiento."

        lines.append(line)

    return "\n".join(lines)


def _build_schedules_context(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    lines = ["Horarios y disponibilidad de Respirarte:"]

    for row in rows:
        day_name = row.get("day_name") or row.get("day_type") or "Día"
        modality = row.get("modality") or "Modalidad no especificada"
        start_time = row.get("start_time")
        end_time = row.get("end_time")
        is_available = row.get("is_available")
        notes = row.get("notes")

        line = f"- {day_name}: {modality}"

        if start_time and end_time:
            line += f", {start_time}–{end_time}"

        if is_available:
            line += f" | disponibilidad: {is_available}"

        if notes:
            line += f" | nota: {notes}"

        lines.append(line)

    return "\n".join(lines)


def _build_rules_context(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    lines = ["Reglas operativas relevantes:"]

    for row in rows:
        rule_type = row.get("rule_type") or "regla"
        condition = row.get("condition") or ""
        response_rule = row.get("response_rule") or ""
        allowed_action = row.get("allowed_action") or ""
        escalation = row.get("escalation")

        line = f"- Tipo: {rule_type}"
        if condition:
            line += f" | condición: {condition}"
        if response_rule:
            line += f" | regla: {response_rule}"
        if allowed_action:
            line += f" | acción permitida: {allowed_action}"
        if escalation:
            line += " | requiere escalamiento"

        lines.append(line)

    return "\n".join(lines)


def get_kb_context(
    engine: Engine,
    *,
    intent: str,
    message: str,
    estado_actual: str | None = None,
) -> dict[str, Any]:
    """
    Build deterministic and traceable KB context.

    This layer may identify service grounding, but it does not independently
    decide conversational state transitions.
    """
    normalized_message = _normalize(message)
    normalized_intent = _normalize(intent)
    normalized_state = _normalize(estado_actual)

    contexts: list[str] = []
    sources: list[str] = []

    matched_service_id: str | None = None
    matched_service_term: str | None = None
    matched_service_field: str | None = None
    service_grounding_status: str | None = None

    explicit_service_intent = normalized_intent in {
        "servicio",
        "servicios",
        "service",
        "services",
    }

    generic_service_question = (
        explicit_service_intent
        and _is_generic_service_portfolio_question(
            normalized_message
        )
    )

    if (
        explicit_service_intent
        and (
            "oximetria dinamica" in normalized_message
            or normalized_state
            == "st_oximetria_dinamica_validacion"
        )
    ):
        dynamic_service = get_approved_service_by_id("SRV-07")

        if dynamic_service and dynamic_service.get("is_active") is True:
            service_context = _build_services_context(
                [dynamic_service]
            )

            return {
                "kb_used": True,
                "kb_sources": ["kb_services"],
                "kb_context": service_context,
                "matched_service_id": "SRV-07",
                "matched_service_term": "oximetria dinamica",
                "matched_service_field": "service_name",
                "service_grounding_status": "exact",
            }

    simple_general_greeting = (
        normalized_intent == "general"
        and _is_simple_greeting(normalized_message)
    )

    if simple_general_greeting:
        return {
            "kb_used": False,
            "kb_sources": [],
            "kb_context": "",
        }

    appointment_state_requires_rules = (
        not explicit_service_intent
        and normalized_state in APPOINTMENT_RULE_STATES
    )

    should_use_rules = (
        normalized_intent
        in {
            "precio",
            "price",
            "pago",
            "urgencia",
            "cancelacion",
        }
        or appointment_state_requires_rules
        or _contains_any(
            normalized_message,
            RULE_KEYWORDS,
        )
    )

    should_use_services = (
        explicit_service_intent
        or normalized_intent == "general"
        or _contains_any(
            normalized_message,
            SERVICE_KEYWORDS,
        )
    )

    should_use_schedules = (
        not explicit_service_intent
        and (
            normalized_intent
            in {
                "cita",
                "schedule",
                "horario",
            }
            or normalized_state.startswith("st_cita")
            or _contains_any(
                normalized_message,
                SCHEDULE_KEYWORDS,
            )
        )
    )

    if should_use_services:
        service_rows = search_services(
            engine,
            normalized_message,
        )

        if generic_service_question:
            # A portfolio question does not name one individual service.
            # Preserve rows already returned by the repository. If the search
            # returned none, load the complete active portfolio.
            if not service_rows:
                service_rows = get_active_approved_services()

            match_metadata = {
                "matched_service_id": None,
                "matched_service_term": "servicios",
                "matched_service_field": "portfolio",
                "service_grounding_status": "exact",
            }
        else:
            matched_rows, match_metadata = _find_service_matches(
                service_rows,
                normalized_message,
            )

            if matched_rows:
                service_rows = matched_rows
            else:
                active_service_rows = get_active_services(engine)

                matched_rows, match_metadata = _find_service_matches(
                    active_service_rows,
                    normalized_message,
                )

                has_search_terms = any(
                    bool((row.get("search_terms") or "").strip())
                    for row in active_service_rows
                )

                if matched_rows:
                    service_rows = matched_rows
                elif explicit_service_intent:
                    service_rows = []
                elif has_search_terms:
                    service_rows = []
                else:
                    service_rows = active_service_rows

        if match_metadata:
            matched_service_id = match_metadata.get(
                "matched_service_id"
            )
            matched_service_term = match_metadata.get(
                "matched_service_term"
            )
            matched_service_field = match_metadata.get(
                "matched_service_field"
            )
            service_grounding_status = match_metadata.get(
                "service_grounding_status"
            )

        service_rows = _compact_rows(service_rows)
        service_context = _build_services_context(
            service_rows
        )

        if service_context:
            contexts.append(service_context)
            sources.append("kb_services")
        elif explicit_service_intent:
            service_grounding_status = "not_found"

    if should_use_schedules:
        schedule_rows = search_schedules(
            engine,
            normalized_message,
        )

        if not schedule_rows:
            schedule_rows = get_all_schedules(engine)

        schedule_rows = _compact_rows(schedule_rows)
        schedule_context = _build_schedules_context(
            schedule_rows
        )

        if schedule_context:
            contexts.append(schedule_context)
            sources.append("kb_schedules")

    if should_use_rules:
        if appointment_state_requires_rules:
            rule_rows = get_rules_by_type(
                engine,
                "agendamiento",
            )
        else:
            rule_rows = search_rules(
                engine,
                normalized_message,
            )

        if not rule_rows:
            rule_rows = get_active_rules(engine)

        rule_rows = _compact_rows(rule_rows)
        rule_context = _build_rules_context(rule_rows)

        if rule_context:
            contexts.append(rule_context)
            sources.append("kb_rules")

    kb_context = "\n\n".join(contexts).strip()

    result = {
        "kb_used": bool(kb_context),
        "kb_sources": sources,
        "kb_context": kb_context,
    }

    if explicit_service_intent or matched_service_id:
        result.update(
            {
                "matched_service_id": matched_service_id,
                "matched_service_term": matched_service_term,
                "matched_service_field": matched_service_field,
                "service_grounding_status": (
                    service_grounding_status
                    or "not_found"
                ),
            }
        )

    return result
