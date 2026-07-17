from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text

from app.config import settings
from app.db.session import engine


@dataclass(frozen=True)
class VoiceProcessingClaim:
    whatsapp_message_id: str
    claim_token: str
    lease_expires_at: datetime


def try_claim_voice_processing(
    *,
    whatsapp_message_id: str,
    telefono: str,
) -> VoiceProcessingClaim | None:
    whatsapp_message_id = (whatsapp_message_id or "").strip()
    telefono = (telefono or "").strip()

    if not whatsapp_message_id:
        raise ValueError("whatsapp_message_id is required")

    if not telefono:
        raise ValueError("telefono is required")

    lease_seconds = settings.voice_processing_lease_seconds

    if lease_seconds <= 0:
        raise ValueError("voice processing lease must be positive")

    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                    INSERT INTO voice_processing_claims (
                        whatsapp_message_id,
                        telefono,
                        claim_token,
                        claimed_at,
                        lease_expires_at
                    )
                    VALUES (
                        :whatsapp_message_id,
                        :telefono,
                        gen_random_uuid(),
                        NOW(),
                        NOW() + make_interval(secs => :lease_seconds)
                    )
                    ON CONFLICT (whatsapp_message_id) DO UPDATE
                    SET
                        telefono = EXCLUDED.telefono,
                        claim_token = gen_random_uuid(),
                        claimed_at = NOW(),
                        lease_expires_at = (
                            NOW() + make_interval(
                                secs => :lease_seconds
                            )
                        )
                    WHERE
                        voice_processing_claims.lease_expires_at <= NOW()
                    RETURNING
                        whatsapp_message_id,
                        claim_token::text AS claim_token,
                        lease_expires_at
                    """
                ),
                {
                    "whatsapp_message_id": whatsapp_message_id,
                    "telefono": telefono,
                    "lease_seconds": lease_seconds,
                },
            )
            .mappings()
            .first()
        )

    if row is None:
        return None

    return VoiceProcessingClaim(
        whatsapp_message_id=row["whatsapp_message_id"],
        claim_token=row["claim_token"],
        lease_expires_at=row["lease_expires_at"],
    )
