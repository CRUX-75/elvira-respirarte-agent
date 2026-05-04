from typing import Optional, Literal

from pydantic import BaseModel, Field


Intent = Literal[
    "general",
    "cita",
    "fecha_cita",
    "hora_cita",
    "pago",
    "servicios",
    "horarios",
    "reglas",
    "optout",
    "urgencia",
]


class ElviraState(BaseModel):
    telefono: str
    mensaje_original: str
    sanitized_input: str
    nombre: Optional[str] = None
    estado_anterior: str = "ST_INIT"
    estado_actual: str = "ST_INIT"
    nuevo_estado: str = "ST_INIT"
    intent: Intent = "general"
    next_action: str = "answer_general"
    respuesta: Optional[str] = None
    opt_out: bool = False
    escalation_required: bool = False

    # Knowledge Base context.
    # Informational only. Never used to decide state transitions.
    kb_used: bool = False
    kb_sources: list[str] = Field(default_factory=list)
    kb_context: Optional[str] = None

    state_reason: Optional[str] = None
    router_version: str = "intent-v1"
    state_machine_version: str = "sm-v1"
    fecha_actual_contexto: Optional[str] = None
    hora_actual_contexto: Optional[str] = None
    timezone_contexto: str = "America/Bogota"
