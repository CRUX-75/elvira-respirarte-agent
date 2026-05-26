from typing import Literal, Optional

from pydantic import BaseModel, Field


AppointmentRequestStatus = Literal[
    "nueva",
    "pendiente_datos",
    "pendiente_confirmacion",
    "confirmada",
    "reagendada",
    "cancelada",
    "cerrada",
]

AppointmentRequestSource = Literal[
    "whatsapp",
    "manual",
    "system",
]


class AppointmentRequest(BaseModel):
    """
    Internal appointment request model.

    Represents the lifecycle of a patient appointment request.
    This is not a confirmed appointment and must not be treated as one.
    """

    # Identity
    id_solicitud: str = Field(..., description="Unique appointment request ID")
    telefono: str = Field(..., description="Patient phone number")
    nombre_paciente: Optional[str] = Field(default=None)

    # Request context
    estado_solicitud: AppointmentRequestStatus = Field(default="nueva")
    intent_origen: str = Field(default="cita")
    canal_origen: AppointmentRequestSource = Field(default="whatsapp")

    # Requested appointment data: patient preference only
    fecha_solicitada: Optional[str] = Field(default=None)
    franja_solicitada: Optional[str] = Field(default=None)
    hora_solicitada_texto: Optional[str] = Field(default=None)

    # Accepted appointment data: patient accepted proposal, not final confirmation
    fecha_aceptada: Optional[str] = Field(default=None)
    franja_aceptada: Optional[str] = Field(default=None)

    # Confirmed appointment data: only after human/clinic confirmation
    fecha_confirmada: Optional[str] = Field(default=None)
    franja_confirmada: Optional[str] = Field(default=None)

    # Required operational visibility fields
    servicio_solicitado: Optional[str] = Field(default=None)
    direccion_domicilio: Optional[str] = Field(default=None)

    # Operational notes
    observaciones: Optional[str] = Field(default=None)
    motivo_reagendamiento: Optional[str] = Field(default=None)
    motivo_cancelacion: Optional[str] = Field(default=None)

    # Audit fields
    source_interaction_id: Optional[str] = Field(default=None)
    created_by: str = Field(default="system")
    updated_by: Optional[str] = Field(default=None)

    # Timestamps as ISO strings for consistency with current lightweight models
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)
