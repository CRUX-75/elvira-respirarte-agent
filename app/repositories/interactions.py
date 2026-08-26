from __future__ import annotations

from app.db.session import engine
from sqlalchemy import text


def get_latest_interaction_by_phone(
    telefono: str,
) -> dict | None:
    telefono = (telefono or "").strip()

    if not telefono:
        raise ValueError("telefono is required")

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    mensaje,
                    intent,
                    kb_used
                FROM interactions
                WHERE telefono = :telefono
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"telefono": telefono},
        ).mappings().first()

    return dict(row) if row else None


def save_interaction(
    *,
    patient_id: str | None,
    telefono: str,
    nombre: str | None = None,
    whatsapp_message_id: str | None = None,
    whatsapp_timestamp: str | None = None,
    mensaje_usuario: str | None = None,
    respuesta_elvira: str | None = None,
    intent: str | None = None,
    estado_anterior: str | None = None,
    nuevo_estado: str | None = None,
    next_action: str | None = None,
    state_reason: str | None = None,
    router_version: str | None = None,
    state_machine_version: str | None = None,
    kb_used: bool = False,
    escalation_required: bool = False,
    delivery_status: str | None = None,
    raw_payload: dict | None = None,
    error_message: str | None = None,
) -> None:
    telefono = (telefono or "").strip()

    if not telefono:
        raise ValueError("telefono is required")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO interactions (
                    patient_id,
                    telefono,
                    nombre,
                    mensaje,
                    respuesta,
                    intent,
                    estado_anterior,
                    nuevo_estado,
                    next_action,
                    state_reason,
                    router_version,
                    state_machine_version,
                    kb_used,
                    escalation_required,
                    whatsapp_message_id,
                    whatsapp_timestamp,
                    delivery_status,
                    created_at
                )
                VALUES (
                    :patient_id,
                    :telefono,
                    :nombre,
                    :mensaje,
                    :respuesta,
                    :intent,
                    :estado_anterior,
                    :nuevo_estado,
                    :next_action,
                    :state_reason,
                    :router_version,
                    :state_machine_version,
                    :kb_used,
                    :escalation_required,
                    :whatsapp_message_id,
                    :whatsapp_timestamp,
                    :delivery_status,
                    NOW()
                )
                """
            ),
            {
                "patient_id": patient_id,
                "telefono": telefono,
                "nombre": nombre,
                "mensaje": mensaje_usuario,
                "respuesta": respuesta_elvira,
                "intent": intent,
                "estado_anterior": estado_anterior,
                "nuevo_estado": nuevo_estado,
                "next_action": next_action,
                "state_reason": state_reason,
                "router_version": router_version,
                "state_machine_version": state_machine_version,
                "kb_used": kb_used,
                "escalation_required": escalation_required,
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
                "delivery_status": delivery_status,
            },
        )
