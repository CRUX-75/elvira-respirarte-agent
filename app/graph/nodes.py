import logging

from app.graph.state import ElviraState
from app.services.intent import normalize_text, classify_intent
from app.graph.transitions import apply_state_transition
from app.services.llm import generate_llm_response
from app.config import settings


logger = logging.getLogger(__name__)


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

        state.kb_used = bool(result.get("kb_used", False))
        state.kb_sources = list(result.get("kb_sources", []))
        state.kb_context = result.get("kb_context") or None

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
    return generate_llm_response(state)
