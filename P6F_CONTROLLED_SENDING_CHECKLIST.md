# P6-F-6 Controlled Real Sending Checklist

## Objective

Enable real WhatsApp sending only for a controlled internal test after dry-run validation has passed and the current appointment handoff layer is operationally complete.

## Preconditions

- P6-F-5 dry-run approved.
- P6-F.8 appointment request containment production validation approved.
- `/health` returns OK.
- `/ready` returns ready.
- `WHATSAPP_SENDING_ENABLED=false` before activation.
- WhatsApp configured: true.
- OpenAI configured: true.
- LangSmith project: elvira-respirarte-prod.
- Test participant is authorized.
- Test message is user-initiated.
- Rollback path is known.

## Current operational hold

Real WhatsApp sending remains intentionally blocked after P6-F.8.

Before activating controlled real sending, the next appointment handoff layer should be completed and validated:

- appointment request persistence
- `Solicitudes_Cita`
- human review handoff for Dra. D'Aleman

This avoids enabling real conversations before the appointment-request workflow is operationally complete.

## Activation rule

Real sending can be enabled only temporarily for the internal controlled test **after the current operational hold has been lifted**.

Until `Solicitudes_Cita` and the human review handoff are validated, keep:

```env
WHATSAPP_SENDING_ENABLED=false
Activation steps
Set WHATSAPP_SENDING_ENABLED=true in Easypanel.
Redeploy production service.
Validate /ready.
Send one user-initiated WhatsApp test message.
Confirm real WhatsApp reply is received.
Confirm DB interaction stores successful delivery status.
Confirm LangSmith trace is visible.
Disable WHATSAPP_SENDING_ENABLED=false again.
Redeploy.
Confirm /ready shows sending disabled.
Test message

"Hola Elvira, que servicios ofrecen?"

Expected result
Elvira replies through WhatsApp.
Intent is servicios.
KB source includes kb_services.
No urgency escalation.
No opt-out.
Conversation state remains controlled.
DB stores the interaction.
LangSmith trace is visible.
Rollback

If anything unexpected happens:

Set WHATSAPP_SENDING_ENABLED=false.
Redeploy.
Confirm /ready.
Investigate by whatsapp_message_id.
