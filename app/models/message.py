from pydantic import BaseModel, Field
from typing import Optional


class IncomingMessage(BaseModel):
    telefono: str = Field(..., description="Número de teléfono del paciente")
    mensaje: str = Field(..., description="Mensaje entrante de WhatsApp")
    nombre: Optional[str] = Field(default=None)
    estado_actual: str = Field(default="ST_INIT")
    opt_out: bool = Field(default=False)


class ProcessedMessage(BaseModel):
    telefono: str
    mensaje_original: str
    sanitized_input: str
    nombre: Optional[str] = None
    estado_actual: str = "ST_INIT"
    opt_out: bool = False
    fecha_actual_contexto: Optional[str] = None
    hora_actual_contexto: Optional[str] = None
    timezone_contexto: str = "America/Bogota"
