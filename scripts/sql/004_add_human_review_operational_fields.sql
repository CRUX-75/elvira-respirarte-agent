-- P6-F.9.73 — Human Review Inbox Operational Fields
-- Purpose:
-- Add doctor-requested operational fields to appointment_requests.
--
-- Important:
-- This migration must be reviewed before running in production.
-- Do not execute automatically from the application.

ALTER TABLE appointment_requests
ADD COLUMN IF NOT EXISTS tipo_cita TEXT;

ALTER TABLE appointment_requests
ADD COLUMN IF NOT EXISTS eps TEXT;

ALTER TABLE appointment_requests
ADD COLUMN IF NOT EXISTS barrio TEXT;

ALTER TABLE appointment_requests
ADD COLUMN IF NOT EXISTS edad_paciente INTEGER;

ALTER TABLE appointment_requests
ADD COLUMN IF NOT EXISTS notas_clinicas_breves TEXT;
