from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.graph.state import ElviraState
from app.config import settings

_SYSTEM_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "elvira_system.txt"
).read_text(encoding="utf-8").strip()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.3,
    api_key=settings.openai_api_key,
)


def generate_llm_response(state: ElviraState) -> ElviraState:
    """
    Elvira redacta — el LLM no decide flujo.
    User message fiel al formato probado en n8n.
    """
    user_message = f"""Mensaje del paciente:
{state.sanitized_input}

Estado:
{state.estado_actual}

Intención:
{state.intent}

Acción:
{state.next_action}

Responda en máximo 2 o 3 frases, en español colombiano, como asistente de Respirarte."""

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    response = _llm.invoke(messages)
    state.respuesta = response.content.strip()
    return state
