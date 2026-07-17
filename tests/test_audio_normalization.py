import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.audio_normalization import prepare_audio_for_stt


def test_prepare_audio_for_stt_remuxes_and_cleans_up(tmp_path):
    source_path = tmp_path / "source.ogg"
    source_path.write_bytes(b"ogg-opus")

    def runner(command, **kwargs):
        Path(command[-1]).write_bytes(b"webm-opus")
        return SimpleNamespace(returncode=0)

    with prepare_audio_for_stt(
        source_path,
        runner=runner,
    ) as normalized_path:
        saved_path = normalized_path

        assert normalized_path.suffix == ".webm"
        assert normalized_path.read_bytes() == b"webm-opus"
        assert normalized_path.stat().st_mode & 0o777 == 0o600

    assert not saved_path.exists()


def test_prepare_audio_for_stt_falls_back_to_mp3(tmp_path):
    source_path = tmp_path / "source.ogg"
    source_path.write_bytes(b"ogg-opus")
    calls = 0

    def runner(command, **kwargs):
        nonlocal calls
        calls += 1

        if calls == 1:
            raise subprocess.CalledProcessError(1, command)

        Path(command[-1]).write_bytes(b"mp3-audio")
        return SimpleNamespace(returncode=0)

    with prepare_audio_for_stt(
        source_path,
        runner=runner,
    ) as normalized_path:
        assert normalized_path.suffix == ".mp3"
        assert normalized_path.read_bytes() == b"mp3-audio"

    assert calls == 2


def test_prepare_audio_for_stt_reports_missing_ffmpeg(tmp_path):
    source_path = tmp_path / "source.ogg"
    source_path.write_bytes(b"ogg-opus")

    def runner(command, **kwargs):
        raise FileNotFoundError("ffmpeg")

    with pytest.raises(RuntimeError, match="ffmpeg is not available"):
        with prepare_audio_for_stt(source_path, runner=runner):
            pass
