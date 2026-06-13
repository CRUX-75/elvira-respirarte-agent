"""Manual controlled Google Sheets human review inbox dry-run.

This script validates the Google Sheets writer/factory path manually.

Safety boundaries:
- Does not connect to /webhook.
- Does not read or write PostgreSQL.
- Does not send WhatsApp messages.
- Does not contact patients.
- Does not read doctor actions.
- Does not trigger Telegram, n8n, Calendar, or campaigns.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adapters.google_sheets_human_review_writer_factory import (
    build_google_sheets_human_review_writer,
)
from app.config import Settings
from app.models.appointment_request import AppointmentRequest


def build_controlled_request() -> AppointmentRequest:
    now = datetime.now(timezone.utc).isoformat()

    return AppointmentRequest(
        id_solicitud="SOL-MANUAL-SHEETS-DRY-RUN-001",
        telefono="0000000000",
        nombre_paciente="Paciente Dry Run",
        estado_solicitud="pendiente_confirmacion",
        intent_origen="manual_google_sheets_dry_run",
        canal_origen="manual",
        fecha_solicitada="2026-06-17",
        franja_solicitada="3:00 p. m.–6:00 p. m.",
        hora_solicitada_texto="miércoles en la tarde",
        servicio_solicitado="Terapia Respiratoria",
        direccion_domicilio="Dirección ficticia dry-run",
        observaciones=(
            "P6-F.9.67 manual controlled Google Sheets dry-run. "
            "No patient. No webhook. No WhatsApp."
        ),
        source_interaction_id="manual-google-sheets-dry-run",
        created_by="manual_dry_run",
        updated_by="manual_dry_run",
        created_at=now,
        updated_at=now,
    )


def main() -> int:
    settings = Settings()
    writer = build_google_sheets_human_review_writer(settings=settings)

    if writer is None:
        print(
            "SKIPPED: Google Sheets writer is not configured. "
            "Required: GOOGLE_SHEETS_ENABLED=true, "
            "GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEETS_SPREADSHEET_ID."
        )
        return 0

    request = build_controlled_request()
    result = writer.upsert_request(request)

    print(f"Google Sheets manual dry-run result: {result}")
    print(f"id_solicitud: {request.id_solicitud}")
    print("Safety: no DB, no webhook, no WhatsApp, no real patient.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
