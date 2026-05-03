from __future__ import annotations

from typing import Any
import json

from sqlalchemy import text

from app.db.session import engine


def save_interaction(
    *,
    patient_id: str | None,
    telefono: str,
    whatsapp_message_id: str | None = None,
    whatsapp_timestamp: str | None = None,
    mensaje_usuario: str | None = None,
    respuesta_elvira: str | None = None,
    intent: str | None = None,
    estado_anterior: str | None = None,
    nuevo_estado: str | None = None,
    next_action: str | None = None,
    delivery_status: str | None = None,
    router_version: str | None = None,
    state_machine_version: str | None = None,
    raw_payload: dict[str, Any] | None = None,
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
                    whatsapp_message_id,
                    whatsapp_timestamp,
                    mensaje,
                    respuesta,
                    intent,
                    estado_anterior,
                    nuevo_estado,
                    next_action,
                    delivery_status,
                    router_version,
                    state_machine_version,
                    created_at
                )
                VALUES (
                    :patient_id,
                    :telefono,
                    :whatsapp_message_id,
                    :whatsapp_timestamp,
                    :mensaje,
                    :respuesta,
                    :intent,
                    :estado_anterior,
                    :nuevo_estado,
                    :next_action,
                    :delivery_status,
                    :router_version,
                    :state_machine_version,
                    NOW()
                )
                """
            ),
            {
                "patient_id": patient_id,
                "telefono": telefono,
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
                "mensaje_usuario": mensaje,
                "respuesta_elvira": respuesta,
                "intent": intent,
                "estado_anterior": estado_anterior,
                "nuevo_estado": nuevo_estado,
                "next_action": next_action,
                "delivery_status": delivery_status,
                "router_version": router_version,
                "state_machine_version": state_machine_version,
            },
        )