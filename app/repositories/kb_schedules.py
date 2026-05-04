from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


def get_available_schedules(engine: Engine) -> list[dict[str, Any]]:
    """
    Return available schedules from the Knowledge Base.

    is_available is stored as TEXT to preserve Google Sheets values such as:
    true, false, pending, —.
    """
    query = text(
        """
        SELECT
            schedule_id,
            day_type,
            day_name,
            modality,
            start_time,
            end_time,
            slot_duration_minutes,
            max_patients,
            location_type,
            is_available,
            notes
        FROM kb_schedules
        WHERE LOWER(is_available) IN ('true', 'yes', 'available', 'disponible')
        ORDER BY schedule_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query).mappings().all()

    return [dict(row) for row in rows]


def get_all_schedules(engine: Engine) -> list[dict[str, Any]]:
    """
    Return all schedule rows, including unavailable or pending ones.
    Useful when Elvira needs to explain limitations.
    """
    query = text(
        """
        SELECT
            schedule_id,
            day_type,
            day_name,
            modality,
            start_time,
            end_time,
            slot_duration_minutes,
            max_patients,
            location_type,
            is_available,
            notes
        FROM kb_schedules
        ORDER BY schedule_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query).mappings().all()

    return [dict(row) for row in rows]


def search_schedules(engine: Engine, search_text: str) -> list[dict[str, Any]]:
    """
    Basic deterministic schedule search.
    """
    normalized_search = f"%{search_text.strip()}%"

    query = text(
        """
        SELECT
            schedule_id,
            day_type,
            day_name,
            modality,
            start_time,
            end_time,
            slot_duration_minutes,
            max_patients,
            location_type,
            is_available,
            notes
        FROM kb_schedules
        WHERE
            day_type ILIKE :search
            OR day_name ILIKE :search
            OR modality ILIKE :search
            OR location_type ILIKE :search
            OR is_available ILIKE :search
            OR notes ILIKE :search
        ORDER BY schedule_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query, {"search": normalized_search}).mappings().all()

    return [dict(row) for row in rows]
