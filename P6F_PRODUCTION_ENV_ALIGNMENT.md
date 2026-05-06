# P6-F Production Environment Alignment

## Objective

Prepare the production environment alignment for the future Colombian WhatsApp number switch without changing Easypanel variables yet.

## Current rule

No Easypanel production variable should be changed until the Colombian `WHATSAPP_PHONE_NUMBER_ID` is confirmed.

`WHATSAPP_SENDING_ENABLED` must remain `false` during this step.

## Variables to verify before Colombian number switch

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_API_VERSION`
- `WHATSAPP_SENDING_ENABLED`
- `KB_RUNTIME_ENABLED`
- `LANGSMITH_PROJECT`
- `APP_ENV`
- `APP_VERSION`

## Future Colombian number switch

When the Colombian number is ready:

1. Replace only `WHATSAPP_PHONE_NUMBER_ID` with the Colombian Phone Number ID.
2. Review whether the existing `WHATSAPP_ACCESS_TOKEN` still has access to the new number.
3. Keep `WHATSAPP_SENDING_ENABLED=false`.
4. Redeploy.
5. Validate `/ready`.
6. Run dry-run tests before enabling real sending.

## Safety rule

Real sending must only be enabled in P6-F-6 after dry-run validation is successful.

