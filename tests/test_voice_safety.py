import subprocess

import app.services.voice_safety as voice_safety


def test_voice_allowlist_normalizes_numbers(monkeypatch):
    monkeypatch.setattr(
        voice_safety.settings,
        "voice_allowed_phone_numbers",
        "+57 300 111 2233,573002224444",
    )

    assert voice_safety.is_voice_phone_allowed("573001112233") is True
    assert voice_safety.is_voice_phone_allowed("+57 300 222 4444") is True
    assert voice_safety.is_voice_phone_allowed("573009999999") is False


def test_empty_voice_allowlist_fails_closed(monkeypatch):
    monkeypatch.setattr(
        voice_safety.settings,
        "voice_allowed_phone_numbers",
        "",
    )

    assert voice_safety.is_voice_phone_allowed("573001112233") is False


def test_validate_voice_note_duration_accepts_bounded_audio(
    monkeypatch,
    tmp_path,
):
    audio_path = tmp_path / "voice.ogg"
    audio_path.write_bytes(b"OggSvoice-data")

    monkeypatch.setattr(
        voice_safety.settings,
        "voice_max_duration_seconds",
        120.0,
    )

    def fake_runner(command, **kwargs):
        assert command[0] == "ffprobe"
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"format": {"duration": "45.25"}}',
            stderr="",
        )

    duration = voice_safety.validate_voice_note_duration(
        audio_path,
        runner=fake_runner,
    )

    assert duration == 45.25


def test_validate_voice_note_duration_rejects_long_audio(
    monkeypatch,
    tmp_path,
):
    audio_path = tmp_path / "voice.ogg"
    audio_path.write_bytes(b"OggSvoice-data")

    monkeypatch.setattr(
        voice_safety.settings,
        "voice_max_duration_seconds",
        120.0,
    )

    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"format": {"duration": "120.01"}}',
            stderr="",
        )

    try:
        voice_safety.validate_voice_note_duration(
            audio_path,
            runner=fake_runner,
        )
    except ValueError as exc:
        assert str(exc) == (
            "WhatsApp voice note exceeds duration limit"
        )
    else:
        raise AssertionError("Expected duration-limit rejection")


def test_validate_voice_note_duration_requires_ffprobe(tmp_path):
    audio_path = tmp_path / "voice.ogg"
    audio_path.write_bytes(b"OggSvoice-data")

    def missing_runner(command, **kwargs):
        raise FileNotFoundError("ffprobe")

    try:
        voice_safety.validate_voice_note_duration(
            audio_path,
            runner=missing_runner,
        )
    except RuntimeError as exc:
        assert str(exc) == "ffprobe is not available"
    else:
        raise AssertionError("Expected ffprobe failure")


def test_voice_phone_allowlist_wildcard_allows_any_valid_phone(
    monkeypatch,
):
    monkeypatch.setattr(
        voice_safety.settings,
        "voice_allowed_phone_numbers",
        "573001112233, *",
    )

    assert voice_safety.configured_voice_phone_numbers() == {
        "573001112233",
        "*",
    }
    assert voice_safety.is_voice_phone_allowed("+57 300 999 9999") is True
    assert voice_safety.is_voice_phone_allowed("573008887777") is True
    assert voice_safety.is_voice_phone_allowed(None) is False
