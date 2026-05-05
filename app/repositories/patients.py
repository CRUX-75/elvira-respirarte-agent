from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db.session import engine


DEFAULT_PATIENT_STATE = "ST_INIT"


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row._mapping)


def get_or_create_patient_by_phone(
    telefono: str,
    nombre: str | None = None,
) -> dict[str, Any]:
    telefono = (telefono or "").strip()
    nombre = (nombre or "").strip() or None

    if not telefono:
        raise ValueError("telefono is required")

    with engine.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT *
                FROM patients
                WHERE telefono = :telefono
                LIMIT 1
                """
            ),
            {"telefono": telefono},
        ).fetchone()

        if existing:
            patient = _row_to_dict(existing)

            if nombre and not patient.get("nombre"):
                conn.execute(
                    text(
                        """
                        UPDATE patients
                        SET nombre = :nombre,
                            updated_at = NOW()
                        WHERE id = :patient_id
                        """
                    ),
                    {
                        "patient_id": patient["id"],
                        "nombre": nombre,
                    },
                )

                refreshed = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM patients
                        WHERE id = :patient_id
                        LIMIT 1
                        """
                    ),
                    {"patient_id": patient["id"]},
                ).fetchone()

                return _row_to_dict(refreshed)  # type: ignore[return-value]

            return patient  # type: ignore[return-value]

        created = conn.execute(
            text(
                """
                INSERT INTO patients (
                    telefono,
                    nombre,
                    estado_actual,
                    created_at,
                    updated_at,
                    last_message_at
                )
                VALUES (
                    :telefono,
                    :nombre,
                    :estado_actual,
                    NOW(),
                    NOW(),
                    NOW()
                )
                RETURNING *
                """
            ),
            {
                "telefono": telefono,
                "nombre": nombre,
                "estado_actual": DEFAULT_PATIENT_STATE,
            },
        ).fetchone()

        return _row_to_dict(created)  # type: ignore[return-value]


def update_patient_state(
    patient_id: str,
    nuevo_estado: str,
    opt_out: bool | None = None,
) -> None:
    if not patient_id:
        raise ValueError("patient_id is required")

    if not nuevo_estado:
        raise ValueError("nuevo_estado is required")

    opt_out_sql = ""
    params = {
        "patient_id": patient_id,
        "nuevo_estado": nuevo_estado,
    }

    if opt_out is not None:
        opt_out_sql = ",\n                    opt_out = :opt_out"
        params["opt_out"] = opt_out

    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE patients
                SET estado_actual = :nuevo_estado{opt_out_sql},
                    updated_at = NOW()
                WHERE id = :patient_id
                """
            ),
            params,
        )


def update_patient_last_message(patient_id: str) -> None:
    if not patient_id:
        raise ValueError("patient_id is required")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE patients
                SET last_message_at = NOW(),
                    updated_at = NOW()
                WHERE id = :patient_id
                """
            ),
            {"patient_id": patient_id},
        )
