import asyncio
from types import SimpleNamespace

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


def test_transcribe_spanish_voice_note_success(tmp_path):
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
    assert transcription.model == "gpt-4o-transcribe"
    assert transcription.language == "es"
    assert transcription.status == "success"
    assert transcription.error_reason is None
    assert transcription.latency_ms >= 0

    call = client.audio.transcriptions.calls[0]
    assert call["model"] == "gpt-4o-transcribe"
    assert call["language"] == "es"
    assert call["response_format"] == "text"
    assert call["file_content"] == b"normalized-audio"
    assert "Conserve literalmente" in call["prompt"]


def test_transcribe_spanish_voice_note_rejects_empty_transcript(tmp_path):
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


def test_transcribe_spanish_voice_note_contains_provider_failure(tmp_path):
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


def test_transcribe_spanish_voice_note_reports_missing_file(tmp_path):
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
