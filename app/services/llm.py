from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.state import ElviraState


_SYSTEM_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "elvira_system.txt"
).read_text(encoding="utf-8").strip()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.3,
    api_key=settings.openai_api_key,
)


def _build_kb_section(state: ElviraState) -> str:
    if not state.kb_used or not state.kb_context:
        return (
            "Contexto KB controlado:\n"
            "No hay contexto relevante de la base de conocimiento para este mensaje."
        )

    sources = ", ".join(state.kb_sources) if state.kb_sources else "sin fuente especificada"

    return f"""Contexto KB controlado:
Fuentes: {sources}

{state.kb_context}"""


def generate_llm_response(state: ElviraState) -> ElviraState:
    """
    Elvira redacta — el LLM no decide flujo.

    The deterministic system already decided:
    - intent
    - next_action
    - state transition
    - opt-out
    - escalation

    KB context is informational only.
    """
    kb_section = _build_kb_section(state)

    user_message = f"""Mensaje del paciente:
{state.sanitized_input}

Estado anterior:
{state.estado_actual}

Nuevo estado:
{state.nuevo_estado}

Intención:
{state.intent}

Acción:
{state.next_action}

{kb_section}

Instrucciones de uso de KB:
- Use la KB solo como información de apoyo para redactar.
- No invente servicios, horarios, precios ni reglas que no estén en la KB.
- Si la KB no contiene información suficiente, responda de forma prudente y ofrezca ayudar a coordinar o escalar.
- No cambie la intención, el estado ni la acción indicada.
- Responda en máximo 2 o 3 frases, en español colombiano, como asistente de Respirarte."""

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    response = _llm.invoke(messages)
    state.respuesta = response.content.strip()
    return state
