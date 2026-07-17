from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine


def is_message_processed(whatsapp_message_id: str | None) -> bool:
    if not whatsapp_message_id:
        return False

    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                SELECT 1
                FROM processed_messages
                WHERE whatsapp_message_id = :whatsapp_message_id
                LIMIT 1
                """
            ),
            {"whatsapp_message_id": whatsapp_message_id},
        ).fetchone()

        return result is not None


def mark_message_processed(
    whatsapp_message_id: str | None,
    telefono: str,
) -> None:
    if not whatsapp_message_id:
        return

    telefono = (telefono or "").strip()

    if not telefono:
        raise ValueError("telefono is required")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO processed_messages (
                    whatsapp_message_id,
                    telefono,
                    processed_at
                )
                VALUES (
                    :whatsapp_message_id,
                    :telefono,
                    NOW()
                )
                ON CONFLICT (whatsapp_message_id) DO NOTHING
                """
            ),
            {
                "whatsapp_message_id": whatsapp_message_id,
                "telefono": telefono,
            },
        )

        conn.execute(
            text(
                """
                DELETE FROM voice_processing_claims
                WHERE whatsapp_message_id = :whatsapp_message_id
                """
            ),
            {"whatsapp_message_id": whatsapp_message_id},
        )
