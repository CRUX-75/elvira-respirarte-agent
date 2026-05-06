# P6-F-6 Controlled Real Sending Checklist

## Objective

Enable real WhatsApp sending only for a controlled internal test after dry-run validation has passed.

## Preconditions

- P6-F-5 dry-run approved.
- `/health` returns OK.
- `/ready` returns ready.
- `WHATSAPP_SENDING_ENABLED=false` before activation.
- WhatsApp configured: true.
- OpenAI configured: true.
- LangSmith project: elvira-respirarte-prod.
- Test participant is authorized.
- Test message is user-initiated.
- Rollback path is known.

## Activation rule

Real sending can be enabled only temporarily for the internal controlled test.

## Activation steps

1. Set `WHATSAPP_SENDING_ENABLED=true` in Easypanel.
2. Redeploy production service.
3. Validate `/ready`.
4. Send one user-initiated WhatsApp test message.
5. Confirm real WhatsApp reply is received.
6. Confirm DB interaction stores successful delivery status.
7. Confirm LangSmith trace is visible.
8. Disable `WHATSAPP_SENDING_ENABLED=false` again.
9. Redeploy.
10. Confirm `/ready` shows sending disabled.

## Test message

"Hola Elvira, que servicios ofrecen?"

## Expected result

- Elvira replies through WhatsApp.
- Intent is `servicios`.
- KB source includes `kb_services`.
- No urgency escalation.
- No opt-out.
- Conversation state remains controlled.
- DB stores the interaction.
- LangSmith trace is visible.

## Rollback

If anything unexpected happens:

- Set `WHATSAPP_SENDING_ENABLED=false`.
- Redeploy.
- Confirm `/ready`.
- Investigate by `whatsapp_message_id`.

