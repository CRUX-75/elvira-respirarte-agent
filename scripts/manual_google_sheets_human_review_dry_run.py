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


CONTROLLED_ID_SOLICITUD = "SOL-MANUAL-SHEETS-CONTRACT-P6-F-9-75"


def build_controlled_request(*, update: bool = False) -> AppointmentRequest:
    now = datetime.now(timezone.utc).isoformat()

    return AppointmentRequest(
        id_solicitud=CONTROLLED_ID_SOLICITUD,
        telefono="0000000000",
        nombre_paciente="Paciente Dry Run Contrato Expandido",
        estado_solicitud="pendiente_confirmacion",
        intent_origen="manual_google_sheets_contract_validation",
        canal_origen="manual",
        fecha_solicitada="2026-06-17",
        franja_solicitada="3:00 p. m.–6:00 p. m.",
        hora_solicitada_texto="miércoles en la tarde",
        servicio_solicitado="Terapia Respiratoria",
        tipo_cita="primera_vez" if not update else "control",
        eps="Compensar" if not update else "Sanitas",
        barrio="Suba" if not update else "Chapinero",
        edad_paciente=12 if not update else 13,
        notas_clinicas_breves=(
            "Dry-run inicial contrato expandido P6-F.9.75."
            if not update
            else "Dry-run actualizado contrato expandido P6-F.9.75."
        ),
        direccion_domicilio="Dirección ficticia dry-run",
        observaciones=(
            "P6-F.9.75 controlled Google Sheets contract validation. "
            "No patient. No webhook. No WhatsApp. No DB."
        ),
        source_interaction_id="manual-google-sheets-contract-validation-p6-f-9-75",
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

    initial_request = build_controlled_request(update=False)
    initial_result = writer.upsert_request(initial_request)

    updated_request = build_controlled_request(update=True)
    update_result = writer.upsert_request(updated_request)

    print("Google Sheets controlled contract validation result:")
    print(f"- initial upsert: {initial_result}")
    print(f"- second upsert: {update_result}")
    print(f"- id_solicitud: {CONTROLLED_ID_SOLICITUD}")
    print("")
    print("Expanded fields validated:")
    print(f"- tipo_cita: {updated_request.tipo_cita}")
    print(f"- eps: {updated_request.eps}")
    print(f"- barrio: {updated_request.barrio}")
    print(f"- edad_paciente: {updated_request.edad_paciente}")
    print(f"- notas_clinicas_breves: {updated_request.notas_clinicas_breves}")
    print("")
    print("Expected result:")
    print("- first run may append or update depending on whether the controlled row already exists")
    print("- second upsert should update the same row, not create a duplicate")
    print("")
    print("Safety: no DB, no webhook, no WhatsApp, no real patient.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
