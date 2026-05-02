from langgraph.graph import StateGraph, START, END
from app.graph.state import ElviraState
from app.graph.nodes import (
    node_sanitize_input,
    node_classify_intent,
    node_transition_state,
    node_generate_response,
)
from app.models.message import IncomingMessage


def build_graph():
    builder = StateGraph(ElviraState)

    builder.add_node("sanitize_input", node_sanitize_input)
    builder.add_node("classify_intent", node_classify_intent)
    builder.add_node("transition_state", node_transition_state)
    builder.add_node("generate_response", node_generate_response)

    builder.add_edge(START, "sanitize_input")
    builder.add_edge("sanitize_input", "classify_intent")
    builder.add_edge("classify_intent", "transition_state")
    builder.add_edge("transition_state", "generate_response")
    builder.add_edge("generate_response", END)

    return builder.compile()


elvira_graph = build_graph()


def process_message(message: IncomingMessage) -> ElviraState:
    initial_state = ElviraState(
        telefono=message.telefono,
        mensaje_original=message.mensaje,
        sanitized_input="",
        nombre=message.nombre,
        estado_actual=message.estado_actual,
        opt_out=message.opt_out,
    )
    result = elvira_graph.invoke(initial_state)
    return ElviraState(**result)
