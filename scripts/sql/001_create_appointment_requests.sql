-- P6-F.9.12.10 — Appointment Requests PostgreSQL Table
-- Purpose:
-- Create the appointment_requests table used by PostgresAppointmentRequestRepository.
--
-- Important:
-- This migration must be reviewed before running in production.
-- Do not execute automatically from the application.

CREATE TABLE IF NOT EXISTS appointment_requests (
    id_solicitud TEXT PRIMARY KEY,

    telefono TEXT NOT NULL,
    nombre_paciente TEXT,

    estado_solicitud TEXT NOT NULL CHECK (
        estado_solicitud IN (
            'nueva',
            'pendiente_datos',
            'pendiente_confirmacion',
            'confirmada',
            'reagendada',
            'cancelada',
            'cerrada'
        )
    ),

    intent_origen TEXT NOT NULL DEFAULT 'cita',
    canal_origen TEXT NOT NULL DEFAULT 'whatsapp' CHECK (
        canal_origen IN (
            'whatsapp',
            'manual',
            'system'
        )
    ),

    fecha_solicitada TEXT,
    franja_solicitada TEXT,
    hora_solicitada_texto TEXT,

    fecha_aceptada TEXT,
    franja_aceptada TEXT,

    fecha_confirmada TEXT,
    franja_confirmada TEXT,

    servicio_solicitado TEXT,
    direccion_domicilio TEXT,

    observaciones TEXT,
    motivo_reagendamiento TEXT,
    motivo_cancelacion TEXT,

    source_interaction_id TEXT,

    created_by TEXT NOT NULL DEFAULT 'system',
    updated_by TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointment_requests_telefono
ON appointment_requests (telefono);

CREATE INDEX IF NOT EXISTS idx_appointment_requests_active_lookup
ON appointment_requests (
    telefono,
    estado_solicitud,
    updated_at DESC,
    created_at DESC,
    id_solicitud DESC
);
