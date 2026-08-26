import logging

from app.graph.state import ElviraState
from app.services.intent import normalize_text, classify_intent
from app.graph.transitions import apply_state_transition
from app.services.llm import generate_llm_response
from app.config import settings
from app.services.governance_boundary import (
    FUNCTIONAL_SCOPE_REFUSAL,
    INTERNAL_INFORMATION_REFUSAL,
    THIRD_PARTY_DATA_REFUSAL,
    build_mixed_h3_response,
    evaluate_h3_boundary,
    evaluate_h4_boundary,
)


logger = logging.getLogger(__name__)


def _is_service_context_followup(state: ElviraState) -> bool:
    if state.intent != "general":
        return False

    message = normalize_text(state.mensaje_original)

    return (
        "orden medica" in message
        or "orden médica" in message
    )


def _resolve_previous_service_context(
    state: ElviraState,
    engine,
    get_kb_context,
) -> dict | None:
    if not _is_service_context_followup(state):
        return None

    try:
        from app.repositories.interactions import (
            get_latest_interaction_by_phone,
        )

        previous = get_latest_interaction_by_phone(state.telefono)
    except Exception as exc:
        logger.warning(
            "Previous service context unavailable: %s",
            exc,
        )
        return None

    if (
        not previous
        or previous.get("intent") != "servicios"
        or previous.get("kb_used") is not True
    ):
        return None

    previous_message = (previous.get("mensaje") or "").strip()

    if not previous_message:
        return None

    try:
        result = get_kb_context(
            engine,
            intent="servicios",
            message=previous_message,
            estado_actual=state.nuevo_estado or state.estado_actual,
        )
    except Exception as exc:
        logger.warning(
            "Previous service re-grounding unavailable: %s",
            exc,
        )
        return None

    if (
        not result.get("kb_used")
        or result.get("service_grounding_status") != "exact"
        or "kb_services" not in result.get("kb_sources", [])
    ):
        return None

    return result


def _load_schedule_rows_for_date_resolution() -> list[dict] | None:
    """Load KB schedule rows for deterministic appointment slot generation."""

    if not settings.kb_runtime_enabled:
        return None

    try:
        schedule_reader = globals().get("get_all_schedules")
        db_engine = globals().get("engine")

        if schedule_reader is None or db_engine is None:
            from app.db.session import engine as runtime_engine
            from app.repositories.kb_schedules import (
                get_all_schedules as runtime_get_all_schedules,
            )

            schedule_reader = runtime_get_all_schedules
            db_engine = runtime_engine

        return schedule_reader(db_engine)
    except Exception as exc:
        logger.warning("KB schedule rows unavailable for date resolution: %s", exc)
        return None


def node_sanitize_input(state: ElviraState) -> ElviraState:
    state.sanitized_input = normalize_text(state.mensaje_original)
    return state


def node_classify_intent(state: ElviraState) -> ElviraState:
    state.intent = classify_intent(
        message=state.mensaje_original,
        current_state=state.estado_actual,
    )
    return state


def node_transition_state(state: ElviraState) -> ElviraState:
    return apply_state_transition(state)


def node_resolve_date_context(state: ElviraState, now=None) -> ElviraState:
    """
    Resolve appointment date references deterministically.

    This node does not decide intent, state, availability, or scheduling.
    It only enriches the state with controlled context for response wording.
    """
    appointment_date_intents = {"cita", "fecha_cita", "hora_cita"}
    appointment_states = {"ST_CITA_FECHA", "ST_CITA_FRANJA", "ST_CITA_PENDIENTE"}

    current_state = state.nuevo_estado or state.estado_actual

    if state.intent not in appointment_date_intents and current_state not in appointment_states:
        return state

    try:
        from app.services.date_resolver import resolve_requested_date

        schedule_rows = _load_schedule_rows_for_date_resolution()
        result = resolve_requested_date(
            state.mensaje_original,
            now=now,
            schedule_rows=schedule_rows,
        )

        state.fecha_actual_colombia = result.fecha_actual_colombia.isoformat()
        state.fecha_solicitada = (
            result.fecha_solicitada.isoformat()
            if result.fecha_solicitada
            else None
        )
        state.fecha_solicitada_texto = result.fecha_solicitada_texto
        state.dia_semana_solicitado = result.dia_semana_solicitado
        state.es_dia_disponible = result.es_dia_disponible
        state.slots_candidatos = list(result.slots_candidatos)
        state.is_weekend = result.is_weekend
        state.is_colombia_holiday = result.is_colombia_holiday
        state.colombia_holiday_name = result.colombia_holiday_name
        state.date_resolution_source = result.source

        if (
            state.intent == "fecha_cita"
            and state.nuevo_estado == "ST_CITA_FRANJA"
            and not state.fecha_solicitada
        ):
            state.nuevo_estado = "ST_CITA_FECHA"
            state.estado_actual = "ST_CITA_FECHA"
            state.next_action = "ask_preferred_date"
            state.state_reason = "missing_fecha_solicitada_guard"

        if (
            state.intent == "fecha_cita"
            and state.nuevo_estado == "ST_CITA_FRANJA"
            and state.fecha_solicitada
            and (
                state.is_weekend is True
                or state.is_colombia_holiday is True
                or state.es_dia_disponible is False
                or not state.slots_candidatos
            )
        ):
            state.nuevo_estado = "ST_CITA_FECHA"
            state.estado_actual = "ST_CITA_FECHA"
            state.next_action = "ask_preferred_date"
            state.state_reason = "unavailable_date_guard"

    except Exception as exc:
        # Date resolution failure must not block the conversational core.
        logger.warning("Date context resolution skipped: %s", exc)

    return state


def node_load_kb_context(state: ElviraState) -> ElviraState:
    """
    Load deterministic Knowledge Base context after intent/state transition.

    The KB is informational only:
    - It does not decide intent.
    - It does not decide state.
    - It does not decide next_action.
    - It only provides controlled context for response wording.

    If KB loading fails, the conversational core must continue.
    We do not overwrite previous state-machine fields on failure.
    """
    if not settings.kb_runtime_enabled:
        return state

    try:
        from app.db.session import engine
        from app.services.kb import get_kb_context

        result = get_kb_context(
            engine,
            intent=state.intent,
            message=state.mensaje_original,
            estado_actual=state.nuevo_estado or state.estado_actual,
        )

        previous_service_context = _resolve_previous_service_context(
            state,
            engine,
            get_kb_context,
        )
        if previous_service_context is not None:
            result = previous_service_context

        state.kb_used = bool(result.get("kb_used", False))
        state.kb_sources = list(result.get("kb_sources", []))
        state.kb_context = result.get("kb_context") or None
        state.matched_service_id = result.get(
            "matched_service_id"
        )
        state.matched_service_term = result.get(
            "matched_service_term"
        )
        state.matched_service_field = result.get(
            "matched_service_field"
        )
        state.service_grounding_status = result.get(
            "service_grounding_status"
        )

        # P6-F.9.97 service grounding guard.
        if (
            state.intent == "servicios"
            and (
                not state.kb_used
                or state.service_grounding_status
                in {"partial", "not_found"}
            )
        ):
            state.next_action = "escalate_unknown_service"
            state.escalation_required = True

            if state.service_grounding_status == "partial":
                state.state_reason = (
                    "partial_service_match_requires_grounded_review"
                )
            else:
                state.service_grounding_status = "not_found"
                state.state_reason = (
                    "unknown_service_requires_grounded_review"
                )

    except Exception as exc:
        # KB failure must not block the conversational core.
        # Important: do not overwrite existing state-machine values here.
        logger.warning("KB context loading skipped: %s", exc)

        if state.kb_sources is None:
            state.kb_sources = []

        if not state.kb_context:
            state.kb_context = None

    return state


def node_generate_response(state: ElviraState) -> ElviraState:
    if state.intent not in {"optout", "urgencia"}:
        privacy_boundary = evaluate_h4_boundary(state.mensaje_original)

        if privacy_boundary.kind == "protected_third_party":
            state.respuesta = THIRD_PARTY_DATA_REFUSAL
            state.next_action = "refuse_third_party_data"
            state.state_reason = "unauthorized_third_party_data_request"
            return state

        boundary = evaluate_h3_boundary(state.mensaje_original)

        if boundary.kind == "protected_internal":
            state.respuesta = INTERNAL_INFORMATION_REFUSAL
            state.next_action = "refuse_internal_information"
            state.state_reason = "protected_internal_information_request"
            return state

        if boundary.kind == "out_of_scope":
            state.respuesta = FUNCTIONAL_SCOPE_REFUSAL
            state.next_action = "refuse_out_of_scope"
            state.state_reason = "request_outside_functional_scope"
            return state

        if boundary.kind == "mixed":
            state.respuesta = build_mixed_h3_response(state)
            state.state_reason = (
                "mixed_request_internal_information_refused"
            )
            return state

    return generate_llm_response(state)
