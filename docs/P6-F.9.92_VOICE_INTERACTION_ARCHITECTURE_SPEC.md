P6-F.9.92_VOICE_INTERACTION_ARCHITECTURE_SPEC.md


# P6-F.9.92 — Voice Interaction Architecture Spec

**Project:** Elvira / Respirarte Agent  
**Status:** Proposed — ready for repository review  
**Date:** 2026-07-17  
**Working branch:** `feature/p6-f-9-92-voice-interaction`

---

## 1. Purpose

Define the inbound and outbound voice architecture for Elvira before any production implementation.

Elvira is active in production. Voice must be introduced as an isolated, reversible interface layer without interrupting or changing the current text workflow.

This specification authorizes architecture and later implementation work only. It does not activate voice in production.

---

## 2. Non-negotiable architecture rule

Voice is an input/output layer. It is not a new decision engine.

```txt
WhatsApp voice note
→ transport adapter
→ speech-to-text
→ existing deterministic Elvira core
→ existing text response
→ text-to-speech
→ transport adapter
→ WhatsApp voice note
```

The existing core remains authoritative for:

- intent classification;
- state transitions;
- appointment context;
- Colombian date resolution;
- weekends and holidays;
- candidate slots;
- AppointmentRequest persistence;
- duplicate active-request prevention;
- opt-out;
- escalation;
- human review;
- appointment-confirmation boundaries.

The transcription service converts speech into text. It does not infer business intent or modify dates, names, numbers, addresses, or appointment preferences.

The TTS service speaks the exact text response already produced by Elvira. It does not rewrite or reinterpret it.

---

## 3. Provider and transport boundary

Meta is used only as the unavoidable transport layer for the existing official WhatsApp channel.

Meta must not provide or own:

- speech recognition;
- speech generation;
- conversational intelligence;
- patient state;
- business rules;
- appointment decisions;
- voice configuration;
- voice observability;
- application persistence.

The interfaces must remain independently replaceable:

```txt
WhatsAppMediaGateway       → Meta transport only
SpeechToTextProvider       → OpenAI initially
ElviraCore                 → existing deterministic application
TextToSpeechProvider       → OpenAI initially
```

If Elvira later supports another channel, only the transport gateway should change. The speech providers and deterministic core must remain reusable.

No BSP such as Twilio is introduced. A BSP would not remove Meta and would add another operational dependency.

---

## 4. Current production baseline inspected

Repository state verified at the start of this phase:

```txt
main HEAD: b58bbcb
origin/main: b58bbcb
working tree: clean
voice branch: feature/p6-f-9-92-voice-interaction
latest documented test baseline: 325 passed
```

Current extension points:

| Responsibility | Current location | Current behavior |
|---|---|---|
| WhatsApp payload parser | `app/models/whatsapp.py` | Accepts `text` only |
| Real webhook | `app/main.py` | Requires `telefono` and `mensaje` before deduplication |
| Core entry | `IncomingMessage` + `traced_process_message(process_message, message)` | Processes text deterministically |
| Appointment runtime | `_apply_appointment_request_runtime()` | Runs after the deterministic core |
| Text send | `app/services/whatsapp.py` | Sends `type=text` only |
| Read/typing UX | `app/services/whatsapp.py` | Sends text typing indicator |
| Configuration | `app/config.py` | No voice settings yet |
| Container | `Dockerfile` | `python:3.12-slim`; no `ffmpeg` |
| SDKs | `requirements.txt` | `openai==2.33.0`, `httpx==0.28.1` |

The current text parser contract and all text-message behavior must remain unchanged.

---

## 5. Scope

### In scope

- inbound WhatsApp voice notes;
- Meta media URL retrieval and authenticated download;
- temporary local media handling;
- audio validation and format normalization;
- Spanish speech-to-text;
- conversion into the current `mensaje` contract;
- processing through the existing deterministic core;
- text-to-speech for Elvira's existing response;
- upload and send as a WhatsApp voice note;
- deterministic fallback to text;
- feature flags;
- tests, logs, metrics, cleanup, and controlled rollout.

### Out of scope

- WhatsApp calls;
- Realtime API;
- live or streaming speech-to-speech;
- cloned voice of Dra. D'Aleman or any real person;
- automatic patient follow-up;
- outbound campaigns;
- multitenancy;
- new appointment logic;
- changes to existing text behavior;
- replacing PostgreSQL, LangGraph, LangSmith, or Google Sheets;
- introducing Celery, Redis, n8n, or another workflow engine for voice.

---

## 6. Accepted inbound message types

Initial production support is intentionally narrow.

| WhatsApp type | Subtype | Initial behavior |
|---|---|---|
| `text` | Non-empty body | Existing behavior, unchanged |
| `audio` | `audio.voice=true`, OGG/Opus | Accepted only when `VOICE_INPUT_ENABLED=true` |
| `audio` | Uploaded/basic audio, `voice=false` or missing | Unsupported in the initial release |
| Status notification | No `messages` array | Ignored, unchanged |
| Image, video, document, sticker, location, contact | Any | Ignored, unchanged |

The initial feature supports voice notes recorded in WhatsApp. It does not treat arbitrary audio attachments, music, recordings, or calls as patient messages.

---

## 7. Parser contract

The parser performs structural extraction only. It must not download media, call OpenAI, transcribe audio, or invoke business logic.

### 7.1 Common fields

```txt
telefono
nombre
msg_type
whatsapp_message_id
whatsapp_timestamp
```

### 7.2 Text fields

```txt
mensaje
```

The current text dictionary must remain byte-for-byte compatible at the contract level.

### 7.3 Audio fields

```txt
mensaje=None
media_id
mime_type
sha256
voice
```

Expected normalized parser result:

```python
{
    "telefono": "57300...",
    "mensaje": None,
    "nombre": "Paciente",
    "msg_type": "audio",
    "whatsapp_message_id": "wamid...",
    "whatsapp_timestamp": "...",
    "media_id": "...",
    "mime_type": "audio/ogg; codecs=opus",
    "sha256": "...",
    "voice": True,
}
```

Malformed audio without `telefono`, `whatsapp_message_id`, `media_id`, or a supported voice-note subtype must not enter STT or the deterministic core.

Feature-flag policy belongs in the webhook/application layer, not in the structural parser.

---

## 8. Normalized patient-message contract

After successful transcription, the interface layer must produce the same semantic input the current core already understands:

```python
IncomingMessage(
    telefono=telefono,
    mensaje=transcript,
    nombre=nombre,
    estado_actual=estado_actual,
    opt_out=opt_out,
)
```

The transcript becomes `mensaje`. No separate voice-specific state machine is allowed.

Voice metadata remains outside `IncomingMessage` and is used only for transport, observability, auditing, and cleanup.

The transcript must not be rewritten by another LLM before entering `process_message()`.

---

## 9. Inbound workflow

```txt
1. Parse common WhatsApp metadata
2. Validate message type and required transport fields
3. Check deduplication using whatsapp_message_id
4. If duplicate, ignore before media download or STT
5. If audio and VOICE_INPUT_ENABLED=false, ignore with explicit reason
6. Mark inbound message read and show typing when sending is enabled
7. Retrieve temporary media URL through WhatsAppMediaGateway
8. Download media with bearer authorization
9. Validate MIME type, byte limit, checksum, and duration
10. Normalize the container into an OpenAI-supported STT input
11. Transcribe in Spanish through SpeechToTextProvider
12. Reject an empty or unusable transcript
13. Build the existing IncomingMessage
14. Execute traced_process_message(process_message, message)
15. Execute existing AppointmentRequest runtime
16. Apply outbound reply policy
17. Persist interaction and state using existing semantics
18. Mark whatsapp_message_id as processed
19. Remove all temporary local files in finally
```

Deduplication must happen before paid or expensive media/STT work.

The current rule remains: if final delivery fails, patient state must not advance and the message must not be marked processed.

Before production activation, P6-F.9.95 must evaluate an atomic processing claim/lease because audio processing is slower than text and concurrent webhook retries could otherwise duplicate external work.

---

## 10. WhatsApp media gateway

`WhatsAppMediaGateway` is a dedicated transport adapter. It must not contain STT, TTS, state-machine, or appointment logic.

### Required operations

```python
async def retrieve_media_metadata(media_id: str) -> MediaMetadata: ...
async def download_media(media_url: str) -> DownloadedMedia: ...
async def upload_audio(file_path: Path, mime_type: str) -> str: ...
async def send_voice_note(telefono: str, media_id: str) -> dict: ...
```

### Inbound download

1. Request media metadata/URL using the inbound `media_id`.
2. Download the binary immediately using bearer authorization.
3. Never log the temporary URL or access token.
4. If the URL expires or returns 404, retrieve a fresh URL and retry once.
5. Do not persist the URL.

### Outbound upload and send

1. Upload the validated OGG/Opus file to `/{Phone-Number-ID}/media`.
2. Capture the returned media ID.
3. Send through `/{Phone-Number-ID}/messages` with:

```json
{
  "messaging_product": "whatsapp",
  "to": "<telefono>",
  "type": "audio",
  "audio": {
    "id": "<media_id>",
    "voice": true
  }
}
```

No public media hosting or permanent audio URL is introduced.

The existing `send_whatsapp_message()` remains the text sender. Voice transport uses explicit, separately tested functions.

---

## 11. Temporary file and audio-normalization policy

### Current container finding

The current `python:3.12-slim` image does not install `ffmpeg`.

P6-F.9.93 must add `ffmpeg`/`ffprobe` to the Docker image using a minimal package-install layer and remove apt metadata afterward.

### Local handling

- Use `tempfile.TemporaryDirectory()` or an equivalent randomized directory under `/tmp`.
- Create files with restrictive permissions.
- Never use patient phone numbers or names in filenames.
- Never persist raw audio in PostgreSQL, Google Sheets, repository files, or LangSmith.
- Delete inbound, normalized, and generated outbound audio in a `finally` block.
- Cleanup failure is logged but must not replace the primary processing outcome.

### Inbound format normalization

WhatsApp voice notes are expected as OGG/Opus. OpenAI file transcription does not accept OGG directly.

Preferred path:

```txt
OGG/Opus
→ validate with ffprobe
→ remux without re-encoding to WebM/Opus when possible
→ gpt-4o-transcribe
```

Fallback path when remuxing is incompatible:

```txt
OGG/Opus
→ controlled ffmpeg conversion to MP3
→ gpt-4o-transcribe
```

No transcoding command may interpolate untrusted filenames into a shell string. Use argument arrays with `subprocess.run(..., shell=False)` and explicit timeouts.

### Initial safety limits

```txt
maximum inbound bytes: 16 MiB
maximum voice-note duration: 120 seconds
maximum OpenAI upload: 25 MB provider limit
```

Oversized or overlong audio does not enter STT. Elvira sends a deterministic text request asking the patient to resend a shorter note or write the message.

---

## 12. Speech-to-text decision

### Provider

OpenAI through the already configured `OPENAI_API_KEY` and installed OpenAI SDK.

### Default model

```env
VOICE_STT_MODEL=gpt-4o-transcribe
VOICE_STT_LANGUAGE=es
```

`gpt-4o-transcribe` is selected over the mini model for the initial healthcare-adjacent rollout because transcription accuracy is more important than marginal cost reduction. Patient names, dates, hours, neighborhoods, EPS names, and respiratory-service terms must be preserved as accurately as possible.

The model remains configurable so a later evaluation can compare `gpt-4o-mini-transcribe` without changing application code.

### Request policy

```txt
endpoint: audio.transcriptions
response_format: text
language: es
streaming: false
```

Use a short static context prompt containing only domain vocabulary, for example:

```txt
Conversación en español colombiano sobre Respirarte, terapia respiratoria
domiciliaria, Dra. D'Aleman, Bogotá, Sabana de Occidente, EPS,
traqueostomía, rehabilitación pulmonar y solicitud de citas.
Conserve literalmente nombres, fechas, horas, números y direcciones.
```

The prompt must not include patient-specific data from previous turns.

### STT output validation

- Trim surrounding whitespace.
- Reject an empty result.
- Do not autocorrect dates, numbers, names, or addresses with another LLM.
- Pass the raw usable transcript into the current sanitization and deterministic pipeline.
- A transcription error never falls through into the core as an empty message.

---

## 13. Outbound voice decision

### Provider and model

```env
VOICE_TTS_MODEL=gpt-4o-mini-tts
VOICE_TTS_VOICE=marin
VOICE_TTS_RESPONSE_FORMAT=opus
```

`marin` is the provisional default for the first controlled evaluation. The definitive voice is selected in P6-F.9.94 after listening tests in Colombian Spanish. No voice cloning is permitted.

### TTS instructions

```txt
Hable en español colombiano claro y natural, con tono cálido, profesional
y tranquilo. Use ritmo moderado, pronunciación precisa y sin exagerar el
acento. No agregue, elimine ni reformule contenido.
```

The TTS input is exactly `result.respuesta` plus any required, approved AI-voice disclosure. TTS must not generate new conversational content.

### Output validation

1. Request Opus output.
2. Validate codec and container using `ffprobe`.
3. Remux to `.ogg` with Opus when necessary.
4. Reject invalid, empty, or oversized output.
5. Upload using the WhatsApp media gateway.
6. Send with `audio.voice=true`.

### AI-generated voice disclosure

End users must receive a clear disclosure that the voice is AI-generated and not a human recording.

During the initial rollout, every generated voice reply begins with a short disclosure:

```txt
Soy Elvira, la asistente virtual de Respirarte.
```

This keeps Elvira natural and human-friendly without impersonating Dra. D'Aleman or another real person. A later persisted one-time disclosure may be evaluated, but disclosure cannot be silently removed.

---

## 14. Voice reply policy

Initial flags:

```env
VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true
```

Decision table:

| Input | Voice input | Voice replies | Reply-to-audio-only | Output |
|---|---:|---:|---:|---|
| Text | Any | Any | `true` | Existing text reply |
| Audio | `false` | Any | Any | Ignore with `voice_input_disabled`; no external voice work |
| Audio | `true` | `false` | Any | Transcribe, run core, send text reply |
| Audio | `true` | `true` | `true` | Transcribe, run core, send voice reply |
| Audio | `true` | `true` | `false` | Voice reply allowed; not activated initially |

With all voice flags false, production text behavior remains unchanged.

`WHATSAPP_SENDING_ENABLED` remains the master external-send switch. Voice flags must never bypass it.

Emergency voice rollback:

```env
VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
```

Broader transport rollback remains:

```env
WHATSAPP_SENDING_ENABLED=false
```

---

## 15. Deterministic fallback policy

### Inbound failure before the core

If media retrieval, validation, conversion, or STT fails:

- do not call `process_message()`;
- do not advance patient state;
- do not create an AppointmentRequest;
- send a fixed text response when external sending is enabled;
- mark the inbound message processed only after the fallback text is sent successfully.

Suggested fallback:

```txt
No pude procesar correctamente su nota de voz. Por favor envíeme una nota
más corta o escríbame el mensaje para poder ayudarle.
```

### Outbound TTS or voice-delivery failure

If the deterministic core succeeded but TTS, validation, upload, or voice sending fails:

1. Send the already generated `result.respuesta` as text.
2. If text fallback succeeds, treat delivery as successful and continue current persistence/state semantics.
3. If both voice and text delivery fail, preserve the current `send_failed` behavior: no state update and no processed mark.

Text fallback must not call the core a second time.

No fallback may invent a new appointment answer.

---

## 16. Configuration contract

All voice settings default to safe/off values.

```env
# Voice feature flags
VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true

# Speech-to-text
VOICE_STT_MODEL=gpt-4o-transcribe
VOICE_STT_LANGUAGE=es

# Text-to-speech
VOICE_TTS_MODEL=gpt-4o-mini-tts
VOICE_TTS_VOICE=marin
VOICE_TTS_RESPONSE_FORMAT=opus

# Safety limits
VOICE_MAX_MEDIA_BYTES=16777216
VOICE_MAX_DURATION_SECONDS=120

# Optional controlled rollout
VOICE_ALLOWED_PHONE_NUMBERS=
```

`VOICE_ALLOWED_PHONE_NUMBERS`, when non-empty, restricts voice processing to explicitly listed test numbers. It must not contain real values in `.env.example` or Git.

Existing settings remain authoritative:

```env
WHATSAPP_SENDING_ENABLED=true|false
WHATSAPP_API_URL=https://graph.facebook.com/v25.0
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_TOKEN=...
OPENAI_API_KEY=...
```

P6-F.9.93 must update `.env.example` comprehensively without adding secrets.

---

## 17. Failure semantics and retry policy

| Operation | Retry policy | Duplicate risk |
|---|---|---|
| Retrieve media URL | One retry on transient failure | None |
| Download media | Refresh URL and retry once on expiry/404 | None |
| Audio validation/conversion | No blind retry | None |
| STT | At most one retry for explicit transient provider errors | Additional cost only |
| TTS | At most one retry for explicit transient provider errors | Additional cost only |
| Media upload | One retry if the response proves no media ID was created | Orphaned media possible |
| Final WhatsApp send | No blind retry without idempotency evidence | Duplicate patient reply |

All HTTP clients require explicit connect/read/write timeouts. Provider failures must be classified without logging secrets or audio content.

---

## 18. Persistence and privacy

- PostgreSQL remains the operational source of truth.
- Raw audio is never stored in PostgreSQL.
- Raw or generated audio is never placed in Google Sheets.
- Temporary audio files are deleted after each request.
- The transcript is stored as `mensaje_usuario`, consistent with current text-message persistence.
- Store `msg_type=audio` and voice observability metadata only where required by the implementation plan.
- Do not log bearer tokens, temporary media URLs, audio bytes, or local temporary paths.
- Prefer transcript length/hash over raw transcript content in new structured voice logs.
- Existing LangSmith tracing may receive the normalized transcript through the current core, but never raw audio.
- Medical diagnosis remains outside Elvira's scope regardless of input modality.

---

## 19. Observability contract

Voice events must include correlation through `whatsapp_message_id`.

Required fields where applicable:

```txt
event
telefono_masked
whatsapp_message_id
whatsapp_timestamp
msg_type
voice
media_id_hash
mime_type
media_bytes
audio_duration_seconds
media_download_ms
audio_normalization_ms
stt_provider
stt_model
stt_latency_ms
transcript_length
core_latency_ms
tts_provider
tts_model
tts_voice
tts_latency_ms
outbound_media_bytes
reply_mode=text|voice
voice_fallback_used
fallback_reason
delivery_status
processed_marked
state_updated
temporary_cleanup_status
```

Stage events:

```txt
voice_input_received
voice_input_disabled
voice_media_downloaded
voice_media_rejected
voice_audio_normalized
voice_stt_succeeded
voice_stt_failed
voice_core_succeeded
voice_tts_succeeded
voice_tts_failed
voice_media_uploaded
voice_reply_sent
voice_text_fallback_sent
voice_processing_failed
voice_cleanup_completed
```

Current canonical delivery semantics should remain compatible. Add `reply_mode` and `voice_fallback_used` rather than replacing every existing `delivery_status` value.

---

## 20. Test plan

### P6-F.9.93 — inbound parser and STT

- Existing text parser result remains unchanged.
- Status notifications remain ignored.
- Unsupported message types remain ignored.
- Valid `audio.voice=true` payload returns the complete media contract.
- Missing `media_id`, phone, WAMID, or invalid audio data is rejected.
- Voice flag off causes no media or OpenAI calls.
- Deduplication occurs before media download and STT.
- Media URL retrieval and authenticated download are mocked and verified.
- Expired URL refreshes once.
- Size, MIME, checksum, and duration limits are enforced.
- OGG/Opus normalization produces a supported STT input.
- Spanish transcript becomes the existing `IncomingMessage.mensaje`.
- Empty transcript never enters the core.
- STT failure produces deterministic text fallback and no state transition.
- Temporary files are removed on success and every failure path.

### P6-F.9.94 — TTS and outbound voice

- Text input continues producing text only with default policy.
- Audio input produces voice only when both voice flags allow it.
- TTS receives the exact deterministic response plus disclosure.
- TTS output is validated as OGG/Opus before upload.
- Media upload returns an ID used with `audio.voice=true`.
- TTS failure falls back to the original text response.
- Upload failure falls back to text.
- Voice send failure falls back to text without re-running the core.
- If voice and text both fail, state and processed-message semantics remain unchanged.
- `WHATSAPP_SENDING_ENABLED=false` causes no external send.

### P6-F.9.95 — safety and production

- Allowlist rollout works.
- Atomic claim/lease or equivalent concurrency protection is validated.
- Duplicate WAMID does not repeat STT, TTS, persistence, or sending.
- Logs contain required fields and no secrets/audio bytes.
- Latency and fallback metrics are visible.
- Voice rollback flags work without redeployment.
- Full regression suite remains green.
- Controlled real-device tests validate WhatsApp rendering as a voice note.

No unit test may require real Meta or OpenAI network calls.

---

## 21. Controlled production rollout

### Stage 0 — architecture only

- Merge only the accepted spec.
- No runtime code or production configuration changes.

### Stage 1 — dark implementation

```env
VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true
```

- Deploy only after the full suite is green.
- Verify text production behavior is unchanged.

### Stage 2 — inbound allowlist

```env
VOICE_INPUT_ENABLED=true
VOICE_REPLIES_ENABLED=false
VOICE_ALLOWED_PHONE_NUMBERS=<internal-test-number>
```

- Validate real media download, Spanish transcription, deterministic routing, persistence, cleanup, and text fallback.

### Stage 3 — outbound allowlist

```env
VOICE_INPUT_ENABLED=true
VOICE_REPLIES_ENABLED=true
VOICE_REPLY_TO_AUDIO_ONLY=true
VOICE_ALLOWED_PHONE_NUMBERS=<internal-test-number>
```

- Validate voice quality, OGG/Opus format, WhatsApp voice-note rendering, disclosure, latency, and fallback.

### Stage 4 — limited patient activation

- Expand gradually after logs and LangSmith traces are reviewed.
- Keep text fallback active.
- Keep both emergency voice flags available without deployment.

### Stage 5 — general activation

- Remove the rollout allowlist only after acceptance criteria remain green.
- Text conversations continue to receive text replies.

Elvira remains online throughout every stage.

---

## 22. Planned implementation boundaries

### P6-F.9.93 — Inbound Voice Notes

Expected components:

```txt
app/models/whatsapp.py                 parser extension
app/services/whatsapp_media.py         Meta transport adapter
app/services/audio_normalization.py    validation and ffmpeg boundary
app/services/speech_to_text.py         provider interface + OpenAI adapter
app/config.py                          safe voice configuration
app/main.py                            guarded audio orchestration
Dockerfile                             ffmpeg/ffprobe
.env.example                           documented non-secret settings
tests/...                              parser, services, webhook, cleanup
```

### P6-F.9.94 — Outbound Voice Replies

Expected components:

```txt
app/services/text_to_speech.py         provider interface + OpenAI adapter
app/services/whatsapp_media.py         upload + voice-note send
app/main.py                            reply policy and text fallback
tests/...                              TTS, upload, send, fallback semantics
```

### P6-F.9.95 — Safety, observability and activation

Expected work:

```txt
atomic processing protection
structured voice events
latency and fallback measurements
allowlist rollout
controlled real-device verification
rollback verification
production activation decision
```

Exact filenames may be refined during implementation, but responsibilities must not be collapsed into `app/main.py` or the parser.

---

## 23. Acceptance criteria for P6-F.9.92

P6-F.9.92 is closed when:

- the architecture spec is reviewed and accepted;
- Meta is explicitly limited to WhatsApp transport;
- STT and TTS provider decisions are documented;
- parser and normalized-message contracts are explicit;
- audio conversion and temporary-file handling are defined;
- feature flags default to off;
- text behavior is guaranteed unchanged while flags are off;
- fallbacks, privacy, observability, tests, and rollout are defined;
- no production runtime code has changed;
- the full existing test suite remains green;
- the working tree is clean after the documentation commit.

---

## 24. Official references

- OpenAI Speech to text: <https://developers.openai.com/api/docs/guides/speech-to-text>
- OpenAI Text to speech: <https://developers.openai.com/api/docs/guides/text-to-speech>
- Meta WhatsApp Cloud API media: <https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/media>
- Meta official WhatsApp Cloud API Postman collection: <https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api>
- Meta voice-message request example: <https://www.postman.com/meta/whatsapp-business-platform/request/y0evt6u/send-reply-to-audio-message-by-url>

---

## Final architecture decision

```txt
Elvira remains online in production.
Voice is developed in an isolated branch.
Voice flags default to off.
Meta transports WhatsApp media only.
OpenAI performs STT and TTS.
The deterministic Elvira core remains unchanged and authoritative.
Text fallback is always available.
No multitenancy, follow-up automation, campaigns, or Realtime are introduced.
```
---

## P6-F.9.94 Closure Record

P6-F.9.94 — Outbound Voice Replies is closed on the isolated voice branch.

Implemented:

- OpenAI request-based TTS using `gpt-4o-mini-tts`;
- approved built-in voice `marin`;
- deterministic AI-voice disclosure;
- exact reuse of the existing deterministic response text;
- OGG/Opus output validation;
- private temporary files with guaranteed cleanup;
- authenticated WhatsApp media upload;
- WhatsApp audio delivery using an uploaded media ID and `audio.voice=true`;
- voice replies only when feature flags permit them;
- text replies preserved when voice replies are disabled;
- deterministic text fallback after TTS, validation, upload, or voice-send failure;
- no rerun of the conversational core during fallback;
- preservation of existing send-failure state and processed-message semantics.

Local voice-quality evidence:

- real OpenAI TTS request completed successfully;
- output identified as OGG/Opus;
- `marin` preview listened to and approved;
- no Meta request and no production activation occurred.

Code integration commit:

```txt
df203d8
Repository verification:

361 passed in 527.69s (0:08:47)

Production state remains unchanged:

VOICE_INPUT_ENABLED=false
VOICE_REPLIES_ENABLED=false
VOICE_REPLY_TO_AUDIO_ONLY=true

Next phase:

P6-F.9.95 — Safety, Observability and Production Activation

