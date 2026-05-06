# P6-F WhatsApp Manager Readiness Checklist

## Objective

Prepare WhatsApp Manager readiness for controlled sending activation while continuing with the current test number until the official Colombian Respirarte number is available.

## Current operating decision

- Continue using the current test WhatsApp number for validation.
- Do not change Easypanel variables yet.
- Do not activate real sending yet.
- Keep `WHATSAPP_SENDING_ENABLED=false`.
- Prepare the system so the final Colombian number switch only requires replacing `WHATSAPP_PHONE_NUMBER_ID`, redeploying and validating.

## Current test number status

- Current test number active: pending
- Current `WHATSAPP_PHONE_NUMBER_ID` available in production env: pending
- WhatsApp configured in `/ready`: pending
- Sending currently disabled: pending
- Dry-run behavior validated with current test number: pending

## Colombian number readiness

To be completed later with Dra. D'Aleman:

- Colombian number added to Meta: pending
- Phone Number ID: pending
- Display name: pending
- Display name status: pending
- Number status: pending
- Messaging limits: pending
- Quality rating: pending
- Two-step verification: pending
- Access token change required: pending / unknown
- Webhook compatibility checked: pending

## Configuration decisions

- Icebreakers: disabled for now
- Commands: disabled for now
- Templates: required later, not blocking first controlled test if user writes first

## Notes

- The Colombian number may stop working as traditional WhatsApp once connected to WhatsApp Cloud API.
- Dra. D'Aleman must be available to receive the verification code in Colombia.
- Production env alignment for the Colombian number belongs to P6-F-4.
