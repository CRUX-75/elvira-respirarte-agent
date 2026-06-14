from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from app.models.appointment_request import AppointmentRequest
from app.repositories.appointment_request_repository import (
    ACTIVE_APPOINTMENT_REQUEST_STATES,
)


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row._mapping)


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class PostgresAppointmentRequestRepository:
    """
    SQLAlchemy/raw-SQL implementation of AppointmentRequestRepository.

    Business rules belong to AppointmentRequestService.
    This repository only persists and retrieves AppointmentRequest rows.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def save(self, request: AppointmentRequest) -> AppointmentRequest:
        params = request.model_dump()

        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    INSERT INTO appointment_requests (
                        id_solicitud,
                        telefono,
                        nombre_paciente,
                        estado_solicitud,
                        intent_origen,
                        canal_origen,
                        fecha_solicitada,
                        franja_solicitada,
                        hora_solicitada_texto,
                        fecha_aceptada,
                        franja_aceptada,
                        fecha_confirmada,
                        franja_confirmada,
                        servicio_solicitado,
                        direccion_domicilio,
                        tipo_cita,
                        eps,
                        barrio,
                        edad_paciente,
                        notas_clinicas_breves,
                        observaciones,
                        motivo_reagendamiento,
                        motivo_cancelacion,
                        source_interaction_id,
                        created_by,
                        updated_by,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :id_solicitud,
                        :telefono,
                        :nombre_paciente,
                        :estado_solicitud,
                        :intent_origen,
                        :canal_origen,
                        :fecha_solicitada,
                        :franja_solicitada,
                        :hora_solicitada_texto,
                        :fecha_aceptada,
                        :franja_aceptada,
                        :fecha_confirmada,
                        :franja_confirmada,
                        :servicio_solicitado,
                        :direccion_domicilio,
                        :tipo_cita,
                        :eps,
                        :barrio,
                        :edad_paciente,
                        :notas_clinicas_breves,
                        :observaciones,
                        :motivo_reagendamiento,
                        :motivo_cancelacion,
                        :source_interaction_id,
                        :created_by,
                        :updated_by,
                        COALESCE(:created_at, CURRENT_TIMESTAMP),
                        COALESCE(:updated_at, CURRENT_TIMESTAMP)
                    )
                    RETURNING *
                    """
                ),
                params,
            ).fetchone()

        return self._row_to_model(row)

    def update(self, request: AppointmentRequest) -> AppointmentRequest:
        params = request.model_dump()

        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    UPDATE appointment_requests
                    SET telefono = :telefono,
                        nombre_paciente = :nombre_paciente,
                        estado_solicitud = :estado_solicitud,
                        intent_origen = :intent_origen,
                        canal_origen = :canal_origen,
                        fecha_solicitada = :fecha_solicitada,
                        franja_solicitada = :franja_solicitada,
                        hora_solicitada_texto = :hora_solicitada_texto,
                        fecha_aceptada = :fecha_aceptada,
                        franja_aceptada = :franja_aceptada,
                        fecha_confirmada = :fecha_confirmada,
                        franja_confirmada = :franja_confirmada,
                        servicio_solicitado = :servicio_solicitado,
                        direccion_domicilio = :direccion_domicilio,
                        tipo_cita = :tipo_cita,
                        eps = :eps,
                        barrio = :barrio,
                        edad_paciente = :edad_paciente,
                        notas_clinicas_breves = :notas_clinicas_breves,
                        observaciones = :observaciones,
                        motivo_reagendamiento = :motivo_reagendamiento,
                        motivo_cancelacion = :motivo_cancelacion,
                        source_interaction_id = :source_interaction_id,
                        created_by = :created_by,
                        updated_by = :updated_by,
                        created_at = COALESCE(:created_at, created_at),
                        updated_at = COALESCE(:updated_at, CURRENT_TIMESTAMP)
                    WHERE id_solicitud = :id_solicitud
                    RETURNING *
                    """
                ),
                params,
            ).fetchone()

        if row is None:
            raise ValueError(
                f"AppointmentRequest not found: {request.id_solicitud}"
            )

        return self._row_to_model(row)

    def get_by_id(self, id_solicitud: str) -> AppointmentRequest | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT *
                    FROM appointment_requests
                    WHERE id_solicitud = :id_solicitud
                    LIMIT 1
                    """
                ),
                {"id_solicitud": id_solicitud},
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    def find_active_by_telefono(self, telefono: str) -> AppointmentRequest | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT *
                    FROM appointment_requests
                    WHERE telefono = :telefono
                      AND estado_solicitud IN :active_states
                    ORDER BY updated_at DESC,
                             created_at DESC,
                             id_solicitud DESC
                    LIMIT 1
                    """
                ).bindparams(bindparam("active_states", expanding=True)),
                {
                    "telefono": telefono,
                    "active_states": tuple(ACTIVE_APPOINTMENT_REQUEST_STATES),
                },
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    def _row_to_model(self, row: Any) -> AppointmentRequest:
        data = _row_to_dict(row)

        if data is None:
            raise ValueError("Cannot map empty appointment request row")

        data["created_at"] = _normalize_timestamp(data.get("created_at"))
        data["updated_at"] = _normalize_timestamp(data.get("updated_at"))

        return AppointmentRequest(**data)
