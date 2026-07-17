import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterator


CommandRunner = Callable[..., subprocess.CompletedProcess]


def _execute_ffmpeg(
    command: list[str],
    *,
    runner: CommandRunner,
) -> None:
    try:
        runner(
            command,
            check=True,
            capture_output=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is not available") from exc


@contextmanager
def prepare_audio_for_stt(
    source_path: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> Iterator[Path]:
    if not source_path.exists():
        raise ValueError("Source audio file does not exist")

    if source_path.stat().st_size == 0:
        raise ValueError("Source audio file is empty")

    with TemporaryDirectory(prefix="elvira-stt-") as directory:
        temporary_directory = Path(directory)
        webm_path = temporary_directory / "voice-note.webm"
        mp3_path = temporary_directory / "voice-note.mp3"

        try:
            _execute_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source_path),
                    "-c:a",
                    "copy",
                    str(webm_path),
                ],
                runner=runner,
            )
            normalized_path = webm_path

        except subprocess.CalledProcessError:
            _execute_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source_path),
                    "-vn",
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "64k",
                    str(mp3_path),
                ],
                runner=runner,
            )
            normalized_path = mp3_path

        if (
            not normalized_path.exists()
            or normalized_path.stat().st_size == 0
        ):
            raise ValueError("Normalized STT audio is empty")

        os.chmod(normalized_path, 0o600)
        yield normalized_path
