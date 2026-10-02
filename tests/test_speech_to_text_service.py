import asyncio
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.services import speech_to_text

from app.services.speech_to_text import transcribe_spanish_voice_note


class FakeTranscriptions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(
            {
                **kwargs,
                "file_content": kwargs["file"].read(),
            }
        )

        if self.error:
            raise self.error

        return self.response


class FakeOpenAIClient:
    def __init__(self, response=None, error=None):
        self.audio = SimpleNamespace(
            transcriptions=FakeTranscriptions(
                response=response,
                error=error,
            )
        )


@pytest.mark.parametrize("model", ["gpt-4o-transcribe", "gpt-transcribe"])
def test_transcribe_spanish_voice_note_success(tmp_path, monkeypatch, model):
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_model", model)
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_language", "es")
    audio_path = tmp_path / "voice-note.webm"
    audio_path.write_bytes(b"normalized-audio")
    client = FakeOpenAIClient(
        response=SimpleNamespace(
            text="Quiero una cita para mañana a las cinco."
        )
    )

    transcription = asyncio.run(
        transcribe_spanish_voice_note(
            audio_path,
            client=client,
        )
    )

    assert transcription.text == (
        "Quiero una cita para mañana a las cinco."
    )
    assert transcription.model == model
    assert transcription.language == "es"
    assert transcription.status == "success"
    assert transcription.error_reason is None
    assert transcription.latency_ms >= 0

    call = client.audio.transcriptions.calls[0]
    assert call["model"] == model
    if model == "gpt-transcribe":
        assert "language" not in call
        assert call["extra_body"] == {"languages": ["es"]}
        assert "response_format" not in call
    else:
        assert call["language"] == "es"
        assert call["response_format"] == "text"
        assert "extra_body" not in call
    assert call["file_content"] == b"normalized-audio"
    assert call["prompt"] == speech_to_text.STT_CONTEXT_PROMPT


@pytest.mark.parametrize("model", ["gpt-4o-transcribe", "gpt-transcribe"])
def test_transcribe_spanish_voice_note_rejects_empty_transcript(tmp_path, monkeypatch, model):
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_model", model)
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_language", "es")
    audio_path = tmp_path / "voice-note.webm"
    audio_path.write_bytes(b"normalized-audio")
    client = FakeOpenAIClient(response=SimpleNamespace(text="   "))

    transcription = asyncio.run(
        transcribe_spanish_voice_note(
            audio_path,
            client=client,
        )
    )

    assert transcription.status == "error"
    assert transcription.text is None
    assert transcription.error_reason == "empty_transcription"


@pytest.mark.parametrize("model", ["gpt-4o-transcribe", "gpt-transcribe"])
def test_transcribe_spanish_voice_note_contains_provider_failure(tmp_path, monkeypatch, model):
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_model", model)
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_language", "es")
    audio_path = tmp_path / "voice-note.webm"
    audio_path.write_bytes(b"normalized-audio")
    client = FakeOpenAIClient(error=RuntimeError("provider unavailable"))

    transcription = asyncio.run(
        transcribe_spanish_voice_note(
            audio_path,
            client=client,
        )
    )

    assert transcription.status == "error"
    assert transcription.text is None
    assert transcription.error_reason == "provider_error:RuntimeError"


@pytest.mark.parametrize("model", ["gpt-4o-transcribe", "gpt-transcribe"])
def test_transcribe_spanish_voice_note_reports_missing_file(tmp_path, monkeypatch, model):
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_model", model)
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_language", "es")
    client = FakeOpenAIClient()

    transcription = asyncio.run(
        transcribe_spanish_voice_note(
            tmp_path / "missing.webm",
            client=client,
        )
    )

    assert transcription.status == "error"
    assert transcription.text is None
    assert transcription.error_reason == "audio_file_missing"
    assert client.audio.transcriptions.calls == []


def test_gpt_transcribe_uses_languages_and_default_json(tmp_path, monkeypatch):
    from app.services import speech_to_text

    monkeypatch.setattr(speech_to_text.settings, "voice_stt_model", "gpt-transcribe")
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_language", "es")
    audio_path = tmp_path / "voice-note.webm"
    audio_path.write_bytes(b"normalized-audio")
    client = FakeOpenAIClient(
        response=SimpleNamespace(text="  Necesito una cita.  ")
    )

    transcription = asyncio.run(
        transcribe_spanish_voice_note(audio_path, client=client)
    )

    assert transcription.status == "success"
    assert transcription.model == "gpt-transcribe"
    assert transcription.language == "es"
    assert transcription.text == "Necesito una cita."
    assert len(client.audio.transcriptions.calls) == 1

    call = client.audio.transcriptions.calls[0]
    assert call["model"] == "gpt-transcribe"
    assert "language" not in call
    assert call["extra_body"] == {"languages": ["es"]}
    assert "response_format" not in call
    assert call["prompt"] == speech_to_text.STT_CONTEXT_PROMPT
    assert call["file_content"] == b"normalized-audio"


@pytest.mark.parametrize("model", ["gpt-4o-transcribe", "gpt-transcribe"])
def test_transcribe_spanish_voice_note_rejects_empty_file_without_provider(tmp_path, monkeypatch, model):
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_model", model)
    monkeypatch.setattr(speech_to_text.settings, "voice_stt_language", "es")
    audio_path = tmp_path / "empty.webm"
    audio_path.write_bytes(b"")
    client = FakeOpenAIClient()

    transcription = asyncio.run(
        transcribe_spanish_voice_note(audio_path, client=client)
    )

    assert transcription.status == "error"
    assert transcription.text is None
    assert transcription.error_reason == "audio_file_empty"
    assert client.audio.transcriptions.calls == []



def test_voice_stt_model_defaults_to_gpt_transcribe():
    assert Settings.model_fields["voice_stt_model"].default == "gpt-transcribe"
