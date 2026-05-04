from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


def get_active_rules(engine: Engine) -> list[dict[str, Any]]:
    """
    Return all active KB rules.

    Rules inform response constraints.
    They do not replace the deterministic state machine.
    """
    query = text(
        """
        SELECT
            rule_id,
            rule_type,
            condition,
            response_rule,
            allowed_action,
            escalation,
            priority,
            is_active
        FROM kb_rules
        WHERE is_active = TRUE
        ORDER BY
            CASE LOWER(priority)
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            rule_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query).mappings().all()

    return [dict(row) for row in rows]


def get_rules_by_type(engine: Engine, rule_type: str) -> list[dict[str, Any]]:
    """
    Return active rules by rule_type.
    """
    query = text(
        """
        SELECT
            rule_id,
            rule_type,
            condition,
            response_rule,
            allowed_action,
            escalation,
            priority,
            is_active
        FROM kb_rules
        WHERE is_active = TRUE
        AND rule_type = :rule_type
        ORDER BY
            CASE LOWER(priority)
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            rule_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query, {"rule_type": rule_type}).mappings().all()

    return [dict(row) for row in rows]


def search_rules(engine: Engine, search_text: str) -> list[dict[str, Any]]:
    """
    Basic deterministic rule search.
    """
    normalized_search = f"%{search_text.strip()}%"

    query = text(
        """
        SELECT
            rule_id,
            rule_type,
            condition,
            response_rule,
            allowed_action,
            escalation,
            priority,
            is_active
        FROM kb_rules
        WHERE is_active = TRUE
        AND (
            rule_type ILIKE :search
            OR condition ILIKE :search
            OR response_rule ILIKE :search
            OR allowed_action ILIKE :search
            OR priority ILIKE :search
        )
        ORDER BY
            CASE LOWER(priority)
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            rule_id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query, {"search": normalized_search}).mappings().all()

    return [dict(row) for row in rows]
