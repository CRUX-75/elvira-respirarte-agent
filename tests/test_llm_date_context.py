from app.graph.state import ElviraState
from app.services import llm


class FakeResponse:
    content = "Respuesta simulada."


class FakeLLM:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return FakeResponse()


def test_llm_prompt_includes_deterministic_date_context(monkeypatch):
    fake_llm = FakeLLM()
    monkeypatch.setattr(llm, "_llm", fake_llm)

    state = ElviraState(
        telefono="573001112233",
        mensaje_original="Mañana en la tarde",
        sanitized_input="mañana en la tarde",
        estado_actual="ST_CITA_FRANJA",
        nuevo_estado="ST_CITA_FRANJA",
        intent="fecha_cita",
        next_action="ask_preferred_time",
        fecha_actual_colombia="2026-05-08",
        fecha_solicitada="2026-05-09",
        dia_semana_solicitado="sábado",
        es_dia_disponible=False,
        slots_candidatos=[],
        date_resolution_source="deterministic_relative_date_resolver",
    )

    result = llm.generate_llm_response(state)

    human_message = fake_llm.messages[1].content

    assert result.respuesta == "Respuesta simulada."
    assert "Contexto determinístico de fecha:" in human_message
    assert "Fecha actual en Colombia: 2026-05-08" in human_message
    assert "Fecha solicitada por el paciente: 2026-05-09" in human_message
    assert "Día de semana solicitado: sábado" in human_message
    assert "Día operativo según reglas internas: False" in human_message
    assert "Slots candidatos generados: sin slots candidatos" in human_message
    assert "no ofrezca horas ni slots" in human_message
    assert "nunca como disponibilidad confirmada" in human_message
