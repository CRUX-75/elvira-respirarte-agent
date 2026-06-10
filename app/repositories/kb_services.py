from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


def get_active_services(engine: Engine) -> list[dict[str, Any]]:
    """
    Return all active services from the Knowledge Base.

    The KB is informational only.
    It must not decide state, intent, next_action, opt-out, or escalation logic.
    """
    query = text(
        """
        SELECT
            service_id,
            service_name,
            category,
            objective,
            techniques,
            patient_scope,
            modality,
            is_active,
            public_answer_short,
            public_answer_long,
            search_terms,
            escalation_required
        FROM kb_services
        WHERE is_active = TRUE
        ORDER BY service_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query).mappings().all()

    return [dict(row) for row in rows]


def get_service_by_id(engine: Engine, service_id: str) -> dict[str, Any] | None:
    """
    Return one active service by service_id.
    """
    query = text(
        """
        SELECT
            service_id,
            service_name,
            category,
            objective,
            techniques,
            patient_scope,
            modality,
            is_active,
            public_answer_short,
            public_answer_long,
            search_terms,
            escalation_required
        FROM kb_services
        WHERE service_id = :service_id
        AND is_active = TRUE
        LIMIT 1
        """
    )

    with engine.begin() as conn:
        row = conn.execute(query, {"service_id": service_id}).mappings().first()

    return dict(row) if row else None


def search_services(engine: Engine, search_text: str) -> list[dict[str, Any]]:
    """
    Basic deterministic service search.

    This is intentionally simple for P5.
    Later we can improve it with synonyms, embeddings, or full-text search.
    """
    normalized_search = f"%{search_text.strip()}%"

    query = text(
        """
        SELECT
            service_id,
            service_name,
            category,
            objective,
            techniques,
            patient_scope,
            modality,
            is_active,
            public_answer_short,
            public_answer_long,
            search_terms,
            escalation_required
        FROM kb_services
        WHERE is_active = TRUE
        AND (
            service_name ILIKE :search
            OR category ILIKE :search
            OR objective ILIKE :search
            OR techniques ILIKE :search
            OR patient_scope ILIKE :search
            OR modality ILIKE :search
            OR public_answer_short ILIKE :search
            OR public_answer_long ILIKE :search
            OR search_terms ILIKE :search
        )
        ORDER BY service_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query, {"search": normalized_search}).mappings().all()

    return [dict(row) for row in rows]
