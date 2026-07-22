import asyncio
from types import SimpleNamespace

import app.services.text_to_speech as tts


def test_synthesize_voice_reply_preserves_response_and_adds_disclosure(
    monkeypatch,
):
    captured = {}

    class FakeSpeech:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(content=b"OggSvoice-data")

    client = SimpleNamespace(
        audio=SimpleNamespace(speech=FakeSpeech()),
    )

    result = asyncio.run(
        tts.synthesize_voice_reply(
            "Con gusto le ayudo con su solicitud.",
            client=client,
        )
    )

    assert result.status == "success"
    assert result.audio_content == b"OggSvoice-data"
    assert captured["model"] == "gpt-4o-mini-tts"
    assert captured["voice"] == "marin"
    assert captured["response_format"] == "opus"
    assert captured["input"] == (
        "Soy Elvira, la asistente virtual de Respirarte. "
        "Con gusto le ayudo con su solicitud."
    )


def test_build_voice_reply_text_omits_disclosure_when_not_required():
    result = tts.build_voice_reply_text(
        "La doctora le confirmará la cita.",
        include_disclosure=False,
    )

    assert result == "La doctora le confirmará la cita."


def test_synthesize_voice_reply_returns_safe_provider_error():
    class FailingSpeech:
        async def create(self, **kwargs):
            raise RuntimeError("private provider detail")

    client = SimpleNamespace(
        audio=SimpleNamespace(speech=FailingSpeech()),
    )

    result = asyncio.run(
        tts.synthesize_voice_reply(
            "Respuesta determinística.",
            client=client,
        )
    )

    assert result.status == "error"
    assert result.audio_content is None
    assert result.error_reason == "provider_error:RuntimeError"


def test_synthesize_voice_reply_rejects_empty_text():
    result = asyncio.run(tts.synthesize_voice_reply("   "))

    assert result.status == "error"
    assert result.error_reason == "Deterministic response text is empty"


def test_temporary_synthesized_voice_note_is_private_and_removed(tmp_path):
    with tts.temporary_synthesized_voice_note(
        b"OggSvoice-data",
    ) as audio_path:
        assert audio_path.exists()
        assert audio_path.suffix == ".ogg"
        assert audio_path.read_bytes() == b"OggSvoice-data"
        assert audio_path.stat().st_mode & 0o777 == 0o600

    assert not audio_path.exists()


def test_temporary_synthesized_voice_note_rejects_non_ogg():
    try:
        with tts.temporary_synthesized_voice_note(b"not-ogg"):
            pass
    except ValueError as exc:
        assert str(exc) == "Synthesized voice audio is not OGG/Opus"
    else:
        raise AssertionError("Expected invalid OGG rejection")


def test_p6f999_build_voice_reply_uses_spoken_version_without_mutating_source():
    written = (
        "La franja es de 3:00 p. m. a 5:00 p. m. "
        "Debe guardar 3 horas de ayuno."
    )

    spoken = tts.build_voice_reply_text(
        written,
        include_disclosure=False,
    )

    assert written == (
        "La franja es de 3:00 p. m. a 5:00 p. m. "
        "Debe guardar 3 horas de ayuno."
    )
    assert spoken == (
        "La franja es de tres de la tarde a cinco de la tarde. "
        "Debe guardar tres horas de ayuno."
    )


def test_p6f999_disclosure_is_added_after_spoken_normalization():
    spoken = tts.build_voice_reply_text(
        "La cita es a las 3:00 p. m.",
        include_disclosure=True,
    )

    assert spoken == (
        "Soy Elvira, la asistente virtual de Respirarte. "
        "La cita es a las tres de la tarde."
    )



def test_p6f999_uses_colombian_spanish_tts_instructions(monkeypatch):
    captured = {}

    class FakeSpeech:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(content=b"OggSvoice-data")

    client = SimpleNamespace(
        audio=SimpleNamespace(speech=FakeSpeech()),
    )

    result = asyncio.run(
        tts.synthesize_voice_reply(
            "La cita es el cinco de septiembre.",
            include_disclosure=False,
            client=client,
        )
    )

    assert result.status == "success"
    assert captured["voice"] == "marin"
    assert "español colombiano neutro" in captured["instructions"]
    assert "seseo latinoamericano" in captured["instructions"]
    assert "peninsular" in captured["instructions"]
