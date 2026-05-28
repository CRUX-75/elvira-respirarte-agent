-- P6-F.9.14.15
-- Add appointment context carryover storage to patients.
-- This migration must be executed manually in production only after review.

ALTER TABLE patients
ADD COLUMN IF NOT EXISTS appointment_context JSONB;
