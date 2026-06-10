from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy.engine import Engine

from app.repositories.kb_rules import get_active_rules, get_rules_by_type, search_rules
from app.repositories.kb_schedules import get_all_schedules, search_schedules
from app.repositories.kb_services import get_active_services, search_services


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


def _service_matches_search_terms(
    row: dict[str, Any],
    normalized_message: str,
) -> bool:
    """
    Match colloquial patient language against service-owned search terms.

    This is not clinical reasoning. It only maps patient language to the most
    likely Respirarte service category so the response can stay safe and the
    doctor can review the case.
    """
    for term in _split_search_terms(row.get("search_terms")):
        if term in normalized_message:
            return True

        # Support natural WhatsApp variants like:
        # "el niño está muy mocoso" vs search term "niño mocoso"
        # "le saquen los mocos" vs search terms containing "mocos"
        tokens = re.findall(r"[a-z0-9]+", term)
        relevant_tokens = [token for token in tokens if len(token) >= 4]

        if len(relevant_tokens) == 1 and relevant_tokens[0] in normalized_message:
            return True

        if len(relevant_tokens) >= 2 and all(
            token in normalized_message for token in relevant_tokens
        ):
            return True

    return False


def _filter_services_by_search_terms(
    rows: list[dict[str, Any]],
    normalized_message: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if _service_matches_search_terms(row, normalized_message)
    ]


def _is_simple_greeting(text: str) -> bool:
    cleaned = text.strip().lower()
    cleaned = cleaned.strip(" .,;:!¡¿?")
    return cleaned in SIMPLE_GREETING_MESSAGES


def _compact_rows(rows: list[dict[str, Any]], max_rows: int = 5) -> list[dict[str, Any]]:
    """
    Keep KB context small and predictable before sending it to the LLM.
    """
    return rows[:max_rows]


def _build_services_context(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    lines = ["Servicios activos de Respirarte:"]

    for row in rows:
        service_name = row.get("service_name") or "Servicio"
        short_answer = row.get("public_answer_short") or row.get("objective") or ""
        modality = row.get("modality") or ""
        escalation_required = row.get("escalation_required")

        line = f"- {service_name}"
        if modality:
            line += f" ({modality})"
        if short_answer:
            line += f": {short_answer}"
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
    Deterministic KB context builder.

    Responsibilities:
    - Read informational context from PostgreSQL KB tables.
    - Return compact context for response generation.
    - Never decide or modify intent, state, next_action, opt-out, or escalation.

    The state machine remains the source of truth for control decisions.
    """
    normalized_message = _normalize(message)
    normalized_intent = _normalize(intent)
    normalized_state = _normalize(estado_actual)

    contexts: list[str] = []
    sources: list[str] = []

    explicit_service_intent = normalized_intent in {
        "servicio",
        "servicios",
        "service",
        "services",
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
        normalized_intent in {"precio", "price", "pago", "urgencia", "cancelacion"}
        or appointment_state_requires_rules
        or _contains_any(normalized_message, RULE_KEYWORDS)
    )

    should_use_services = (
        explicit_service_intent
        or normalized_intent == "general"
        or _contains_any(normalized_message, SERVICE_KEYWORDS)
    )

    should_use_schedules = (
        not explicit_service_intent
        and (
            normalized_intent in {"cita", "schedule", "horario"}
            or normalized_state.startswith("st_cita")
            or _contains_any(normalized_message, SCHEDULE_KEYWORDS)
        )
    )

    if should_use_services:
        service_rows = search_services(engine, normalized_message)

        if not service_rows:
            active_service_rows = get_active_services(engine)
            matched_service_rows = _filter_services_by_search_terms(
                active_service_rows,
                normalized_message,
            )

            # If the KB has service-owned search terms, prefer them over the
            # old full-portfolio fallback. This prevents colloquial patient
            # messages like "le silva el pecho" or "niño mocoso" from loading
            # unrelated services such as Curso Materno or SST.
            has_search_terms = any(
                bool((row.get("search_terms") or "").strip())
                for row in active_service_rows
            )

            if matched_service_rows:
                service_rows = matched_service_rows
            elif has_search_terms and not _contains_any(
                normalized_message,
                {"servicio", "servicios", "ofrecen", "ofrece", "portafolio"},
            ):
                service_rows = []
            else:
                service_rows = active_service_rows

        service_rows = _compact_rows(service_rows)
        service_context = _build_services_context(service_rows)

        if service_context:
            contexts.append(service_context)
            sources.append("kb_services")

    if should_use_schedules:
        schedule_rows = search_schedules(engine, normalized_message)
        if not schedule_rows:
            schedule_rows = get_all_schedules(engine)

        schedule_rows = _compact_rows(schedule_rows)
        schedule_context = _build_schedules_context(schedule_rows)

        if schedule_context:
            contexts.append(schedule_context)
            sources.append("kb_schedules")

    if should_use_rules:
        if appointment_state_requires_rules:
            rule_rows = get_rules_by_type(engine, "agendamiento")
        else:
            rule_rows = search_rules(engine, normalized_message)

        if not rule_rows:
            rule_rows = get_active_rules(engine)

        rule_rows = _compact_rows(rule_rows)
        rule_context = _build_rules_context(rule_rows)

        if rule_context:
            contexts.append(rule_context)
            sources.append("kb_rules")

    kb_context = "\n\n".join(contexts).strip()

    return {
        "kb_used": bool(kb_context),
        "kb_sources": sources,
        "kb_context": kb_context,
    }
