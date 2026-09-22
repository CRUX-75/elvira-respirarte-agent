# P6-F.13 — Operational Batch Reactivation SDD

## 1. Status

**IMPLEMENTED LOCALLY / PRODUCTION EXECUTION PENDING**

P6-F.13 does not reopen P6-F.11 or P6-F.12.

---

## 2. Objective

Execute controlled patient reactivation operations in explicitly authorized
batches of no more than ten known historical contacts.

The phase reuses the existing eligibility, persistence, lifecycle, delivery,
callback, response-correlation, opt-out and idempotency contracts.

This phase is not a cold-prospecting system.

---

## 3. First operational batch

The first batch is fixed to:

~~~text
HIST-004
HIST-005
HIST-006
HIST-007
HIST-008
HIST-009
HIST-010
HIST-011
HIST-012
HIST-013
~~~

Records `HIST-014` and `HIST-015` remain outside this batch.

No automatic contact selection is allowed.

---

## 4. Operational sequence

~~~text
Reactivacion_Historica
→ read-only context resolution
→ existing eligibility evaluation
→ explicit selection of up to 10 source references
→ read-only batch preflight
→ safe aggregate summary
→ campaign-and-selection-bound authorization token
→ independent send authorization
→ existing idempotent campaign/contact persistence
→ existing DRAFT -> READY -> ACTIVE lifecycle
→ existing atomic per-contact delivery claim
→ existing best-effort dispatcher
→ Meta lifecycle callbacks
→ inbound response correlation
→ read-only metrics report
~~~

---

## 5. Preflight contract

The required preview summary is:

~~~text
requested
eligible
excluded
already_processed
estimated_sends
~~~

For the first real batch, authorization requires:

~~~text
requested=10
eligible=10
excluded=0
already_processed=0
estimated_sends=10
~~~

Preflight performs:

- no campaign persistence;
- no contact persistence;
- no campaign activation;
- no delivery claim;
- no Meta request;
- no WhatsApp send.

The previous value of `estado_reactivacion` in Sheets is not trusted as an
eligibility input. Eligibility is recalculated from source and human-reviewed
fields plus current database safety context.

---

## 6. Authorization

Authorization is bound to:

- the normalized campaign ID;
- the exact ordered tuple of `source_reference` values;
- a SHA-256-derived selection digest.

The required token format is:

~~~text
AUTHORIZE_BATCH:<campaign_id>:<selection_digest>
~~~

Changing the campaign or any selected source reference invalidates the token.

A real execution additionally requires:

~~~text
REACTIVATION_BATCH_SEND_AUTHORIZED=1
~~~

No write or send is permitted when either authorization gate is absent or
invalid.

---

## 7. Batch limit and failure isolation

Maximum batch size:

~~~text
10
~~~

The earlier real-pilot default remains:

~~~text
3
~~~

P6-F.13 passes the larger limit explicitly and does not weaken the P6-F.11
pilot boundary.

Each contact continues to use the existing atomic claim and idempotency
contract.

An unexpected failure for one contact:

- is recorded as a safe per-contact result;
- does not stop later contacts;
- does not resend contacts already accepted by Meta;
- does not remove the provider-message guard.

---

## 8. Implementation components

Batch service:

~~~text
app/services/reactivation_batch.py
~~~

Responsibilities:

- explicit selection of up to ten contacts;
- batch preflight summary;
- authorization-token generation and validation;
- reuse of existing persistence;
- persisted-contact authorization matching;
- reuse of the existing best-effort dispatcher.

Batch metrics:

~~~text
app/services/reactivation_batch_metrics.py
~~~

Responsibilities:

- delivered;
- read;
- replied;
- interested;
- appointment requests;
- opt-out;
- total cost;
- cost per delivered message;
- cost per reply;
- cost per positive response;
- cost per appointment request.

Administrative execution:

~~~text
scripts/manual_reactivation_batch.py
~~~

Read-only metrics report:

~~~text
scripts/manual_reactivation_batch_report.py
~~~

Read-only repository support:

~~~text
ReactivationCampaignContactRepository.list_by_campaign_id(...)
~~~

---

## 9. Execution gates

Preflight and execution variables:

~~~text
REACTIVATION_BATCH_ENABLED
REACTIVATION_BATCH_CAMPAIGN_ID
REACTIVATION_BATCH_CAMPAIGN_NAME
REACTIVATION_BATCH_SOURCE_REFERENCES
REACTIVATION_BATCH_DEFAULT_COUNTRY_CODE
REACTIVATION_BATCH_AUTHORIZATION
REACTIVATION_BATCH_SEND_AUTHORIZED
~~~

Without `REACTIVATION_BATCH_AUTHORIZATION`, the entrypoint prints:

~~~text
PREVIEW_ONLY=True
writes_performed=False
whatsapp_send=False
authorization_required=<token>
~~~

The preview command must be executed and reviewed before setting the
authorization and send gates.

---

## 10. Metrics and pricing

Pricing is never hardcoded in application code.

The report requires externally supplied current pricing data:

~~~text
REACTIVATION_BATCH_META_UNIT_COST
REACTIVATION_BATCH_META_CURRENCY
REACTIVATION_BATCH_META_PRICING_SOURCE
REACTIVATION_BATCH_META_PRICING_AS_OF
~~~

The pricing date must use `YYYY-MM-DD`.

Cost calculations use the supplied delivered-message unit cost and the
observed delivered population.

A read callback or correlated inbound response counts as delivery evidence
when an intermediate delivered callback was not persisted.

Positive response currently means:

~~~text
positive_contact_request
~~~

Appointment requests are supplied as explicit correlated contact IDs. They
are not inferred from general interest or service questions.

Opt-out includes:

~~~text
global_opt_out
campaign_refusal
contact status opted_out
~~~

---

## 11. Safety and privacy

Operational output contains aggregate counts and safe identifiers only.

It does not print:

- patient names;
- phone numbers;
- message bodies;
- provider payloads;
- database credentials;
- Meta credentials.

The batch remains limited to existing patient relationships.

~~~text
Elvira reactiva relaciones existentes.
No contacta prospectos fríos.
~~~

---

## 12. Production checklist

Before execution:

- [ ] Directed regression GREEN.
- [ ] Full suite GREEN.
- [ ] Python compilation GREEN.
- [ ] `git diff --check` clean.
- [ ] Branch reviewed and committed.
- [ ] Production deployment healthy.
- [ ] Read-only preview returns 10/10/0/0/10.
- [ ] Current Meta pricing source and date recorded.
- [ ] Authorization token copied from the reviewed preview.
- [ ] Independent send gate explicitly enabled.

After execution:

- [ ] Total result equals 10.
- [ ] Accepted, failed and ignored counts recorded.
- [ ] Each contact has at most one new attempt.
- [ ] Provider message IDs recorded only for accepted sends.
- [ ] No earlier accepted contact was resent.
- [ ] Delivery/read callbacks observed.
- [ ] Response and opt-out outcomes reviewed.
- [ ] Read-only metrics report executed.
- [ ] Campaign closed explicitly after the observation period.

---

## 13. Explicit exclusions

P6-F.13 does not implement:

- cold prospecting;
- automatic lead discovery;
- automatic batch selection;
- scheduling or recurring jobs;
- automatic Marketing resend;
- a parallel CRM;
- a parallel eligibility engine;
- diagnosis or autonomous clinical advice;
- automatic batch-size expansion.

Increasing the limit from 10 to 20 requires a separate decision based on
observed delivery, response, appointment and opt-out metrics.

---

## 14. Closure criteria

P6-F.13 may be marked closed only after:

1. the first ten-contact preview is reviewed;
2. the exact batch is explicitly authorized;
3. the real execution completes;
4. persisted delivery attempts are verified;
5. metrics are recorded;
6. the campaign is closed explicitly;
7. final documentation reflects production evidence.
