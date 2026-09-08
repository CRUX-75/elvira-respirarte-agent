# P6-F.12 — Controlled Manual Reactivation Trigger and Inbound Response Correlation SDD

## 1. Status

**CLOSED / IMPLEMENTED / VALIDATED IN PRODUCTION**

Closure date: **2026-09-08**

Validated production application baseline at closure:

~~~text
validated_application_code=0a2a4066dec09403f5e2f6d0f47eb715833cefda
full_suite=926 passed in 19.00s
production=GREEN
~~~

P6-F.12 does not reopen P6-F.11.

---

## 2. Objective

Provide a deliberately constrained administrative path for preparing a small
reactivation operation from known prior-contact records while reusing the
existing P6-F.11 eligibility, persistence, lifecycle, delivery and response
contracts.

The phase also completes productive inbound-response correlation so that a
reply to a controlled reactivation contact can be associated with the
persisted campaign contact and classified without interrupting the normal
Elvira conversation.

This phase is not a prospecting engine.

---

## 3. Relationship to P6-F.11

P6-F.11 remains:

~~~text
CLOSED / IMPLEMENTED / VALIDATED IN PRODUCTION
~~~

P6-F.12 reuses existing P6-F.11 contracts for:

- reactivation campaign persistence;
- campaign-contact persistence;
- authorization and doctor-review gates;
- live PostgreSQL opt-out verification;
- idempotency;
- delivery claims;
- approved WhatsApp template delivery;
- provider lifecycle callbacks;
- inbound-response persistence;
- deterministic response policy.

P6-F.12 does not authorize another historical batch, mass messaging or cold
prospecting.

---

## 4. Manual trigger safety boundary

The manual trigger is constrained to:

- historical or otherwise known prior-contact records;
- explicit operator-selected `source_reference` values;
- between one and three selected records per controlled execution;
- unique and non-empty source references;
- preflight before persistence;
- successful evaluation of every selected row;
- `eligible` status for every selected contact;
- campaign-specific explicit confirmation;
- idempotent persistence;
- existing P6-F.11 lifecycle rules.

The trigger does not provide:

- automatic contact discovery;
- automatic eligible-contact selection;
- scheduler or cron execution;
- automatic campaign repetition;
- automatic follow-up;
- mass-send behavior;
- cold-prospect import;
- CRM lead scraping;
- WhatsApp transport from the trigger itself.

An `ACTIVE` campaign means lifecycle activation only.

It does not mean that a WhatsApp message was sent.

---

## 5. Manual preparation architecture

The implemented preparation boundary is:

~~~text
Reactivacion_Historica staging
→ dry-run dependency resolution
→ read-only preflight
→ explicit source_reference selection
→ every selected contact must be eligible
→ campaign-specific operator confirmation
→ persist DRAFT campaign
→ persist selected ELIGIBLE contacts
→ DRAFT -> READY -> ACTIVE
→ STOP
~~~

The manual trigger contains no WhatsApp dispatcher path.

Any real outbound template delivery remains a separate and explicitly
authorized operation through the existing P6-F.11 transport contracts.

---

## 6. Implementation components

Manual preparation service:

~~~text
app/services/reactivation_manual_trigger.py
~~~

Responsibilities include:

- conversion of an already evaluated eligible staging record into the
  persistent reactivation-contact contract;
- preflight aggregation;
- explicit-selection validation;
- controlled campaign/contact persistence;
- campaign lifecycle activation.

Administrative entrypoint:

~~~text
scripts/manual_reactivation_trigger.py
~~~

Administrative gates:

~~~text
REACTIVATION_MANUAL_TRIGGER_ENABLED
REACTIVATION_MANUAL_CAMPAIGN_ID
REACTIVATION_MANUAL_CAMPAIGN_NAME
REACTIVATION_MANUAL_SOURCE_REFERENCES
REACTIVATION_MANUAL_CONFIRM
REACTIVATION_MANUAL_DEFAULT_COUNTRY_CODE
~~~

The enable gate must be exactly:

~~~text
REACTIVATION_MANUAL_TRIGGER_ENABLED=1
~~~

Campaign confirmation is campaign-specific:

~~~text
CONFIRM:<campaign_id>
~~~

Without that exact confirmation, the entrypoint remains preview-only:

~~~text
PREVIEW_ONLY=True
writes_performed=False
whatsapp_send=False
~~~

Maximum selected contacts per controlled execution:

~~~text
3
~~~

---

## 7. Inbound response correlation

Productive wiring commit:

~~~text
f2dc83d45d7dd7476280eb9d0bd029b24b15b6c6
Wire reactivation inbound response correlation
~~~

The productive inbound sequence is:

~~~text
Meta inbound
→ payload extraction
→ text or completed voice transcription
→ best-effort reactivation response correlation
→ normal patient load/create
→ normal Elvira deterministic flow
~~~

Correlation uses:

~~~text
phone_e164
inbound_whatsapp_message_id
message or completed voice transcription
~~~

The response service:

1. finds the latest valid response candidate for the phone;
2. applies deterministic reactivation-response policy;
3. persists a response event;
4. persists contact-level response metadata;
5. returns safe correlation metadata.

Raw inbound response text is not persisted in the reactivation response event.

The productive webhook does not inject separate reactivation global-opt-out or
human-escalation writers because the normal webhook already owns those
patient-side effects.

---

## 8. Response classifications

The existing response taxonomy includes:

~~~text
global_opt_out
campaign_refusal
positive_contact_request
complaint
ambiguous
~~~

Production closure also validates:

~~~text
service_inquiry
~~~

`service_inquiry` represents a concrete question about a Respirarte service or
procedure after a correlated reactivation contact.

It does not by itself mean:

~~~text
global opt-out
campaign opt-out
human escalation
explicit human callback request
~~~

Existing precedence remains protective: opt-out, campaign refusal, complaint
and explicit positive contact request retain their established semantics.

---

## 9. Controlled production evidence

Controlled source reference:

~~~text
TEST-MANUAL-001
~~~

The controlled end-to-end path demonstrated:

~~~text
manual preparation
→ campaign active
→ separately authorized template delivery
→ provider accepted
→ sent
→ delivered
→ read
→ recipient inbound reply
→ response correlation
~~~

The same controlled flow also demonstrated voice handling:

~~~text
WhatsApp voice note
→ STT
→ reactivation correlation
→ normal Elvira conversation
~~~

Correlation evidence included:

~~~text
inbound_whatsapp_message_id_present=True
responded_at_present=True
REACTIVATION_RESPONSE_CORRELATED=True
~~~

No Marketing resend was required for the final validation.

---

## 10. Service-inquiry production validation

On 2026-09-08, a fresh controlled WhatsApp voice response asked whether
spirometry is also performed at home.

Normal Elvira service grounding produced:

~~~text
intent=servicios
kb_used=true
kb_sources=["kb_services"]
matched_service_id=SRV-03
matched_service_field=techniques
matched_service_term=espirometria
service_grounding_status=exact
next_action=answer_services
escalation_required=false
~~~

The final read-only reactivation persistence verification produced:

~~~text
source_reference=TEST-MANUAL-001
contact_status=read
contact_inbound_message_present=True
contact_response_classification=service_inquiry
contact_response_safe_reason=None
contact_requires_human_escalation=False
contact_responded_at_present=True

latest_event_inbound_message_present=True
latest_event_classification=service_inquiry
latest_event_safe_reason=None
latest_event_global_opt_out=False
latest_event_campaign_opt_out=False
latest_event_requires_human_escalation=False
latest_event_received_at_present=True

SERVICE_INQUIRY_PERSISTENCE_GREEN=True
~~~

The verification transaction was read-only.

No Marketing message was resent for this validation.

---

## 11. Database contract

P6-F.12 reuses the existing P6-F.11 persistence tables:

~~~text
reactivation_campaigns
reactivation_campaign_contacts
reactivation_campaign_response_events
~~~

Response classification fields are stored as `TEXT`.

Adding:

~~~text
service_inquiry
~~~

therefore required no PostgreSQL schema migration.

No fake CRM table, Demo-only database or parallel patient store was introduced.

---

## 12. Implementation commits

Manual-trigger implementation sequence:

~~~text
1d19a5f  Add manual reactivation contact preparation
54af219  Add manual reactivation preflight
ca92a2d  Require explicit manual reactivation selection
45c76b2  Add controlled manual reactivation persistence
8ec0cd6  Add manual reactivation campaign lifecycle
6b38532  Add manual reactivation trigger entrypoint
~~~

Productive inbound-response wiring:

~~~text
f2dc83d  Wire reactivation inbound response correlation
~~~

Final service-grounding and classification hardening:

~~~text
0a2a406  Fix service grounding and classify reactivation inquiries
~~~

---

## 13. Validation

Final automated baseline:

~~~text
926 passed in 19.00s
~~~

Static validation:

~~~text
python compilation: passed
git diff --check: passed
~~~

Post-deploy runtime verification confirmed:

~~~text
polite real spirometry case=exact
polite natural variant=exact
unsupported modifier after procedure=partial
unsupported modifier before procedure=partial
service inquiry classification=service_inquiry
requires_human_escalation=False
~~~

Real WhatsApp voice validation was GREEN.

The final read-only persistence verification was also GREEN.

---

## 14. Explicit exclusions

P6-F.12 does not implement or authorize:

- cold prospecting;
- automatic lead generation;
- automatic contact selection;
- automatic campaign scheduling;
- recurring reactivation jobs;
- background polling;
- automatic Marketing resend;
- mass outbound operations;
- automatic appointment confirmation;
- a separate Demo runtime;
- a fake CRM database;
- multitenancy.

P6-F.12 does not change P6-F.11 closure status.

---

## 15. Closure decision

P6-F.12 is:

~~~text
CLOSED / IMPLEMENTED / VALIDATED IN PRODUCTION
~~~

The system can prepare a deliberately small and explicitly selected
prior-contact reactivation operation, reuse the existing controlled delivery
infrastructure, and correlate a later text or voice response back to the
reactivation contact.

Validated commercial boundary:

~~~text
Elvira reactiva relaciones existentes.
No busca ni contacta prospectos fríos.
~~~

P6-F.11 remains closed.

Any future outbound operation requires new explicit operational authorization
and must preserve opt-out, eligibility, idempotency, lifecycle and privacy
contracts.
