# P6-F.9.95 — Voice Safety, Observability and Production Activation SDD

## Status

- Date: 2026-07-17
- Status: Closed — controlled production activation
- Branch: `feature/p6-f-9-92-voice-interaction`
- Production rollback tag: `pre-voice-production-2026-07-17`
- Global production voice activation: Not authorized

This document defines the controlled activation of Elvira voice without interrupting the existing production text service.

## Architecture

WhatsApp voice note  
→ authenticated media download  
→ safety validation and normalization  
→ OpenAI STT  
→ existing deterministic Elvira core  
→ OpenAI TTS  
→ WhatsApp voice note

Voice remains an input/output layer. It cannot modify routing, state-machine, appointment, persistence, or safety decisions.

Meta remains transport-only.

## Scope

Included:

- Atomic voice-processing lease
- Telephone allowlist
- Media size and duration limits
- Privacy-safe voice observability
- Disabled production deployment
- Controlled inbound activation
- Controlled outbound activation
- Operational rollback

Excluded:

- Multitenancy
- Patient follow-up
- Campaigns
- Realtime voice
- Calls or streaming
- Voice cloning
- New conversational logic
- Global voice activation

## Safety Invariants

1. Existing production text traffic must remain available.
2. Voice flags remain disabled by default.
3. An empty allowlist authorizes no telephone numbers.
4. Non-allowlisted audio is rejected before media download.
5. Deduplication occurs before STT and core execution.
6. Atomic leases prevent concurrent duplicate processing.
7. TTS receives the deterministic response and cannot rewrite it.
8. Voice delivery failure falls back to text without rerunning the core.
9. Raw audio, transcripts, and responses must not appear in voice logs.
10. State must not advance if both voice and text delivery fail.
11. Voice can be disabled without rolling back the text application.

## Verified Repository Baseline

Full suite:

`377 passed in 525.47s (0:08:45)`

Real local voice roundtrip:

- TTS model: `gpt-4o-mini-tts`
- Voice: `marin`
- Format: OGG/Opus
- STT model: `gpt-4o-transcribe`
- Language: Spanish
- Audio duration: 11.707 seconds
- STT latency: 2640 ms
- Human voice review: Approved

## Recovery Checkpoints

### Git

The production state before voice deployment is tagged:

`pre-voice-production-2026-07-17`

### PostgreSQL

A manual Easypanel backup completed successfully before deployment:

- Database: `elvira_respirarte_prod`
- Storage: Local Disk
- Path: `elvira/elvira_respirarte_prod/2026-07-17T14:28:31.086Z.sql.gz`
- Size: 41 kB
- Result: Success
- Retention: 7
- Schedule: `0 2 * * *`

Local Disk provides an operational rollback checkpoint. External storage remains recommended for disaster recovery.

## Easypanel Environment Contract

Before deploying the voice code:

```env
VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true
VOICE_STT_MODEL=gpt-4o-transcribe
VOICE_STT_LANGUAGE=es
VOICE_TTS_MODEL=gpt-4o-mini-tts
VOICE_TTS_VOICE=marin
VOICE_TTS_RESPONSE_FORMAT=opus
VOICE_MAX_MEDIA_BYTES=16777216
VOICE_MAX_DURATION_SECONDS=120
VOICE_PROCESSING_LEASE_SECONDS=300
VOICE_ALLOWED_PHONE_NUMBERS=
```

Only these are activation flags:

VOICE_INPUT_ENABLED
VOICE_REPLIES_ENABLED

VOICE_REPLY_TO_AUDIO_ONLY must remain true.

WHATSAPP_SENDING_ENABLED must retain its current production value so text delivery remains unchanged.

Database Migration

Migration:

scripts/sql/005_create_voice_processing_claims.sql

Execution:

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/sql/005_create_voice_processing_claims.sql

Verification:

SELECT to_regclass('public.voice_processing_claims');

Expected result:

voice_processing_claims

The migration is additive and must not modify existing production records.

Stage 0 — Deploy With Voice Disabled

Required values:

VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true
VOICE_ALLOWED_PHONE_NUMBERS=

Procedure:

Merge the voice branch into main.
Deploy the application in Easypanel.
Run migration 005_create_voice_processing_claims.sql.
Verify /health.
Verify /ready.
Send a normal production text message.
Confirm text response, persistence, and deduplication.
Confirm no voice processing occurs.

Stage 0 passes only if production text behavior remains unchanged.

Stage 1 — Inbound Voice With Text Reply

Authorize one controlled test telephone:

VOICE_ALLOWED_PHONE_NUMBERS=<authorized_test_number>
VOICE_INPUT_ENABLED=true
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true

Validation:

Send audio from the allowlisted number.
Confirm download, validation, normalization, and STT.
Confirm the transcript enters the deterministic core once.
Confirm Elvira replies by text.
Confirm the message is marked processed.
Replay the webhook and confirm no duplicate processing.
Send audio from a non-allowlisted number and confirm early rejection.
Confirm ordinary production text messages still work.

Stage 2 requires explicit approval after Stage 1 evidence.

Stage 2 — Controlled Voice Reply

Keep the single-number allowlist:

VOICE_INPUT_ENABLED=true
VOICE_REPLIES_ENABLED=true
VOICE_REPLY_TO_AUDIO_ONLY=true

Validation:

Send audio from the allowlisted number.
Confirm deterministic processing.
Confirm TTS preserves the deterministic response.
Confirm WhatsApp receives an OGG/Opus voice note.
Confirm the AI disclosure is present on the initial voice reply and is not repeated in subsequent stateful replies.
Confirm text input still receives text output.
Confirm voice failure falls back to text once.
Confirm no duplicate state transition.

This remains controlled activation, not global authorization.

Observability

Events must correlate by whatsapp_message_id and cover:

Allowlist decision
Lease claim or rejection
Media download and validation
Audio normalization
STT result and latency
Deterministic-core completion
TTS result and latency
Media upload
Voice delivery
Text fallback
Temporary-file cleanup
Final processed-message result

Logs must not contain:

Raw or encoded audio
Transcript text
Response text
Credentials
Temporary-file contents
Immediate Rollback

Set in Easypanel:

VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true
VOICE_ALLOWED_PHONE_NUMBERS=

Redeploy and verify:

/health is healthy.
/ready is healthy.
Normal text conversation succeeds.
No STT, TTS, or voice delivery occurs.

The additive voice_processing_claims table does not need removal.

Code Rollback

Use code rollback only if disabling voice flags does not restore stability.

Rollback reference:

pre-voice-production-2026-07-17

Database restoration is reserved for confirmed corruption and is not required merely to disable voice.

Stop Conditions

Stop activation and disable both voice flags if:

Text production is interrupted
Readiness becomes unhealthy
Duplicate STT or core execution occurs
A non-allowlisted sender reaches STT
Sensitive content appears in logs
State advances after total delivery failure
Media safety controls fail
Temporary files are not cleaned
Voice is sent in response to text
Unexpected database errors occur
Closure Evidence

P6-F.9.95 closes only after recording:

Production merge commit
Migration result
Health and readiness results
Text regression result
Controlled inbound result
Controlled outbound result
Duplicate-webhook result
Non-allowlisted sender result
Voice fallback result
Privacy-log review
Rollback validation
Final feature-flag state
Explicit global activation decision

After production validation:

Complete this evidence.
Update AI_CONTEXT.md.
Add the P6-F.9.95 closure to the voice architecture spec.
Update the production SDD with verified evidence.
Commit documentation closure separately.

Controlled production activation is complete. Global activation remains pending and unauthorized.

---

## Controlled Production Activation Closure — 2026-07-18

### Deployment Evidence

- Initial production voice merge: `f811406`
- Privacy correction commit: `687aa23`
- Production privacy-fix merge: `571b19e`
- Full regression suite: `377 passed in 525.06s`
- Easypanel deployment: Success
- PostgreSQL migration: `voice_processing_claims`
- `/health`: 200
- `/ready`: 200
- Existing production text conversation: Passed

### Recovery Evidence

- Git rollback tag: `pre-voice-production-2026-07-17`
- PostgreSQL backup: Success
- Database: `elvira_respirarte_prod`
- Backup path: `elvira/elvira_respirarte_prod/2026-07-17T14:28:31.086Z.sql.gz`
- Backup size: 41 kB
- Configuration rollback validated with both voice flags disabled, empty allowlist, and readiness 200
- Production text remained operational during rollback

### Controlled Voice Evidence

Inbound voice-to-text and outbound voice-to-voice passed on a real allowlisted WhatsApp number.

Final outbound validation:

- Intent: `fecha_cita`
- STT latency: 1548 ms
- TTS model: `gpt-4o-mini-tts`
- TTS voice: `marin`
- TTS latency: 2492 ms
- Output format: OGG/Opus
- Output size: 134362 bytes
- WhatsApp upload and delivery: Success
- Reply mode: `voice`
- Voice fallback used: False
- Legacy interaction log: `msg=None | resp=None`
- Deterministic appointment and holiday behavior: Preserved

A privacy stop condition was detected during the first controlled inbound validation because the legacy interaction logger exposed transcript and response content. Voice was immediately disabled, rollback was verified, the defect was corrected, and Stage 1 and Stage 2 were repeated successfully.

### Final Production State

```env
VOICE_INPUT_ENABLED=true
VOICE_REPLIES_ENABLED=true
VOICE_REPLY_TO_AUDIO_ONLY=true
VOICE_ALLOWED_PHONE_NUMBERS=<one controlled test number>
```

Controlled production voice is approved only for the single allowlisted number.

Global voice activation is not authorized.

Natural intonation and consistently clear pronunciation of “Elvira” remain future quality improvements and do not block controlled functional closure.

Duplicate-webhook, non-allowlisted sender, and delivery-fallback contracts remain covered by the passing automated regression suite rather than expanded production testing.
