"""AppointmentRequest repository contract.

P6-F.9.12.3 — Repository Protocol Extraction.

This module defines the persistence contract for AppointmentRequest without
implementing PostgreSQL, Google Sheets, Telegram, Calendar, WhatsApp, or n8n.
"""

from __future__ import annotations

from typing import Protocol

from app.models.appointment_request import AppointmentRequest


ACTIVE_APPOINTMENT_REQUEST_STATES = {
    "nueva",
    "pendiente_datos",
    "pendiente_confirmacion",
    "confirmada",
    "reagendada",
}

TERMINAL_APPOINTMENT_REQUEST_STATES = {
    "cancelada",
    "cerrada",
}


class AppointmentRequestRepository(Protocol):
    """Persistence contract for AppointmentRequest repositories."""

    def save(self, request: AppointmentRequest) -> AppointmentRequest:
        """Persist a new AppointmentRequest."""

    def update(self, request: AppointmentRequest) -> AppointmentRequest:
        """Update an existing AppointmentRequest."""

    def get_by_id(self, id_solicitud: str) -> AppointmentRequest | None:
        """Return one AppointmentRequest by id_solicitud."""

    def find_active_by_telefono(self, telefono: str) -> AppointmentRequest | None:
        """Return the latest active AppointmentRequest for a phone number."""
