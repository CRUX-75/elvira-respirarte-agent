from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.appointment_request import AppointmentRequest


COLOMBIA_TIMEZONE = "America/Bogota"


def _last_four_digits(value: str) -> str:
    digits = "".join(char for char in value if char.isdigit())
    return digits[-4:] if len(digits) >= 4 else digits.zfill(4)


def generate_appointment_request_id(
    telefono: str,
    now: datetime | None = None,
) -> str:
    """Generate a visible appointment request ID using Colombia local time."""
    colombia_tz = ZoneInfo(COLOMBIA_TIMEZONE)

    if now is None:
        current_time = datetime.now(colombia_tz)
    elif now.tzinfo is None:
        current_time = now.replace(tzinfo=colombia_tz)
    else:
        current_time = now.astimezone(colombia_tz)

    timestamp = current_time.strftime("%Y%m%d-%H%M%S")
    last4 = _last_four_digits(telefono)

    return f"SOL-{timestamp}-{last4}"


def create_appointment_request(
    telefono: str,
    nombre_paciente: str | None = None,
    source_interaction_id: str | None = None,
    intent_origen: str = "cita",
    canal_origen: str = "whatsapp",
    fecha_solicitada: str | None = None,
    franja_solicitada: str | None = None,
    hora_solicitada_texto: str | None = None,
    servicio_solicitado: str | None = None,
    direccion_domicilio: str | None = None,
    observaciones: str | None = None,
    now: datetime | None = None,
) -> AppointmentRequest:
    """Create a new internal AppointmentRequest.

    This function creates a request, not a confirmed appointment.
    It does not persist data or call external services.
    """
    colombia_tz = ZoneInfo(COLOMBIA_TIMEZONE)

    if now is None:
        current_time = datetime.now(colombia_tz)
    elif now.tzinfo is None:
        current_time = now.replace(tzinfo=colombia_tz)
    else:
        current_time = now.astimezone(colombia_tz)

    iso_timestamp = current_time.isoformat()

    return AppointmentRequest(
        id_solicitud=generate_appointment_request_id(
            telefono=telefono,
            now=current_time,
        ),
        telefono=telefono,
        nombre_paciente=nombre_paciente,
        estado_solicitud="nueva",
        intent_origen=intent_origen,
        canal_origen=canal_origen,
        fecha_solicitada=fecha_solicitada,
        franja_solicitada=franja_solicitada,
        hora_solicitada_texto=hora_solicitada_texto,
        fecha_aceptada=None,
        franja_aceptada=None,
        fecha_confirmada=None,
        franja_confirmada=None,
        servicio_solicitado=servicio_solicitado,
        direccion_domicilio=direccion_domicilio,
        observaciones=observaciones,
        source_interaction_id=source_interaction_id,
        created_by="system",
        updated_by=None,
        created_at=iso_timestamp,
        updated_at=iso_timestamp,
    )
