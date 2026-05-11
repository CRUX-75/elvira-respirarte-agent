# P6-F — Controlled Sending Activation Plan

## Status

Sprint: P6-F  
Phase: Pre-activation operational planning  
Current sending status: disabled  
Live WhatsApp sending must remain disabled until explicitly activated for one authorized test.

Current production readiness baseline:

- `/ready` status: ready
- environment: production
- WHATSAPP_SENDING_ENABLED=false
- KB_RUNTIME_ENABLED=true
- real_whatsapp_sending_allowed=false

## Non-negotiable Rules

- Do not activate `WHATSAPP_SENDING_ENABLED=true` yet.
- Do not connect or replace the Colombian Respirarte number yet.
- Do not connect Google Calendar real availability yet.
- Do not modify state machine logic, KB routing, or database schema unless a critical bug is found.
- All production validation must be done through browser, Swagger, EasyPanel logs, LangSmith, Meta dashboard, or local/VS Code terminal.
- Curl must not be assumed available inside EasyPanel Bash.

---

## P6-F Objective

Create a safe, reversible and auditable operational activation plan for WhatsApp real sending.

The activation must happen in a controlled way:

1. Validate WhatsApp Manager readiness.
2. Prepare Colombian Respirarte number checklist.
3. Define minimum required templates.
4. Validate EasyPanel environment variables.
5. Run final production dry-run with sending disabled.
6. Temporarily activate sending for one authorized test only.
7. Audit DB, LangSmith and Meta.
8. Roll back immediately to sending disabled.

---

## P6-F.1 — WhatsApp Manager Readiness Checklist

Before enabling real sending, validate in Meta WhatsApp Manager:

- Meta App is connected to the correct Business Manager.
- WhatsApp product is configured.
- Webhook callback URL points to production:
  - `https://elvira.genflowautomation.com/webhook`
- Webhook verify token is correctly configured.
- Required webhook fields are subscribed.
- Test number is still available for controlled testing.
- Production phone number migration has not been started yet.
- No ice breakers are configured for now.
- Templates section is accessible.
- Message templates can be created and submitted for approval.

Decision:

- Ice breakers remain disabled because Elvira is intended to behave as a controlled conversational assistant, not as a generic chatbot menu.

---

## P6-F.2 — Colombian Respirarte Number Checklist

The Colombian Respirarte number must not be connected yet.

Before migrating or adding the number, validate:

- The number is controlled by Dra. D'Aleman / Respirarte.
- The team has access to receive SMS or voice verification.
- The number is not actively registered in WhatsApp or WhatsApp Business App at migration time.
- The Business Manager is the correct one.
- The display name is ready for review.
- The production webhook is already stable.
- Rollback strategy is understood before replacing the test number.

Decision:

- Continue with the test number until the first controlled production sending test is completed successfully.
- The Colombian number migration belongs after the controlled sending test, not before.

---

## P6-F.3 — Minimum WhatsApp Templates

Minimum recommended templates before go-live:

### 1. Appointment Follow-up / Confirmation

Purpose:

- Follow up after a patient has requested an appointment.
- Confirm that the request was received.
- Avoid promising confirmed availability unless manually confirmed.

Suggested category:

- Utility

### 2. Appointment Reminder

Purpose:

- Remind the patient about an already confirmed appointment.
- Only after manual or future calendar-confirmed scheduling.

Suggested category:

- Utility

### 3. Administrative Recontact

Purpose:

- Recontact a patient when operationally necessary.
- Example: missing information, clarification, or follow-up.

Suggested category:

- Utility

### 4. Optional Service Information

Purpose:

- Send requested service information only when allowed by WhatsApp policy and patient context.

Suggested category:

- Utility or Marketing depending on final wording and use case.

Rules:

- No medical diagnosis.
- No urgency handling through templates.
- No confirmed availability unless confirmed by human or future calendar service.
- No aggressive promotional wording.
- No automated payment handling in Elvira.

---

## P6-F.5 — EasyPanel Environment Variables and /ready Validation

Before any controlled activation, validate these variables in EasyPanel:

- ENVIRONMENT=production
- WHATSAPP_SENDING_ENABLED=false
- KB_RUNTIME_ENABLED=true
- WHATSAPP_ACCESS_TOKEN configured
- WHATSAPP_PHONE_NUMBER_ID configured
- WHATSAPP_VERIFY_TOKEN configured
- OPENAI_API_KEY configured
- LANGSMITH_TRACING configured
- LANGSMITH_PROJECT configured
- DATABASE_URL configured

Expected `/ready` before activation:

- status=ready
- environment=production
- whatsapp_configured=true
- database_configured=true
- openai_configured=true
- langsmith_configured=true
- WHATSAPP_SENDING_ENABLED=false
- KB_RUNTIME_ENABLED=true
- real_whatsapp_sending_allowed=false

---

## P6-F.6 — Final Dry-run With Sending Disabled

Before activating real sending, run one final dry-run in production with sending disabled.

Validation method:

- Use browser or Swagger.
- Do not rely on curl inside EasyPanel Bash.

Test scenario:

- Patient in appointment flow.
- Message: "Mañana en la tarde"
- Expected behavior:
  - Elvira interprets the date using Colombia timezone.
  - Elvira does not claim confirmed availability.
  - Elvira does not say "disponemos de".
  - Elvira asks for the preferred hour or continues the appointment flow safely.
  - DB interaction is stored.
  - LangSmith trace is created.
  - WhatsApp real sending remains skipped.

Expected production state:

- WHATSAPP_SENDING_ENABLED=false
- real_whatsapp_sending_allowed=false
- no real WhatsApp message sent

---

## P6-F.7 — Documentation and Git Closure

Purpose:

Close the validated dry-run documentation state before preparing controlled real sending.

Status:

- P6-F.5 EasyPanel environment variables and `/ready` validation completed.
- P6-F.6 final production dry-run with `WHATSAPP_SENDING_ENABLED=false` completed.
- Production `/test/message-stateful` validated.
- Appointment flow validated:
  - `ST_INIT → ST_CITA_FECHA → ST_CITA_FRANJA → ST_CITA_PENDIENTE`
- Opt-out flow validated:
  - `ST_CITA_PENDIENTE → ST_OPTOUT`
- `delivery_status=sending_skipped` confirmed.
- Real WhatsApp sending remains disabled.
- No Colombian number migration has been executed.
- No Google Calendar integration has been activated.

Closure rule:

P6-F.7 is documentation and repository closure only.
It does not activate real WhatsApp sending.

---

## P6-F.8 — Controlled Real WhatsApp Sending Activation Checklist

This checklist is prepared but not executed yet. Real WhatsApp sending must not be activated until explicitly authorized during the controlled live test.

Activation window:

- One authorized test only.
- One known phone number only.
- One incoming WhatsApp message only.
- Immediate rollback after validation.

Activation steps:

1. Change EasyPanel variable:
   - WHATSAPP_SENDING_ENABLED=true

2. Redeploy production service.

3. Validate `/ready`:

Expected:

- status=ready
- WHATSAPP_SENDING_ENABLED=true
- real_whatsapp_sending_allowed=true

4. Send one test message from the authorized WhatsApp number.

5. Confirm:

- WhatsApp receives Elvira's response.
- DB stores interaction.
- processed_messages stores WhatsApp message ID.
- LangSmith trace is created.
- Meta dashboard shows message activity.

6. Immediately rollback:

- WHATSAPP_SENDING_ENABLED=false

7. Redeploy again.

8. Validate `/ready`:

Expected:

- WHATSAPP_SENDING_ENABLED=false
- real_whatsapp_sending_allowed=false

---

### P6-F.8.1 — Post-test Audit

After the single live test, audit:

### Database

Validate:

- patients table updated correctly.
- interactions table contains the message and response.
- processed_messages contains the WhatsApp message ID.
- opt_out remains false unless explicitly requested.
- state transition is correct.

### LangSmith

Validate:

- trace exists.
- intent is correct.
- estado_anterior and nuevo_estado are correct.
- kb_used value is expected.
- deterministic date context is present when relevant.
- no unsafe medical or availability claim appears.

### Meta / WhatsApp Manager

Validate:

- inbound message received.
- outbound message sent.
- no repeated or duplicate messages.
- no template issue caused unexpected behavior.
- no delivery error appears.

---

### P6-F.8.2 — Rollback Rule

Rollback must happen immediately after the single authorized live test.

Final expected production state:

- WHATSAPP_SENDING_ENABLED=false
- real_whatsapp_sending_allowed=false
- Production remains ready.
- No further real messages are sent automatically.

---

## P6-F Exit Criteria

P6-F can be considered complete when:

- WhatsApp Manager readiness checklist is documented.
- Colombian number migration checklist is documented.
- Minimum templates are defined.
- EasyPanel variables checklist is documented.
- Final dry-run with sending disabled is validated.
- Controlled one-message activation procedure is documented.
- Rollback procedure is documented.
- Audit procedure for DB, LangSmith and Meta is documented.

P6-F does not require leaving real sending enabled.


---

## P6-F.3 — WhatsApp Manager Readiness Verification

Manual verification completed in WhatsApp Manager.

Verified:

- WhatsApp Manager access confirmed.
- Message templates section accessible.
- Existing templates visible.
- Two templates currently active.
- German test phone number connected.
- German test phone number quality rating: high.
- Colombian Respirarte phone number is already listed in WhatsApp Manager.
- Colombian phone number status: not verified.

Pending:

- Colombian Respirarte number verification must be completed together with Dra. D'Aleman during a live call.
- Do not complete the Colombian number verification without direct coordination with Dra. D'Aleman.
- Do not replace the current connected test number before controlled sending validation is completed.

Decision:

- Continue P6-F using the currently connected German test number.
- Keep the Colombian number pending verification until the dedicated number activation step.


---

## Appendix A — Minimum WhatsApp Templates Review

Current WhatsApp Manager state:

- Two message templates are active.
- Existing templates include:
  - `flyer_servicios_respira`
  - `appointment_confirm...`

Decision for P6-F controlled sending:

- The first controlled live sending test must be user-initiated.
- No outbound template should be used during the first controlled activation.
- The authorized tester must send the first WhatsApp message to Elvira.
- Elvira should reply within the active 24-hour customer service window.
- Marketing templates must not be used for the first activation test.
- Appointment confirmation templates must not be used until the appointment confirmation workflow is explicitly implemented and validated.

Reason:

- P6-F validates real WhatsApp response sending, not outbound campaign/template behavior.
- Avoid mixing template approval, campaign delivery, and conversational safety in the same activation step.
- Keep the first live test reversible, minimal and auditable.

Template roadmap after P6-F:

- Review and adjust appointment confirmation template.
- Create or refine administrative follow-up template if needed.
- Create appointment reminder template only after the appointment workflow exists.
- Keep marketing templates separate from Elvira's medical/service conversation flow.
