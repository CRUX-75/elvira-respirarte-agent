from app.graph.state import ElviraState
from app.services.intent import normalize_text, classify_intent
from app.graph.transitions import apply_state_transition
from app.services.llm import generate_llm_response


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


def node_generate_response(state: ElviraState) -> ElviraState:
    return generate_llm_response(state)
