from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine

from app.repositories.kb_rules import get_active_rules, search_rules
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
    "teleconsulta",
}


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


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

    should_use_services = (
        normalized_intent in {"servicio", "services", "general"}
        or _contains_any(normalized_message, SERVICE_KEYWORDS)
    )

    should_use_schedules = (
        normalized_intent in {"cita", "schedule", "horario"}
        or normalized_state.startswith("st_cita")
        or _contains_any(normalized_message, SCHEDULE_KEYWORDS)
    )

    should_use_rules = (
        normalized_intent in {"precio", "price", "pago", "urgencia", "cancelacion"}
        or _contains_any(normalized_message, RULE_KEYWORDS)
    )

    if should_use_services:
        service_rows = search_services(engine, normalized_message)
        if not service_rows:
            service_rows = get_active_services(engine)

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
