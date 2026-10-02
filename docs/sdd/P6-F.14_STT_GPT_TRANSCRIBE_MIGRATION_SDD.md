# P6-F.14 — STT migration to GPT-Transcribe SDD

## 1. Status

**IMPLEMENTED LOCALLY / PRODUCTION VALIDATION PENDING**

Validation date: 2026-10-02.
Working branch: `feature/p6-f14-stt-gpt-transcribe`.

## 2. Objective and scope

Migrate completed WhatsApp voice-note transcription from `gpt-4o-transcribe`
to `gpt-transcribe`, preserving the existing deterministic inbound behavior.

No inbound redesign, TTS change, conversational-model migration, SDK upgrade,
database migration or batch-reactivation operation belongs to this phase.

## 3. Official compatibility decision

Official OpenAI documentation checked on 2026-10-02:

- https://developers.openai.com/api/docs/deprecations
- https://developers.openai.com/api/docs/guides/speech-to-text
- https://developers.openai.com/api/docs/models/gpt-transcribe

`gpt-4o-transcribe` is scheduled for API removal on 2027-02-26.
`gpt-transcribe` supports completed audio files through the existing
`client.audio.transcriptions.create()` endpoint.

For the new model, `languages` replaces singular `language`; both must not
be sent together. The integration supplies the plural field through
`extra_body` with the installed `openai==2.33.0` SDK.

The integration omits `response_format` for the new model and consumes the
documented default JSON response through `.text`. This decision does not
assert support for explicit `response_format="text"` on the new model.

## 4. Implementation contract

Files:
- `app/config.py`
- `app/services/speech_to_text.py`
- `tests/test_speech_to_text_service.py`

For `model == "gpt-transcribe"`:
- preserve `model`, audio `file` and `prompt=STT_CONTEXT_PROMPT`;
- send `extra_body={"languages": [settings.voice_stt_language]}`;
- omit `language`;
- omit `response_format`.

For other configured models, preserve the existing singular `language` and
`response_format="text"` arguments for transitional compatibility.
The former `gpt-4o-transcribe` path is covered by tests.

Preserve string and object `.text` response handling, whitespace trimming,
empty-transcript rejection, missing/empty-file rejection, provider-error
containment, latency reporting and owned-client cleanup.

The code default becomes `gpt-transcribe`; explicit environment settings
continue to take precedence. Conversation and TTS models remain unchanged.

## 5. Automated validation

RED:
- new-model request test failed because singular `language` was present;
- default-model test failed because the default was `gpt-4o-transcribe`.

GREEN:
- 12 STT test cases pass within the targeted regression;
- request arguments and object `.text` success are tested for both models;
- provider failures and empty transcripts are contained for both models;
- missing and empty files are rejected without a provider call;
- prompt preservation and the new default are asserted;
- voice/inbound regression passed;
- complete suite: **947 passed in 22.21s**.

Code and documentation diff reviewed; `git diff --check` passed.
Commit, push and PR are pending.
Mocked tests do not establish live provider or production compatibility.

## 6. Deployment and controlled validation

Production STT at phase opening: `gpt-4o-transcribe`.

After review and merge:
1. Deploy the validated code.
2. Set the production STT setting to `VOICE_STT_MODEL=gpt-transcribe`.
3. Confirm the effective setting without exposing credentials.
4. Check health/readiness.
5. Send one permitted operator-controlled WhatsApp voice note.
6. Confirm STT success with the new model, expected response and existing
   privacy-safe observability.
7. Record deployed commit and safe validation evidence before closure.

Do not change voice access flags, TTS, inbound routing or reactivation settings
as part of the migration.

## 7. Rollback and closure

If the controlled validation fails, restore the previous STT setting and
redeploy/restart as required by the existing deployment process.
The compatibility path allows the former model while it remains available,
before its scheduled removal on 2027-02-26.

Close P6-F.14 only after reviewed code, clean diff checks, deployment,
effective-model confirmation and controlled voice validation are recorded.
Production validation remains pending.
