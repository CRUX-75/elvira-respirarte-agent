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


def _build_requested_date_reference(state: ElviraState) -> str:
    """
    Build a natural patient-facing reference to the resolved appointment date.

    Examples:
    - "mañana, jueves 14 de mayo"
    - "pasado mañana, viernes 15 de mayo"
    - "domingo 17 de mayo"
    """
    fecha_texto = state.fecha_solicitada_texto or "la fecha solicitada"
    message = (state.sanitized_input or state.mensaje_original or "").lower()

    if "pasado mañana" in message or "pasado manana" in message or "pasado maniana" in message:
        return f"pasado mañana, {fecha_texto}"

    if "mañana" in message or "manana" in message or "maniana" in message:
        return f"mañana, {fecha_texto}"

    if "hoy" in message:
        return f"hoy, {fecha_texto}"

    return fecha_texto


def _build_patient_afternoon_window(state: ElviraState) -> str:
    """
    Return the real patient-facing afternoon service window for domiciliary consultations.

    This mirrors the currently approved Respirarte operational rules:
    - Monday, Tuesday, Thursday, Friday: 3:00 p. m. to 7:00 p. m.
    - Wednesday: 3:00 p. m. to 6:00 p. m.
    """
    if state.dia_semana_solicitado == "miércoles":
        return "entre 3:00 p. m. y 6:00 p. m."

    return "entre 3:00 p. m. y 7:00 p. m."


def _build_date_context_section(state: ElviraState) -> str:
    if not state.fecha_solicitada:
        return (
            "Contexto determinístico de fecha:\n"
            "No hay fecha solicitada detectada para este mensaje.\n\n"
            "Reglas para usar este contexto:\n"
            "- No interprete disponibilidad operativa sin una fecha solicitada explícita.\n"
            "- No diga que hoy no se opera, que hoy no hay atención o que el día no está disponible.\n"
            "- Si el flujo requiere coordinar una cita, limite la respuesta a registrar la preferencia o pedir la información faltante."
        )

    slots = (
        ", ".join(state.slots_candidatos)
        if state.slots_candidatos
        else "sin slots candidatos"
    )

    return f"""Contexto determinístico de fecha:
Fecha actual en Colombia: {state.fecha_actual_colombia or "no detectada"}
Fecha solicitada por el paciente: {state.fecha_solicitada or "no detectada"}
Día de semana solicitado: {state.dia_semana_solicitado or "no detectado"}
Día operativo según reglas internas: {state.es_dia_disponible}
Slots candidatos generados: {slots}
Fuente: {state.date_resolution_source or "sin fuente"}

Reglas para usar este contexto:
- Este contexto es determinístico e informativo.
- No confirma disponibilidad real de agenda.
- Si Día operativo según reglas internas es False, no ofrezca horas ni slots.
- Si hay slots candidatos, preséntelos solo como opciones a revisar o validar, nunca como disponibilidad confirmada.
- Use expresiones como “podemos revisar”, “podemos validar disponibilidad” o “puedo registrar su preferencia”."""


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

    if state.next_action == "ask_preferred_date":
        state.respuesta = (
            "Claro, con muchísimo gusto. "
            "Le cuento que las atenciones domiciliarias se manejan solamente en la tarde, "
            "normalmente en dos franjas: de 3:00 p. m. a 5:00 p. m. "
            "o de 5:00 p. m. a 7:00 p. m. "
            "¿Para qué día le gustaría agendar su cita?"
        )
        return state

    if state.next_action == "ask_preferred_time":
        date_reference = _build_requested_date_reference(state)

        if state.is_weekend:
            state.respuesta = (
                f"Se refiere a {date_reference}. "
                "Ese día no se atienden consultas. "
                "¿Le gustaría indicarme otro día entre semana?"
            )
            return state

        if state.is_colombia_holiday:
            holiday_detail = (
                f" porque corresponde al festivo de {state.colombia_holiday_name}"
                if state.colombia_holiday_name
                else ""
            )
            state.respuesta = (
                f"Se refiere a {date_reference}. "
                f"Ese día no se atienden consultas{holiday_detail}. "
                "¿Le gustaría indicarme otro día entre semana?"
            )
            return state

        slots = " o ".join(
            f"entre {slot.replace('–', ' y ')}"
            for slot in state.slots_candidatos
        )

        if slots:
            state.respuesta = (
                f"Perfecto, se refiere a {date_reference}. "
                "La doctora solo atiende consultas domiciliarias en la tarde. "
                f"Para ese día tengo disponibles {slots} "
                "¿Cuál le sirve mejor?"
            )
        else:
            afternoon_window = _build_patient_afternoon_window(state)
            state.respuesta = (
                f"Perfecto, se refiere a {date_reference}. "
                f"La doctora solo atiende consultas domiciliarias en la tarde, {afternoon_window} "
                "¿Qué horario le gustaría que registre como preferencia?"
            )
        return state

    if state.next_action == "ask_specific_time_slot":
        state.respuesta = (
            "Para continuar, por favor elija una de las franjas disponibles: "
            "de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. "
            "¿Cuál le queda mejor?"
        )
        return state

    if state.next_action == "ask_specific_time_slot":
        state.respuesta = (
            "Para continuar, por favor elija una de las franjas disponibles: "
            "de 3:00 p. m. a 5:00 p. m. o de 5:00 p. m. a 7:00 p. m. "
            "¿Cuál le queda mejor?"
        )
        return state

    if state.next_action == "confirm_appointment_request":
        state.respuesta = (
            "Perfecto, queda registrada su solicitud para esa franja. "
            "La Dra. D'Aleman le confirmará la cita."
        )
        return state

    kb_section = _build_kb_section(state)
    date_context_section = _build_date_context_section(state)

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

{date_context_section}

Instrucciones de uso de KB:
- Use la KB como única fuente confirmada cuando la pregunta sea sobre servicios, horarios, cobertura, precios, costos, disponibilidad o reglas de atención.
- No invente servicios que no aparezcan explícitamente en la KB.
- No invente horarios, días de atención, zonas de cobertura, requisitos, precios, tarifas, costos, promociones ni descuentos.
- Si el paciente pregunta por precios o costos y la KB no contiene un valor explícito, no dé ningún valor. Indique de forma amable que el valor debe confirmarse directamente con el equipo de Respirarte o después de la valoración correspondiente.
- Si el paciente pregunta por un servicio que no aparece en la KB, no confirme que Respirarte lo ofrece. Responda que no tiene esa información confirmada y ofrezca ayudar a escalar la consulta.
- No mencione al paciente la KB, base de conocimiento, PostgreSQL, sistema, modelo, prompt, herramientas ni detalles técnicos internos.
- No cambie la intención, el estado ni la acción indicada.
- Responda en máximo 2 o 3 frases, en español colombiano, cálido y respetuoso, como asistente de Respirarte."""

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    response = _llm.invoke(messages)
    state.respuesta = response.content.strip()
    return state
