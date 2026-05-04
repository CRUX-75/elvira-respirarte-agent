from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.db.session import engine


BASE_DIR = Path(__file__).resolve().parents[1]
KB_DIR = BASE_DIR / "data" / "kb"

SERVICES_CSV = KB_DIR / "KB_Servicios.csv"
SCHEDULES_CSV = KB_DIR / "KB_Horarios.csv"
RULES_CSV = KB_DIR / "KB_Reglas.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader]


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default

    normalized = str(value).strip().lower()

    if normalized in {"true", "yes", "1", "si", "sí", "active", "activo"}:
        return True

    if normalized in {"false", "no", "0", "inactive", "inactivo"}:
        return False

    return default


def _clean(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if cleaned in {"", "-", "—", "null", "None", "none"}:
        return None

    return cleaned


def import_services() -> int:
    rows = _read_csv(SERVICES_CSV)

    query = text(
        """
        INSERT INTO kb_services (
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
            escalation_required,
            source,
            updated_at
        )
        VALUES (
            :service_id,
            :service_name,
            :category,
            :objective,
            :techniques,
            :patient_scope,
            :modality,
            :is_active,
            :public_answer_short,
            :public_answer_long,
            :escalation_required,
            'google_sheets_csv',
            NOW()
        )
        ON CONFLICT (service_id)
        DO UPDATE SET
            service_name = EXCLUDED.service_name,
            category = EXCLUDED.category,
            objective = EXCLUDED.objective,
            techniques = EXCLUDED.techniques,
            patient_scope = EXCLUDED.patient_scope,
            modality = EXCLUDED.modality,
            is_active = EXCLUDED.is_active,
            public_answer_short = EXCLUDED.public_answer_short,
            public_answer_long = EXCLUDED.public_answer_long,
            escalation_required = EXCLUDED.escalation_required,
            source = EXCLUDED.source,
            updated_at = NOW()
        """
    )

    imported = 0

    with engine.begin() as conn:
        for row in rows:
            service_id = _clean(row.get("service_id"))
            service_name = _clean(row.get("service_name"))

            if not service_id or not service_name:
                continue

            conn.execute(
                query,
                {
                    "service_id": service_id,
                    "service_name": service_name,
                    "category": _clean(row.get("category")),
                    "objective": _clean(row.get("objective")),
                    "techniques": _clean(row.get("techniques")),
                    "patient_scope": _clean(row.get("patient_scope")),
                    "modality": _clean(row.get("modality")),
                    "is_active": _to_bool(row.get("is_active"), default=True),
                    "public_answer_short": _clean(row.get("public_answer_short")),
                    "public_answer_long": _clean(row.get("public_answer_long")),
                    "escalation_required": _to_bool(
                        row.get("escalation_required"),
                        default=False,
                    ),
                },
            )
            imported += 1

    return imported


def import_schedules() -> int:
    rows = _read_csv(SCHEDULES_CSV)

    query = text(
        """
        INSERT INTO kb_schedules (
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
            notes,
            source,
            updated_at
        )
        VALUES (
            :schedule_id,
            :day_type,
            :day_name,
            :modality,
            :start_time,
            :end_time,
            :slot_duration_minutes,
            :max_patients,
            :location_type,
            :is_available,
            :notes,
            'google_sheets_csv',
            NOW()
        )
        ON CONFLICT (schedule_id)
        DO UPDATE SET
            day_type = EXCLUDED.day_type,
            day_name = EXCLUDED.day_name,
            modality = EXCLUDED.modality,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            slot_duration_minutes = EXCLUDED.slot_duration_minutes,
            max_patients = EXCLUDED.max_patients,
            location_type = EXCLUDED.location_type,
            is_available = EXCLUDED.is_available,
            notes = EXCLUDED.notes,
            source = EXCLUDED.source,
            updated_at = NOW()
        """
    )

    imported = 0

    with engine.begin() as conn:
        for row in rows:
            schedule_id = _clean(row.get("schedule_id"))
            day_type = _clean(row.get("day_type"))
            day_name = _clean(row.get("day_name"))

            if not schedule_id or not day_type or not day_name:
                continue

            conn.execute(
                query,
                {
                    "schedule_id": schedule_id,
                    "day_type": day_type,
                    "day_name": day_name,
                    "modality": _clean(row.get("modality")),
                    "start_time": _clean(row.get("start_time")),
                    "end_time": _clean(row.get("end_time")),
                    "slot_duration_minutes": _clean(row.get("slot_duration_minutes")),
                    "max_patients": _clean(row.get("max_patients")),
                    "location_type": _clean(row.get("location_type")),
                    "is_available": _clean(row.get("is_available")) or "true",
                    "notes": _clean(row.get("notes")),
                },
            )
            imported += 1

    return imported


def import_rules() -> int:
    rows = _read_csv(RULES_CSV)

    query = text(
        """
        INSERT INTO kb_rules (
            rule_id,
            rule_type,
            condition,
            response_rule,
            allowed_action,
            escalation,
            priority,
            is_active,
            source,
            updated_at
        )
        VALUES (
            :rule_id,
            :rule_type,
            :condition,
            :response_rule,
            :allowed_action,
            :escalation,
            :priority,
            :is_active,
            'google_sheets_csv',
            NOW()
        )
        ON CONFLICT (rule_id)
        DO UPDATE SET
            rule_type = EXCLUDED.rule_type,
            condition = EXCLUDED.condition,
            response_rule = EXCLUDED.response_rule,
            allowed_action = EXCLUDED.allowed_action,
            escalation = EXCLUDED.escalation,
            priority = EXCLUDED.priority,
            is_active = EXCLUDED.is_active,
            source = EXCLUDED.source,
            updated_at = NOW()
        """
    )

    imported = 0

    with engine.begin() as conn:
        for row in rows:
            rule_id = _clean(row.get("rule_id"))
            rule_type = _clean(row.get("rule_type"))
            condition = _clean(row.get("condition"))
            response_rule = _clean(row.get("response_rule"))

            if not rule_id or not rule_type or not condition or not response_rule:
                continue

            conn.execute(
                query,
                {
                    "rule_id": rule_id,
                    "rule_type": rule_type,
                    "condition": condition,
                    "response_rule": response_rule,
                    "allowed_action": _clean(row.get("allowed_action")),
                    "escalation": _to_bool(row.get("escalation"), default=False),
                    "priority": _clean(row.get("priority")) or "medium",
                    "is_active": _to_bool(row.get("is_active"), default=True),
                },
            )
            imported += 1

    return imported


def main() -> None:
    print("Importing Knowledge Base CSV files into PostgreSQL...")
    print(f"KB directory: {KB_DIR}")

    services_count = import_services()
    schedules_count = import_schedules()
    rules_count = import_rules()

    print("Knowledge Base import completed.")
    print(f"Services imported/updated: {services_count}")
    print(f"Schedules imported/updated: {schedules_count}")
    print(f"Rules imported/updated: {rules_count}")


if __name__ == "__main__":
    main()
